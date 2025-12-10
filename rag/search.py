# rag/search.py
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np

from .config import (
    CLEAN_PRODUCTS_PATH,
    CHROMA_PATH,
    CHROMA_COLLECTION_NAME,
    EMBED_MODEL_NAME,
)
import pandas as pd


# ---------------------------------------------------------
# Load embedding model
# ---------------------------------------------------------
embed_model = SentenceTransformer(EMBED_MODEL_NAME)

# ---------------------------------------------------------
# Load Chroma client + collection
# ---------------------------------------------------------
chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)


# ---------------------------------------------------------
# Hybrid RAG Search
# ---------------------------------------------------------
def normalize_url(url):
    if not url:
        return ""
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return "https://" + url


def search_products(
    query: str,
    max_results: int = 5,
    max_price: Optional[float] = None,
    brand: Optional[str] = None,
    subcategory_filter: Optional[str] = None,
    sort_by: str = "hybrid",  # "similarity", "rating_price", "hybrid"
) -> List[Dict[str, Any]]:
    """
    Enhanced hybrid retrieval combining:
    - vector similarity (50 candidates)
    - metadata filtering (price, brand, subcategory)
    - hybrid reranking across (distance, rating, price)
    """

    # ---------------------------------------
    # 1. Encode query
    # ---------------------------------------
    query_emb = embed_model.encode([query])[0]

    # ---------------------------------------
    # 2. Retrieve more candidates
    # ---------------------------------------
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=max_results * 10,    # retrieve 50 candidates
        include=["metadatas", "distances"]
    )

    ids = results.get("ids", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    candidates = []

    for pid, meta, dist in zip(ids, metas, dists):

        # Extract metadata with fallbacks
        title = meta.get("title", "")
        price = meta.get("price", None)
        rating = meta.get("rating", -1.0)
        brand_val = meta.get("brand", "") or ""
        subcat = meta.get("subcategory", "") or ""
        product_url = meta.get("product_url", "")
        image_url = meta.get("image_url", "")
        ingredients = meta.get("ingredients", "")
        features = meta.get("features", "")

        # ---------------------------------------
        # Apply metadata filters
        # ---------------------------------------

        # price ≤ max_price
        if (max_price is not None) and (price is not None) and (price > max_price):
            continue

        # brand filter (optional)
        if brand and brand.lower() not in brand_val.lower():
            continue

        # subcategory filter (optional)
        if subcategory_filter and subcategory_filter.lower() not in subcat.lower():
            continue

        # normalize missing rating
        if rating is None:
            rating = -1.0

        candidates.append({
            "id": pid,
            "title": title,
            "price": price,
            "rating": rating,
            "brand": brand_val,
            "subcategory": subcat,
            "category": meta.get("category", ""),
            "features": features,
            "ingredients": ingredients,
            "product_url": product_url,
            "image_url": image_url,
            "doc_id": f"products_clothing::{pid}",
            "_distance": dist,
        })

    if not candidates:
        return []

    # -------------------------------------------------
    # 3. Reranking Strategies
    # -------------------------------------------------

    if sort_by == "similarity":
        # smaller distance is better
        candidates = sorted(candidates, key=lambda x: x["_distance"])

    elif sort_by == "rating_price":
        candidates = sorted(
            candidates,
            key=lambda x: (
                -(x["rating"] if x["rating"] is not None else -1),
                x["price"] if x["price"] is not None else 1e9,
            ),
        )

    else:  # hybrid (BEST)
        def hybrid_key(x):
            dist = x["_distance"]
            rating = x["rating"] if x["rating"] is not None else -1
            price = x["price"] if x["price"] is not None else 1e9
            return (
                dist,     # similarity first
                -rating,  # higher rating better
                price,    # cheaper preferred
            )

        candidates = sorted(candidates, key=hybrid_key)

    # Remove internal keys and return top-k
    final = []
    for c in candidates[:max_results]:
        c.pop("_distance", None)
        final.append(c)

    return final
