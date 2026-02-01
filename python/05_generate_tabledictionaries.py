"""
05_generate_tabledictionaries.py

Batch generator:
- For a configured list of (schema, table, column),
  export value distribution (dictionary) to artifacts/tabledictionaries/
- Also write dictionary_index.csv as a summary per column.

Output files:
- artifacts/tabledictionaries/<schema>__<table>__<column>__dict.csv
- artifacts/tabledictionaries/dictionary_index.csv

Value normalization:
- NULL   -> [NULL]
- blank/whitespace -> [BLANK]
- else trimmed text

Connection:
- Loads .env (if exists at project root) then reads:
  PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDB
"""

from __future__ import annotations

import os
import csv
from pathlib import Path
from typing import Iterable, List, Tuple

import psycopg


# -------------------------
# CONFIG (edit this list)
# -------------------------
# Put only columns you really want (start 15-30 cols is enough).
DICT_TARGETS: List[Tuple[str, str, str]] = [
    # ("stg", "customers", "country"),
    # ("stg", "customers", "price_category"),
    # ("stg", "customers", "customer_class"),
    # ("stg", "customers", "lead_source"),
    # ("stg", "customers", "discontinued"),
    # ("stg", "products", "status"),
    # ("stg", "orders", "shipping_method_id"),
    # ("stg", "payments", "payment_method_id"),
]

# Output under artifacts (as you requested)
OUT_DIR = Path("artifacts/tabledictionaries")

# Limit for each dictionary file (None = full)
TOP_N = None  # e.g. 300


# -------------------------
# .env loader (no extra deps)
# -------------------------
def load_dotenv_simple(dotenv_path: Path = Path(".env")) -> None:
    """
    Minimal .env loader:
    - supports KEY=VALUE (VALUE may be quoted with " or ')
    - ignores blank lines and comments starting with #
    - does NOT override existing os.environ values
    """
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        # strip surrounding quotes
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]

        # do not override if already set in environment
        os.environ.setdefault(key, val)


# -------------------------
# ENV helpers
# -------------------------
def require_env(key: str) -> str:
    val = os.getenv(key)
    if val is None or str(val).strip() == "":
        raise SystemExit(
            f"Missing required env var: {key}\n"
            f"Tip: put it in .env at repo root (or export it in your shell)."
        )
    return val


def conn_str() -> str:
    host = require_env("PGHOST")
    port = require_env("PGPORT")
    user = require_env("PGUSER")
    password = require_env("PGPASSWORD")
    db = require_env("PGDB")
    return f"host={host} port={port} dbname={db} user={user} password={password}"


# -------------------------
# SQL builders (safe-ish)
# -------------------------
def q_ident(name: str) -> str:
    """
    Minimal identifier validation: allow letters, digits, underscore only.
    (Because we control DICT_TARGETS, this is mostly a sanity check.)
    """
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Unsafe identifier: {name}")
    return name


def build_dict_sql(schema: str, table: str, col: str, top_n: int | None) -> str:
    s = q_ident(schema)
    t = q_ident(table)
    c = q_ident(col)

    limit_clause = f"limit {int(top_n)}" if top_n is not None else ""

    return f"""
with x as (
  select
    case
      when {c} is null then '[NULL]'
      when trim(({c})::text) = '' then '[BLANK]'
      else trim(({c})::text)
    end as col_value
  from {s}.{t}
)
select
  col_value,
  count(*)::bigint as cnt
from x
group by 1
order by cnt desc, col_value
{limit_clause};
""".strip()


def build_index_sql(schema: str, table: str, col: str) -> str:
    s = q_ident(schema)
    t = q_ident(table)
    c = q_ident(col)

    return f"""
with base as (
  select
    case
      when {c} is null then '[NULL]'
      when trim(({c})::text) = '' then '[BLANK]'
      else trim(({c})::text)
    end as col_value
  from {s}.{t}
),
agg as (
  select
    count(*)::bigint as total_rows,
    count(distinct col_value)::bigint as distinct_cnt_mapped,
    sum((col_value = '[NULL]')::int)::bigint as null_cnt,
    sum((col_value = '[BLANK]')::int)::bigint as blank_cnt
  from base
),
top1 as (
  select col_value as top_value, count(*)::bigint as top_cnt
  from base
  group by 1
  order by top_cnt desc, top_value
  limit 1
)
select
  '{s}'::text as table_schema,
  '{t}'::text as table_name,
  '{c}'::text as column_name,
  a.total_rows,
  a.distinct_cnt_mapped,
  a.null_cnt,
  a.blank_cnt,
  t.top_value,
  t.top_cnt,
  case when a.total_rows = 0 then 0
       else round((t.top_cnt::numeric * 100.0) / a.total_rows::numeric, 2)
  end as top_pct
from agg a
cross join top1 t;
""".strip()


# -------------------------
# IO helpers
# -------------------------
def write_rows_to_csv(path: Path, headers: List[str], rows: Iterable[Tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(list(r))


# -------------------------
# Main
# -------------------------
def main() -> int:
    # load .env first (if exists). env vars already set in shell will win.
    load_dotenv_simple(Path(".env"))

    if not DICT_TARGETS:
        raise SystemExit(
            "DICT_TARGETS is empty.\n"
            "Edit python/05_generate_tabledictionaries.py and add targets."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index_rows: List[Tuple] = []
    index_headers = [
        "table_schema",
        "table_name",
        "column_name",
        "total_rows",
        "distinct_cnt_mapped",
        "null_cnt",
        "blank_cnt",
        "top_value",
        "top_cnt",
        "top_pct",
    ]

    with psycopg.connect(conn_str()) as con:
        for (schema, table, col) in DICT_TARGETS:
            print(f"== {schema}.{table}.{col} ==")

            # 1) dictionary file
            dict_sql = build_dict_sql(schema, table, col, TOP_N)
            with con.cursor() as cur:
                cur.execute(dict_sql)
                rows = cur.fetchall()

            out_name = f"{schema}__{table}__{col}__dict.csv"
            out_path = OUT_DIR / out_name
            write_rows_to_csv(out_path, ["col_value", "cnt"], rows)
            print(f"  - OK: {out_path.as_posix()} (rows={len(rows)})")

            # 2) index row
            idx_sql = build_index_sql(schema, table, col)
            with con.cursor() as cur:
                cur.execute(idx_sql)
                idx = cur.fetchone()
                if idx:
                    index_rows.append(idx)

    # Write summary index
    index_path = OUT_DIR / "dictionary_index.csv"
    write_rows_to_csv(index_path, index_headers, index_rows)
    print(f"\nDone. index={index_path.as_posix()} targets={len(DICT_TARGETS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())