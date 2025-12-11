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
    Enhanced hybrid retrieval with:
    - vector similarity (50 candidates)
    - metadata filtering (price, brand, subcategory)
    - hybrid reranking across (distance, rating, price)
    Clean version: removed all -1 placeholder outputs.
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

        # Extract metadata with clean fallbacks
        title = meta.get("title", "") or ""
        price = meta.get("price", None)
        rating = meta.get("rating")
        brand_val = meta.get("brand", "") or ""
        subcat = meta.get("subcategory", "") or ""
        product_url = meta.get("product_url", "") or ""
        image_url = meta.get("image_url", "") or ""
        ingredients = meta.get("ingredients", "") or ""
        features = meta.get("features", "") or ""
        category = meta.get("category", "") or ""

        # ---------------------------------------
        # Apply metadata filters
        # ---------------------------------------

        # price filter
        if max_price is not None:
            # If price is missing, skip immediately
            if price is None or price < 0:
                continue
            # Otherwise enforce max price
            if price > max_price:
                continue

        # brand filter
        if brand and brand.lower() not in brand_val.lower():
            continue

        # subcategory filter
        if subcategory_filter and subcategory_filter.lower() not in subcat.lower():
            continue

        # rating: convert -1 → None so UI never sees -1
        if rating in [None, "", "-1", -1, -1.0]:
            rating = 0.0
        else:
            rating = float(rating)

        candidates.append({
            "id": pid,
            "title": title,
            "price": price if price is not None else None,
            "rating": rating,
            "brand": brand_val,
            "subcategory": subcat,
            "category": category,
            "features": features,
            "ingredients": ingredients,
            "product_url": product_url,
            "image_url": image_url,
            "doc_id": f"products::{pid}",
            "_distance": dist,
        })

    if not candidates:
        return []

    # -------------------------------------------------
    # 3. Reranking Strategies
    # -------------------------------------------------

    if sort_by == "similarity":
        candidates = sorted(candidates, key=lambda x: x["_distance"])

    elif sort_by == "rating_price":
        candidates = sorted(
            candidates,
            key=lambda x: (
                -(x["rating"] or 0),  # if None → 0
                x["price"] if x["price"] is not None else 1e9,
            ),
        )

    else:  # hybrid (BEST)
        def hybrid_key(x):
            dist = x["_distance"]
            rating_val = x["rating"] if x["rating"] is not None else 0
            price_val = x["price"] if x["price"] is not None else 1e9
            return (
                dist,          # similarity
                -rating_val,   # higher rating is better
                price_val,     # cheaper is better
            )

        candidates = sorted(candidates, key=hybrid_key)

    # Remove internal keys and return top-k clean results
    final = []
    for c in candidates[:max_results]:
        c.pop("_distance", None)
        final.append(c)

    return final
