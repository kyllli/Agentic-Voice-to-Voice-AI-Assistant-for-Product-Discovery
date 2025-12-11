# mcp_server/server.py
import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

from rag.search import search_products
from .web_search import web_search

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="MCP Server - rag.search + web.search")


# ---------- Pydantic models ----------

class RagSearchRequest(BaseModel):
    query: str
    constraints: Dict[str, Any] = {}
    max_results: int = 5


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5


# ---------- Tool Discovery ----------

@app.get("/mcp/tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": "rag.search",
                "description": "Search local Amazon product slice.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "constraints": {
                            "type": "object",
                            "properties": {
                                "budget": {"type": "number"},
                                "brand": {"type": "string"},
                                "material": {"type": "string"},
                                "category": {"type": "string"},
                            },
                        },
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                    },
                },
            },
            {
                "name": "web.search",
                "description": "Call external web search for current prices/availability.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "timestamp": {"type": "string"},
                    },
                },
            },
        ]
    }


# ---------- Tools ----------

import difflib

def fuzzy_match(a: str, b: str, threshold=0.45) -> bool:
    """Basic fuzzy matching for brand & category."""
    if not a or not b:
        return False
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


@app.post("/mcp/tools/rag.search")
async def mcp_rag_search(req: RagSearchRequest):
    try:
        constraints = req.constraints or {}

        max_price = constraints.get("budget")
        brand = constraints.get("brand")
        category = constraints.get("category")

        logger.info(
            f"[rag.search] query='{req.query}', "
            f"max_price={max_price}, brand={brand}, category={category}"
        )

        # ---------------------------------------------------------
        # 🔥 DO NOT pass brand/category directly into search_products
        #     because they perform STRICT matching → empty results.
        #
        # Instead:
        #   - let search_products retrieve candidates from embeddings
        #   - apply fuzzy filtering AFTERWARD
        # ---------------------------------------------------------

        raw_results = search_products(
            query=req.query,
            max_results=req.max_results * 5,  # retrieve more candidates
            max_price=max_price,
        )

        filtered = []
        for p in raw_results:
            ok = True

            # Fuzzy brand
            if brand:
                prod_brand = p.get("brand", "")
                if prod_brand and not fuzzy_match(prod_brand, brand):
                    ok = False

            # Fuzzy category / subcategory
            if category:
                prod_cat = p.get("subcategory", "") or p.get("category", "")
                if prod_cat and not fuzzy_match(prod_cat, category):
                    ok = False

            if ok:
                filtered.append(p)

        # Clip to max_results
        filtered = filtered[:req.max_results]

        logger.info(f"[rag.search] returning {len(filtered)} results")
        return {"results": filtered}

    except Exception as e:
        logger.exception("Error in rag.search")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/web.search")
async def mcp_web_search(req: WebSearchRequest):
    try:
        logger.info(f"[web.search] query='{req.query}'")
        payload = web_search(query=req.query, max_results=req.max_results)
        return payload
    except Exception as e:
        logger.exception("Error in web.search")
        raise HTTPException(status_code=500, detail=str(e))
