from __future__ import annotations

from pathlib import Path
import re
import pandas as pd


# ----------------------------
# Config
# ----------------------------
RAW_DIR = Path("raw_data")
OUT_DIR = Path("extra-i-cleaning/cleaned_data")
ARTIFACT_DIR = Path("extra-i-cleaning/artifacts")

# If you want to lock to specific files, set this list; otherwise None loads all *.csv in RAW_DIR.
ONLY_FILES: list[str] | None = None

# Source date format (as profiled): mm-dd-yyyy
RAW_DATE_FORMAT = "%m-%d-%Y"

# Output date format (ISO) for Postgres-friendly CSVs
OUTPUT_DATE_FORMAT = "%Y-%m-%d"


# ----------------------------
# Encoding helpers
# ----------------------------
def detect_encoding_by_bom(csv_path: Path) -> str | None:
    with open(csv_path, "rb") as f:
        first4 = f.read(4)

    if first4.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if first4.startswith(b"\xff\xfe") or first4.startswith(b"\xfe\xff"):
        return "utf-16"
    if first4.startswith(b"\xff\xfe\x00\x00") or first4.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32"
    return None


def read_csv_smart(csv_path: Path) -> tuple[pd.DataFrame, str]:
    enc = detect_encoding_by_bom(csv_path)
    enc_candidates = [enc] if enc else []
    enc_candidates += ["utf-8", "utf-8-sig", "cp1252", "latin1"]

    last_err: Exception | None = None
    for e in enc_candidates:
        try:
            df = pd.read_csv(csv_path, encoding=e, low_memory=False)
            return df, e
        except UnicodeDecodeError as err:
            last_err = err

    raise last_err  # type: ignore[misc]


# ----------------------------
# Naming helpers: CamelCase -> snake_case
# ----------------------------
_CAMEL_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_2 = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    s = name.strip().replace(" ", "_").replace("-", "_")
    s = _CAMEL_1.sub(r"\1_\2", s)
    s = _CAMEL_2.sub(r"\1_\2", s)
    s = re.sub(r"__+", "_", s)
    return s.lower()


def normalize_columns_to_snake(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [camel_to_snake(c) for c in df.columns]
    return df


# ----------------------------
# Column detection rules (after snake_case)
# ----------------------------
def detect_id_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.endswith("_id")]


def detect_date_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.endswith("_date")]


# ----------------------------
# Standardization steps
# ----------------------------
def cast_id_columns_to_string(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    id_cols = detect_id_columns(df)
    for c in id_cols:
        df[c] = df[c].astype("string")
    return df, id_cols


def parse_date_columns(df: pd.DataFrame, *, raw_format: str = RAW_DATE_FORMAT) -> tuple[pd.DataFrame, list[str], dict[str, int]]:
    """
    Smart date parsing for *_date columns.
    Strategy:
      1) Try strict RAW_DATE_FORMAT first (e.g., %m-%d-%Y).
      2) If success rate is very low, try common alternatives.
      3) Finally fallback to pandas inference.
    Keeps errors='coerce' (conservative).
    """
    df = df.copy()
    date_cols = detect_date_columns(df)
    invalid_counts: dict[str, int] = {}

    # Common formats we may encounter across different CSVs
    common_formats = [
        raw_format,       # e.g. %m-%d-%Y
        "%Y-%m-%d",       # ISO
        "%m/%d/%Y",       # US slashes
        "%Y/%m/%d",       # ISO slashes
        "%d-%m-%Y",       # just in case
        "%d/%m/%Y",       # just in case
    ]

    for c in date_cols:
        # If already datetime dtype, keep it
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            parsed = df[c]
        else:
            s = df[c]

            non_null_before = int(s.notna().sum())

            # Work with strings for consistent parsing
            s_str = s.astype("string").str.strip()
            # optional small normalization
            # (do NOT replace '-' aggressively; just trim spaces)
            # s_str = s_str.str.replace(r"\s+", " ", regex=True)

            parsed = None

            # 1) Try RAW_DATE_FORMAT first (strict)
            p1 = pd.to_datetime(s_str, format=raw_format, errors="coerce")
            success1 = int(p1.notna().sum())
            success_rate1 = (success1 / non_null_before) if non_null_before else 1.0

            if success_rate1 >= 0.80:
                parsed = p1
            else:
                # 2) Try other common formats, but only if they improve
                best = p1
                best_success = success1

                for fmt in common_formats:
                    if fmt == raw_format:
                        continue
                    p = pd.to_datetime(s_str, format=fmt, errors="coerce")
                    succ = int(p.notna().sum())
                    if succ > best_success:
                        best = p
                        best_success = succ

                # If still too low, 3) fallback to inference
                best_rate = (best_success / non_null_before) if non_null_before else 1.0
                if best_rate < 0.80 and non_null_before > 0:
                    pinfer = pd.to_datetime(s_str, errors="coerce", infer_datetime_format=True)
                    succ_inf = int(pinfer.notna().sum())
                    if succ_inf > best_success:
                        best = pinfer
                        best_success = succ_inf

                parsed = best

            # Count invalids: values that were non-null but became NaT
            invalid = non_null_before - int(parsed.notna().sum())
            invalid_counts[c] = int(invalid)

        df[c] = parsed

    return df, date_cols, invalid_counts



def impute_descriptive_strings(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Minimal, explicitly allowed imputations for descriptive (non-financial) attributes.
    Current policy:
      - products.color: NULL -> "unknown"
    Returns counts of imputed cells per column.
    """
    df = df.copy()
    imputed: dict[str, int] = {}

    if table_name == "products" and "color" in df.columns:
        null_cnt = int(df["color"].isna().sum())
        if null_cnt > 0:
            df["color"] = df["color"].fillna("unknown")
        imputed["color"] = null_cnt

    return df, imputed


def add_orders_temporal_flags(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Orders-only anomaly handling:
      - flag if order_date > ship_date
      - add ship_lead_days = (ship_date - order_date).days
    """
    df = df.copy()
    metrics: dict[str, int] = {}

    if table_name == "orders" and {"order_date", "ship_date"}.issubset(df.columns):
        # Ensure datetime dtype (should already be after parse_date_columns)
        od = df["order_date"]
        sd = df["ship_date"]

        cond = (od.notna()) & (sd.notna()) & (od > sd)
        df["is_orderdate_gt_shipdate"] = cond

        # Compute lead days where both dates exist
        df["ship_lead_days"] = (sd - od).dt.days

        metrics["orderdate_gt_shipdate_cnt"] = int(cond.sum())

    return df, metrics


def standardize_table(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, dict]:
    """
    Apply:
      - snake_case columns
      - cast *_id to string
      - parse *_date using mm-dd-yyyy -> datetime
      - small safe imputations (products.color)
      - orders temporal anomaly flag + lead days
    """
    metrics: dict = {}

    df2 = normalize_columns_to_snake(df)

    # ID cast
    df2, id_cols = cast_id_columns_to_string(df2)
    metrics["id_cols"] = id_cols
    metrics["id_cols_count"] = len(id_cols)

    # Date parse
    df2, date_cols, invalid_counts = parse_date_columns(df2, raw_format=RAW_DATE_FORMAT)
    metrics["date_cols"] = date_cols
    metrics["date_cols_count"] = len(date_cols)
    metrics["invalid_date_counts"] = invalid_counts
    metrics["invalid_date_total"] = int(sum(invalid_counts.values()))

    # Allowed string imputations
    df2, imputed_counts = impute_descriptive_strings(df2, table_name)
    metrics["imputed_string_counts"] = imputed_counts
    metrics["imputed_string_total"] = int(sum(imputed_counts.values()))

    # Orders temporal flags
    df2, orders_metrics = add_orders_temporal_flags(df2, table_name)
    metrics.update(orders_metrics)

    return df2, metrics


# ----------------------------
# IO: load/save batch
# ----------------------------
def list_raw_csv_files(raw_dir: Path = RAW_DIR) -> list[Path]:
    files = sorted(raw_dir.glob("*.csv"))
    if ONLY_FILES is None:
        return files
    only = {x.lower() for x in ONLY_FILES}
    return [p for p in files if p.name.lower() in only]


def load_all_raw_tables(raw_dir: Path = RAW_DIR) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """
    Returns:
      tables: {snake_table_name: df_raw}
      enc_used: {snake_table_name: encoding_str}
    """
    tables: dict[str, pd.DataFrame] = {}
    enc_used: dict[str, str] = {}

    for csv_path in list_raw_csv_files(raw_dir):
        table_name = camel_to_snake(csv_path.stem)
        df, enc = read_csv_smart(csv_path)
        tables[table_name] = df
        enc_used[table_name] = enc

    return tables, enc_used


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def save_cleaned_tables(tables: dict[str, pd.DataFrame], *, out_dir: Path = OUT_DIR) -> None:
    """
    Save each standardized df to cleaned_data/{table}.csv using UTF-8 and ISO date format.
    """
    ensure_dirs()
    for table_name, df in tables.items():
        out_path = out_dir / f"{table_name}.csv"
        df.to_csv(out_path, index=False, encoding="utf-8", date_format=OUTPUT_DATE_FORMAT)


def build_cleaning_report(
    std_tables: dict[str, pd.DataFrame],
    metrics_map: dict[str, dict],
    enc_used: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for table_name, df in std_tables.items():
        m = metrics_map.get(table_name, {})
        rows.append(
            {
                "table": table_name,
                "rows": int(len(df)),
                "cols": int(df.shape[1]),
                "source_encoding": enc_used.get(table_name, ""),
                "id_cols_count": int(m.get("id_cols_count", 0)),
                "id_cols": ",".join(m.get("id_cols", [])),
                "date_cols_count": int(m.get("date_cols_count", 0)),
                "date_cols": ",".join(m.get("date_cols", [])),
                "invalid_date_total": int(m.get("invalid_date_total", 0)),
                "imputed_string_total": int(m.get("imputed_string_total", 0)),
                "imputed_string_counts": str(m.get("imputed_string_counts", {})),
                "orderdate_gt_shipdate_cnt": int(m.get("orderdate_gt_shipdate_cnt", 0)),
            }
        )
    return pd.DataFrame(rows).sort_values(["table"]).reset_index(drop=True)


def save_cleaning_report(report_df: pd.DataFrame) -> Path:
    ensure_dirs()
    out_path = ARTIFACT_DIR / "cleaning_report.csv"
    report_df.to_csv(out_path, index=False, encoding="utf-8")
    return out_path


def print_table_infos(tables: dict[str, pd.DataFrame]) -> None:
    for table_name, df in tables.items():
        print(f"\n=== {table_name} ===")
        df.info()


def main() -> None:
    raw_tables, enc_used = load_all_raw_tables(RAW_DIR)
    print(f"Loaded {len(raw_tables)} tables from: {RAW_DIR.resolve()}")
    print("Tables:", ", ".join(raw_tables.keys()))

    std_tables: dict[str, pd.DataFrame] = {}
    metrics_map: dict[str, dict] = {}

    for table_name, df in raw_tables.items():
        df_std, metrics = standardize_table(df, table_name)
        std_tables[table_name] = df_std
        metrics_map[table_name] = metrics

    # Print df.info() for each table
    print_table_infos(std_tables)

    # Save cleaned CSVs + report
    save_cleaned_tables(std_tables, out_dir=OUT_DIR)
    print(f"\nSaved cleaned CSVs to: {OUT_DIR.resolve()}")

    report_df = build_cleaning_report(std_tables, metrics_map, enc_used)
    report_path = save_cleaning_report(report_df)
    print(f"Saved cleaning report to: {report_path.resolve()}")

    # Quick peek
    if "orders" in std_tables:
        print("\n--- orders temporal anomalies (sample) ---")
        od = std_tables["orders"]
        if "is_orderdate_gt_shipdate" in od.columns:
            print(od.loc[od["is_orderdate_gt_shipdate"] == True, ["order_id", "order_date", "ship_date", "ship_lead_days"]].head(10))


if __name__ == "__main__":
    main()
