"""
04_generate_describe_csv.py

Minimal batch generator:
- Load each CSV under a folder (default: raw_data/)
- Try to coerce numeric-like object columns (e.g., "1,288.00") into numbers
- Run pandas .describe() (numeric columns only; default behavior)
- Save output as CSV per table into docs/tablestats/
- If a table has no numeric columns, skip (no file generated)

Usage:
  python python/04_generate_describe_csv.py
  python python/04_generate_describe_csv.py --input raw_data --out docs/tablestats
  python python/04_generate_describe_csv.py --input extra-i-cleaning/cleaned_data --out docs/tablestats_cleaned
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def read_csv_safely(path: Path) -> pd.DataFrame:
    """Try UTF-8 first, fallback to UTF-16. Also support thousands separators."""
    try:
        return pd.read_csv(path, thousands=",")
    except UnicodeError:
        return pd.read_csv(path, encoding="utf-16", thousands=",")


def coerce_numeric_like_object_columns(df: pd.DataFrame, min_non_null_ratio: float = 0.85) -> pd.DataFrame:
    """
    Convert object columns that mostly look like numbers into numeric.
    - Handles values like "1,288.00", " 603.50 ", "2,000"
    - Leaves true categorical columns (e.g., Country/Region) untouched
    """
    obj_cols = df.select_dtypes(include=["object"]).columns
    for col in obj_cols:
        s = df[col]

        # skip if all null
        if s.notna().sum() == 0:
            continue

        # Try numeric conversion:
        #  - strip spaces
        #  - remove commas (thousands)
        #  - coerce errors -> NaN
        cleaned = (
            s.astype(str)
             .str.strip()
             .str.replace(",", "", regex=False)
        )
        converted = pd.to_numeric(cleaned, errors="coerce")

        # Only apply if conversion "mostly works" for non-null values
        non_null = s.notna().sum()
        ok = converted.notna().sum()
        if non_null > 0 and (ok / non_null) >= min_non_null_ratio:
            df[col] = converted

    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="raw_data", help="Folder containing *.csv")
    ap.add_argument("--out", default="docs/tablestats", help="Output folder")
    ap.add_argument("--ratio", type=float, default=0.85, help="min ratio to coerce object->numeric")
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(in_dir.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No CSV files found under: {in_dir.resolve()}")

    created = 0
    skipped = 0

    for csv_path in csv_files:
        table = csv_path.stem
        print(f"== {table} ==")

        df = read_csv_safely(csv_path)
        df = coerce_numeric_like_object_columns(df, min_non_null_ratio=args.ratio)

        # pandas default describe() summarizes numeric columns only
        try:
            desc = df.describe()
        except Exception as e:
            print(f"  - SKIP: describe() failed: {e}")
            skipped += 1
            continue

        if desc.empty:
            print("  - SKIP: no numeric columns")
            skipped += 1
            continue

        out_path = out_dir / f"{table}__describe.csv"
        desc.to_csv(out_path)
        print(f"  - OK: {out_path.as_posix()}")
        created += 1

    print(f"\nDone. created={created}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
