# rag/build_index.py
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb

from .config import (
    CLEAN_PRODUCTS_PATH,
    CHROMA_PATH,
    CHROMA_COLLECTION_NAME,
    EMBED_MODEL_NAME,
)
from .data_prep import run_cleaning_pipeline

def build_index_from_clean_df(batch_size: int = 256) -> None:
    # Load cleaned slice
    df = pd.read_parquet(CLEAN_PRODUCTS_PATH)

    embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Re-create collection
    try:
        chroma_client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception as e:
        print("Warning when deleting collection (may not exist yet):", e)

    collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION_NAME)

    ids = df["id"].astype(str).tolist()
    texts = (df["title"].astype(str) + ". " + df["features"].astype(str)).tolist()

    metadatas = []
    for _, row in df.iterrows():
        price_val = float(row["price"]) if row["price"] is not None and not pd.isna(row["price"]) else -1.0
        rating_val = float(row["rating"]) if row["rating"] is not None and not pd.isna(row["rating"]) else -1.0

        meta = {
            "title": str(row["title"]) if not pd.isna(row["title"]) else "",
            "brand": str(row.get("brand", "")) if not pd.isna(row.get("brand", "")) else "",
            "price": price_val,
            "rating": rating_val,
            "ingredients": str(row.get("ingredients", "")) if not pd.isna(row.get("ingredients", "")) else "",
        }
        metadatas.append(meta)

    for start in range(0, len(ids), batch_size):
        end = min(start + batch_size, len(ids))
        batch_ids = ids[start:end]
        batch_texts = texts[start:end]
        batch_metas = metadatas[start:end]

        embeddings = embed_model.encode(batch_texts, show_progress_bar=False)

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            metadatas=batch_metas,
        )
        print(f"Indexed {end} / {len(ids)}")

    print("Finished building Chroma index.")


def rebuild_index() -> None:
    """Full pipeline: clean data + rebuild Chroma index."""
    run_cleaning_pipeline()
    build_index_from_clean_df()


if __name__ == "__main__":
    rebuild_index()
