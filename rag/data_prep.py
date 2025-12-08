# rag/data_prep.py
from typing import List
import pandas as pd
from .config import RAW_PRODUCTS_PATH, CLEAN_PRODUCTS_PATH

# Keywords to focus on cleaning-related items
CLEANING_KEYWORDS = [
    "cleaner", "cleaning", "detergent", "soap", "wipe", "polish",
    "degreaser", "disinfectant", "stainless", "surface", "spray"
]

def load_raw_products(path=RAW_PRODUCTS_PATH) -> pd.DataFrame:
    df_raw = pd.read_csv(path)
    return df_raw


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Try to map the notebook schema; adjust if your CSV has slightly different names.
    rename_map = {
        "Uniq Id": "id",
        "Product Name": "title",
        "Category": "category",
        "Selling Price": "price_raw",
    }
    # Only rename columns that exist
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Basic required columns
    if "id" not in df.columns:
        df["id"] = df.index.astype(str)

    if "title" not in df.columns:
        df["title"] = df.get("Product Name", "")

    if "category" not in df.columns:
        df["category"] = df.get("Category", "")

    # Filter to cleaning domain using category + title keywords
    mask_category = df["category"].astype(str).str.contains("Cleaning", case=False, na=False)
    mask_title = df["title"].astype(str).str.lower().str.contains("|".join(CLEANING_KEYWORDS), na=False)
    df = df[mask_category | mask_title].copy()

    # Price standardization
    price_col = "price_raw" if "price_raw" in df.columns else "Selling Price"
    if price_col in df.columns:
        df["price"] = (
            df[price_col]
              .astype(str)
              .str.replace("$", "", regex=False)
              .str.replace(",", "", regex=False)
        )
        df["price"] = pd.to_numeric(df["price"], errors="coerce").clip(lower=0)
    else:
        df["price"] = None

    # Rating – if dataset has "Average Rating"
    if "Average Rating" in df.columns:
        df["rating"] = pd.to_numeric(df["Average Rating"], errors="coerce")
    else:
        df["rating"] = None

    # Build features text from any descriptive columns we can find
    candidate_feature_cols: List[str] = [
        "About Product",
        "Product Specification",
        "Technical Details",
        "Product Details",
        "Product Description",
        "Description",
        "about_product",
        "product_description",
    ]
    feature_cols = [c for c in candidate_feature_cols if c in df.columns]

    if feature_cols:
        df["features"] = (
            df[feature_cols]
              .astype(str)
              .replace("nan", "")
              .agg(" ".join, axis=1)
              .str.strip()
        )
    else:
        df["features"] = ""

    # Ingredients – best-effort
    for cand in ["Ingredients", "ingredients"]:
        if cand in df.columns:
            df["ingredients"] = (
                df[cand]
                  .astype(str)
                  .replace("nan", "")
                  .fillna("")
                  .str.strip()
            )
            break
    else:
        df["ingredients"] = ""

    # Brand
    if "Brand" in df.columns:
        df["brand"] = df["Brand"].astype(str)
    else:
        df["brand"] = ""

    keep_cols = ["id", "title", "category", "price", "rating", "features", "ingredients", "brand"]
    df = df[keep_cols].drop_duplicates(subset=["id"]).reset_index(drop=True)

    return df


def save_clean_products(df: pd.DataFrame, path=CLEAN_PRODUCTS_PATH) -> None:
    df.to_parquet(path, index=False)


def run_cleaning_pipeline() -> None:
    df_raw = load_raw_products()
    df_clean = clean_products(df_raw)
    save_clean_products(df_clean)
    print(f"Cleaned {len(df_clean)} products and saved to {CLEAN_PRODUCTS_PATH}")
