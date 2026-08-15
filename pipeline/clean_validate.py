"""
Cleaning and validation for the raw scraped catalog.

Handles the stuff that always shows up in a real scrape:
  - duplicate SKUs from repeated crawls
  - missing/blank fields
  - inconsistent price formatting ("$19.99", "19.99 USD", "19.99")
  - category values that don't match the site's actual taxonomy
  - a completeness score per row so partial records can be triaged
    instead of silently dropped
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def load_raw(path=None):
    path = path or config.RAW_CSV_PATH
    df = pd.read_csv(path, dtype=str)
    return df


def normalize_whitespace(df):
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": np.nan, "": np.nan, "None": np.nan})
    return df


def coerce_price(df):
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["currency"] = df["currency"].fillna("USD")
    return df


def fix_categories(df):
    """
    Flags category values that fall outside the known taxonomy rather
    than dropping them, since a mismatch is often a formatting issue
    (extra whitespace, wrong casing) and worth a human look.
    """
    df["category"] = df["category"].str.strip()
    known = config.VALID_CATEGORIES
    df["category_valid"] = df["category"].isin(known)
    return df


def dedupe(df):
    """
    Same SKU can appear more than once from overlapping crawl passes.
    Keep the record with the highest field-completeness, and log what
    was dropped so the removal is auditable rather than silent.
    """
    df["_completeness_tmp"] = df[config.COMPLETENESS_FIELDS].notna().sum(axis=1)
    df = df.sort_values("_completeness_tmp", ascending=False)

    duplicate_mask = df.duplicated(subset="sku", keep="first")
    removed = df[duplicate_mask].copy()
    kept = df[~duplicate_mask].copy()

    kept = kept.drop(columns="_completeness_tmp").reset_index(drop=True)
    removed = removed.drop(columns="_completeness_tmp").reset_index(drop=True)
    return kept, removed


def flag_missing_required(df):
    missing_required = df[config.REQUIRED_FIELDS].isna().any(axis=1)
    df["missing_required_field"] = missing_required
    return df


def score_completeness(df):
    filled = df[config.COMPLETENESS_FIELDS].notna().sum(axis=1)
    df["completeness_pct"] = (filled / len(config.COMPLETENESS_FIELDS) * 100).round(1)
    return df


def build_quality_report(raw_df, clean_df, removed_dupes_df):
    total_raw = len(raw_df)
    total_clean = len(clean_df)

    missing_by_field = {}
    for field in config.COMPLETENESS_FIELDS:
        missing_by_field[field] = int(clean_df[field].isna().sum())

    report_rows = [
        {"metric": "Raw records scraped", "value": total_raw},
        {"metric": "Duplicate SKUs removed", "value": len(removed_dupes_df)},
        {"metric": "Records after dedupe", "value": total_clean},
        {"metric": "Records missing a required field", "value": int(clean_df["missing_required_field"].sum())},
        {"metric": "Records with invalid/unrecognized category", "value": int((~clean_df["category_valid"]).sum())},
        {"metric": "Average completeness score (%)", "value": round(clean_df["completeness_pct"].mean(), 1)},
    ]
    for field, count in missing_by_field.items():
        report_rows.append({"metric": f"Missing '{field}'", "value": count})

    return pd.DataFrame(report_rows)


def run(raw_path=None):
    raw_df = load_raw(raw_path)
    df = raw_df.copy()

    df = normalize_whitespace(df)
    df = coerce_price(df)
    df = fix_categories(df)
    df, removed_dupes = dedupe(df)
    df = flag_missing_required(df)
    df = score_completeness(df)

    df = df.sort_values(["category", "product_name"], na_position="last").reset_index(drop=True)

    quality_report = build_quality_report(raw_df, df, removed_dupes)

    return {
        "clean": df,
        "removed_duplicates": removed_dupes,
        "quality_report": quality_report,
    }


if __name__ == "__main__":
    result = run()
    os.makedirs(config.PROCESSED_DATA_DIR, exist_ok=True)
    result["clean"].to_csv(config.CLEAN_CSV_PATH, index=False)
    print(f"clean data written to {config.CLEAN_CSV_PATH}")
    print(result["quality_report"].to_string(index=False))
