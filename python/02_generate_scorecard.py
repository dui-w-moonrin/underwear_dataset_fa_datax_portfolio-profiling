#!/usr/bin/env python3
"""
Option B (one-click): Generate Data Quality Scorecard for Underwear dataset in PostgreSQL.

What it does
- Connects to PostgreSQL (target DB must already contain your stg.* views).
- Runs the scorecard SQL pack in order.
- Exports dq.scorecard_v to artifacts/scorecard.csv (and optional dq.fk_orphans_detail).

Usage (Windows PowerShell)
  # 1) set env vars (recommended)
  $env:PGHOST="127.0.0.1"
  $env:PGPORT="5432"
  $env:PGUSER="postgres"
  $env:PGPASSWORD="your_password"
  $env:PGDATABASE="underwear_fa_profiling"

  # 2) run from repo root
  python python/02_generate_scorecard.py

Alternative: provide DATABASE_URL
  $env:DATABASE_URL="postgresql://postgres:your_password@127.0.0.1:5432/underwear_fa_profiling"
  python python/02_generate_scorecard.py

Dependencies
  pip install psycopg[binary] pandas sqlalchemy

Notes
- This script expects your SQL pack files exist under: sql/10_scorecard/
  (00_create_scorecard_tables.sql, 01_nulls.sql, 02_pk_dupes.sql, 03_date_range.sql,
   04_negative_flags.sql, 05_fk_orphans.sql, 99_export_scorecard_view.sql)
- Exports to artifacts/ by default.
"""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

try:
    import psycopg
except ImportError as e:
    raise SystemExit("Missing dependency psycopg. Run: pip install psycopg[binary]") from e

try:
    from sqlalchemy import create_engine
except ImportError as e:
    raise SystemExit("Missing dependency sqlalchemy. Run: pip install sqlalchemy") from e


SQL_RUN_ORDER = [
    "00_create_scorecard_tables.sql",
    "01_nulls.sql",
    "02_pk_dupes.sql",
    "03_date_range.sql",
    "04_negative_flags.sql",
    "05_fk_orphans.sql",
    "99_export_scorecard_view.sql",
]


def build_db_url_from_env() -> Optional[str]:
    """
    Prefer DATABASE_URL if present.
    Otherwise build from PG* env vars.
    """
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    db = os.getenv("PGDATABASE")

    if not all([host, user, password, db]):
        return None

    # psycopg / sqlalchemy accept the same URL format
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def normalize_sqlalchemy_url(url: str) -> str:
    """
    Ensure URL works for SQLAlchemy with psycopg driver.
    Accept:
      - postgresql://... (we'll convert)
      - postgresql+psycopg://...
    """
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def normalize_psycopg_url(url: str) -> str:
    """
    psycopg.connect() accepts:
      - postgresql://...
      - postgresql+psycopg://... (NOT accepted)
    So convert to postgresql:// for psycopg.
    """
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def read_sql_file(path: Path) -> str:
    txt = path.read_text(encoding="utf-8")
    # cheap safety: ignore empty/whitespace-only
    return txt.strip()


def exec_sql(conn: "psycopg.Connection", sql: str, label: str) -> None:
    """
    Execute possibly-multi-statement SQL.
    psycopg can execute multi statements in a single execute() for simple scripts,
    but DO blocks and function defs are fine.
    """
    if not sql:
        print(f" - Skipped empty: {label}")
        return
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f" - OK: {label}")


def export_view_to_csv(db_url_sqlalchemy: str, view_sql: str, out_csv: Path) -> None:
    engine = create_engine(db_url_sqlalchemy)
    df = pd.read_sql(view_sql, engine)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f" - Exported: {out_csv.as_posix()}  (rows={len(df):,})")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate DQ scorecard (Option B)")
    parser.add_argument(
        "--db-url",
        default=None,
        help="DB URL. If omitted, uses DATABASE_URL or PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE env vars.",
    )
    parser.add_argument(
        "--sql-dir",
        default="sql/10_scorecard",
        help="Folder containing scorecard SQL scripts.",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts",
        help="Output folder for scorecard.csv",
    )
    parser.add_argument(
        "--export-fk-detail",
        action="store_true",
        help="Also export dq.fk_orphans_detail to artifacts/fk_orphans_detail.csv",
    )

    args = parser.parse_args(argv)

    # Resolve db url
    url = args.db_url or build_db_url_from_env()
    if not url:
        print(
            "ERROR: No DB connection info found.\n"
            "Set DATABASE_URL or PGHOST/PGUSER/PGPASSWORD/PGDATABASE (and optional PGPORT),\n"
            "or pass --db-url.\n"
            "Example:\n"
            '  $env:DATABASE_URL="postgresql://postgres:pass@127.0.0.1:5432/underwear_fa_profiling"\n'
        )
        return 2

    db_url_sa = normalize_sqlalchemy_url(url)
    db_url_pg = normalize_psycopg_url(url)

    sql_dir = Path(args.sql_dir)
    out_dir = Path(args.out_dir)

    # Basic checks
    missing = [f for f in SQL_RUN_ORDER if not (sql_dir / f).exists()]
    if missing:
        print("ERROR: Missing SQL files in", sql_dir.as_posix())
        for f in missing:
            print(" -", f)
        return 3

    print("== Connect ==")
    # psycopg connect uses postgresql://
    with psycopg.connect(db_url_pg, autocommit=False) as conn:
        # Run scripts
        print("== Run SQL pack ==")
        for fname in SQL_RUN_ORDER:
            path = sql_dir / fname
            sql = read_sql_file(path)
            exec_sql(conn, sql, fname)

    # Export scorecard
    print("== Export artifacts ==")
    export_view_to_csv(
        db_url_sa,
        "select * from dq.scorecard_v order by table_schema, table_name",
        out_dir / "scorecard.csv",
    )

    if args.export_fk_detail:
        export_view_to_csv(
            db_url_sa,
            "select * from dq.fk_orphans_detail order by child_schema, child_table, child_fk_col",
            out_dir / "fk_orphans_detail.csv",
        )

    print("DONE ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
