# rag/search.py
from typing import List, Dict, Any, Optional
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from .config import (
    CHROMA_PATH,
    CHROMA_COLLECTION_NAME,
    EMBED_MODEL_NAME,
)

@lru_cache(maxsize=1)
def get_embed_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL_NAME)


@lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(CHROMA_COLLECTION_NAME)


def search_products(
    query: str,
    max_results: int = 5,
    max_price: Optional[float] = None,
    brand: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Core RAG retrieval used by MCP rag.search."""
    embed_model = get_embed_model()
    collection = get_collection()

    query_emb = embed_model.encode([query])[0]

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=max_results * 3,
    )

    out: List[Dict[str, Any]] = []
    ids_list = results.get("ids", [[]])[0]
    metas_list = results.get("metadatas", [[]])[0]

    for pid, meta in zip(ids_list, metas_list):
        price = meta.get("price", None)
        prod_brand = meta.get("brand", "")

        # Apply price filter
        if (max_price is not None) and (price is not None) and (price > max_price):
            continue

        # Apply brand filter
        if brand is not None and brand.lower() not in str(prod_brand).lower():
            continue

        out.append({
            "sku": pid,
            "title": meta.get("title", ""),
            "price": price,
            "rating": meta.get("rating", None),
            "brand": prod_brand,
            "ingredients": meta.get("ingredients", ""),
            "doc_id": f"products_cleaning::{pid}",
        })

        if len(out) >= max_results:
            break

    return out
