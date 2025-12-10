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
    """Discovery endpoint listing available tools + their JSON schemas."""
    return {
        "tools": [
            {
                "name": "rag.search",
                "description": "Search local Amazon 2020 cleaning-product slice.",
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

@app.post("/mcp/tools/rag.search")
async def mcp_rag_search(req: RagSearchRequest):
    try:
        constraints = req.constraints or {}
        max_price = constraints.get("budget")
        brand = constraints.get("brand")

        logger.info(f"[rag.search] query='{req.query}', max_price={max_price}, brand={brand}")

        results = search_products(
            query=req.query,
            max_results=req.max_results,
            max_price=max_price,
            brand=brand,
        )

        return {"results": results}
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
