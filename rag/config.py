# rag/config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"

RAW_PRODUCTS_PATH = RAW_DIR / "marketing_sample_for_amazon_com-ecommerce__20200101_20200131__10k_data.csv"
CLEAN_PRODUCTS_PATH = PROCESSED_DIR / "clean_products_clothing.parquet"

CHROMA_PATH = INDEX_DIR / "chroma_products_clothing"
CHROMA_COLLECTION_NAME = "products_clothing"

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Make sure folders exist
for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR, INDEX_DIR]:
    d.mkdir(parents=True, exist_ok=True)
