# rag/data_prep.py
from typing import List
import pandas as pd
from .config import RAW_PRODUCTS_PATH, CLEAN_PRODUCTS_PATH


# ============================================================
# Load Raw CSV
# ============================================================

def load_raw_products(path=RAW_PRODUCTS_PATH) -> pd.DataFrame:
    """Load the raw Amazon dataset CSV."""
    df_raw = pd.read_csv(path)
    return df_raw


# ============================================================
# Clean + Filter for Toys & Games
# ============================================================

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --------------------------------------------------------
    # 1) Normalize raw column names → standardized schema
    # --------------------------------------------------------
    rename_map = {
        "Uniq Id": "id",
        "Product Name": "title",
        "Brand Name": "brand",
        "Category": "category_raw",
        "Sub Category": "subcategory_raw",
        "Selling Price": "price_raw",
        "Product Url": "product_url",
        "Image": "image_url",
    }
    df = df.rename(columns=rename_map)

    # --------------------------------------------------------
    # 2) Filter to Toys & Games category
    # --------------------------------------------------------
    df = df[
        df["category_raw"]
        .astype(str)
        .str.contains("Toys & Games", case=False, na=False)
    ].copy()

    # If dataset has no matching rows → return empty schema
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "title", "brand", "category", "subcategory",
            "price", "rating", "features", "ingredients",
            "product_url", "image_url"
        ])

    # --------------------------------------------------------
    # 3) Standard category + subcategory
    # --------------------------------------------------------
    df["category"] = "Toys & Games"

    if "subcategory_raw" in df.columns:
        df["subcategory"] = df["subcategory_raw"].astype(str)
    else:
        df["subcategory"] = df["category_raw"].astype(str)

    # --------------------------------------------------------
    # 4) Clean price (string → numeric)
    # --------------------------------------------------------
    df["price"] = (
        df["price_raw"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    df["price"] = pd.to_numeric(df["price"], errors="coerce").clip(lower=0)

    # --------------------------------------------------------
    # 5) Ratings (dataset doesn't include ratings → fill None)
    # --------------------------------------------------------
    df["rating"] = None

    # --------------------------------------------------------
    # 6) Build unified "features" text field
    # --------------------------------------------------------
    candidate_feature_cols = [
        "About Product",
        "Product Specification",
        "Technical Details",
        "Product Details",
        "Product Description",
        "Description",
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

    # --------------------------------------------------------
    # 7) Ingredients
    # --------------------------------------------------------
    if "Ingredients" in df.columns:
        df["ingredients"] = (
            df["Ingredients"]
            .astype(str)
            .replace("nan", "")
            .fillna("")
            .str.strip()
        )
    else:
        df["ingredients"] = ""

    # --------------------------------------------------------
    # 8) URL cleaning
    # --------------------------------------------------------
    df["product_url"] = df.get("product_url", "").astype(str).fillna("").str.strip()
    df["image_url"] = df.get("image_url", "").astype(str).fillna("").str.strip()
    df["image_url"] = df["image_url"].astype(str).str.split("|").str[0]

    # --------------------------------------------------------
    # 9) Final RAG schema
    # --------------------------------------------------------
    keep_cols = [
        "id",
        "title",
        "brand",
        "category",
        "subcategory",
        "price",
        "rating",
        "features",
        "ingredients",
        "product_url",
        "image_url",
    ]
    df = df[keep_cols].drop_duplicates(subset=["id"]).reset_index(drop=True)

    return df


# ============================================================
# Save Clean Data
# ============================================================

def save_clean_products(df: pd.DataFrame, path=CLEAN_PRODUCTS_PATH) -> None:
    """Save cleaned dataset as Parquet for indexing."""
    df.to_parquet(path, index=False)


# ============================================================
# Pipeline Runner
# ============================================================

def run_cleaning_pipeline() -> None:
    print("Loading raw products from:", RAW_PRODUCTS_PATH)
    df_raw = load_raw_products()

    print("Cleaning + filtering for Toys & Games...")
    df_clean = clean_products(df_raw)

    print(f"Cleaned {len(df_clean)} products. Saving to {CLEAN_PRODUCTS_PATH} ...")
    save_clean_products(df_clean)

    print("Done! Cleaned dataset ready for embedding + vector DB indexing.")
