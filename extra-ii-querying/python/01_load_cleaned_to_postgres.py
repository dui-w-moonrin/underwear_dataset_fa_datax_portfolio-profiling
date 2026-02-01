"""
01_load_cleaned_to_postgres.py

Load cleaned CSV files from extra-i-cleaning/cleaned_data into Postgres.

Key features:
- Reads .env from project root automatically (no human error).
- Default schema = clean (override with --schema).
- Auto-adjust chunksize to avoid Postgres bind-parameter limit (65535).
- Supports --skip and --only.
- Uses SQLAlchemy + psycopg driver.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# -----------------------------
# Paths / Env
# -----------------------------

def project_root() -> Path:
    # file: <root>/extra-ii-querying/python/01_load_cleaned_to_postgres.py
    # parents[0]=python, parents[1]=extra-ii-querying, parents[2]=root
    return Path(__file__).resolve().parents[2]


def read_dotenv(dotenv_path: Path) -> Dict[str, str]:
    """
    Minimal .env parser (no dependency on python-dotenv).
    Supports lines like KEY=VALUE, ignores comments and blanks.
    """
    env: Dict[str, str] = {}
    if not dotenv_path.exists():
        return env

    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            env[k] = v
    return env


def get_env_value(key: str, dotenv: Dict[str, str], default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key) or dotenv.get(key) or default


@dataclass
class PgConfig:
    host: str
    port: int
    user: str
    password: str
    maintdb: str
    db: str

    def sqlalchemy_url(self, db_override: Optional[str] = None) -> str:
        database = db_override or self.db
        # SQLAlchemy 2 + psycopg (v3)
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{database}"


def load_pg_config() -> PgConfig:
    root = project_root()
    dotenv_path = root / ".env"
    dotenv = read_dotenv(dotenv_path)

    host = get_env_value("PGHOST", dotenv, "localhost")
    port = int(get_env_value("PGPORT", dotenv, "5432") or "5432")
    user = get_env_value("PGUSER", dotenv, "postgres")
    password = get_env_value("PGPASSWORD", dotenv, "")
    maintdb = get_env_value("PGMAINTDB", dotenv, "postgres")
    db = get_env_value("PGDB", dotenv, "")

    if not password:
        raise RuntimeError("PGPASSWORD is empty. Please set it in .env (PGPASSWORD=...).")
    if not db:
        raise RuntimeError("PGDB is empty. Please set it in .env (PGDB=...).")

    return PgConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        maintdb=maintdb,
        db=db,
    )


# -----------------------------
# Postgres helpers
# -----------------------------

def ensure_database_exists(cfg: PgConfig) -> None:
    """
    Optional safety: create target DB if missing.
    If user doesn't have privilege, it will just fail silently with a clear message.
    """
    url = cfg.sqlalchemy_url(cfg.maintdb)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            exists = conn.execute(
                text("select 1 from pg_database where datname = :db"),
                {"db": cfg.db},
            ).scalar()
            if not exists:
                conn.execute(text(f'create database "{cfg.db}"'))
                print(f"[OK] created database: {cfg.db}")
    except Exception as e:
        # Not fatal; maybe DB already exists or no privilege.
        print(f"[WARN] ensure_database_exists skipped/failed: {e}")
    finally:
        engine.dispose()


def make_engine(cfg: PgConfig) -> Engine:
    url = cfg.sqlalchemy_url(cfg.db)
    return create_engine(url, pool_pre_ping=True)


def ensure_schema(engine: Engine, schema: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f'create schema if not exists "{schema}"'))


# -----------------------------
# CSV loading
# -----------------------------

def list_csv_files(cleaned_dir: Path) -> List[Path]:
    return sorted([p for p in cleaned_dir.glob("*.csv") if p.is_file()])


def table_name_from_csv(path: Path) -> str:
    # customers_clean.csv -> customers_clean (keep as-is)
    # If you prefer stripping suffix, change here.
    return path.stem


def safe_chunksize(requested: int, ncols: int, bind_limit: int = 65535) -> int:
    """
    Postgres prepared statement bind parameter limit ~ 65535.
    Inserting N rows with C columns uses N*C binds (roughly).
    Keep N <= floor(bind_limit / max(1, C)).
    """
    if requested <= 0:
        return 1000
    if ncols <= 0:
        return requested
    max_rows = max(1, bind_limit // max(1, ncols))
    return max(1, min(requested, max_rows))


def load_one_csv(
    engine: Engine,
    csv_path: Path,
    schema: str,
    if_exists: str,
    chunksize_req: int,
    verbose: bool = True,
) -> Tuple[str, int]:
    table = table_name_from_csv(csv_path)

    # Read header quickly to estimate columns (for safe chunksize)
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    ncols = len(header)

    chunksize = safe_chunksize(chunksize_req, ncols)
    if verbose and chunksize != chunksize_req:
        print(f"[INFO] Adjust chunksize for {table}: req={chunksize_req} -> safe={chunksize} (cols={ncols})")

    if verbose:
        print(f"--- Loading: {csv_path.name}  ->  {schema}.{table}")

    # Use dtype=str to avoid pandas guessing issues; let Postgres store as text by default.
    # If you want typed columns later, we can add a typing map stage.
    total_rows = 0
    first = True

    for chunk in pd.read_csv(csv_path, chunksize=chunksize, dtype=str, keep_default_na=False):
        # Normalize empty strings to None (optional)
        chunk = chunk.replace({"": None})

        # first chunk decides replace/append behavior
        this_if_exists = if_exists if first else "append"
        chunk.to_sql(
            name=table,
            con=engine,
            schema=schema,
            if_exists=this_if_exists,
            index=False,
            method="multi",
        )
        total_rows += len(chunk)
        first = False

    if verbose:
        print(f"[OK] {schema}.{table} rows={total_rows}")
    return table, total_rows


# -----------------------------
# CLI / main
# -----------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    root = project_root()
    default_cleaned = root / "extra-i-cleaning" / "cleaned_data"

    p = argparse.ArgumentParser(description="Load cleaned CSVs into Postgres.")
    p.add_argument("--cleaned-dir", default=str(default_cleaned), help="Path to cleaned_data directory")
    p.add_argument("--schema", default="clean", help="Target schema (default: clean)")
    p.add_argument("--if-exists", default="replace", choices=["replace", "append", "fail"], help="to_sql if_exists")
    p.add_argument("--chunksize", type=int, default=1000, help="CSV read chunksize (auto-adjusted for bind limit)")
    p.add_argument("--skip", nargs="*", default=[], help="Table names (csv stem) to skip")
    p.add_argument("--only", nargs="*", default=[], help="If provided, load only these table names (csv stem)")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    cleaned_dir = Path(args.cleaned_dir).resolve()
    schema = args.schema
    if_exists = args.if_exists
    chunksize = args.chunksize
    skip = set(args.skip or [])
    only = set(args.only or [])

    print("=== Load Cleaned CSVs to Postgres ===")
    print(f"cleaned_dir : {cleaned_dir}")
    print(f"schema      : {schema}")
    print(f"if_exists   : {if_exists}")
    print(f"chunksize   : {chunksize}")
    print(f"skip        : {sorted(skip)}")

    if not cleaned_dir.exists():
        print(f"[ERROR] cleaned_dir not found: {cleaned_dir}")
        return 2

    cfg = load_pg_config()
    # Optional: ensure DB exists
    ensure_database_exists(cfg)

    engine = make_engine(cfg)
    try:
        ensure_schema(engine, schema)

        csv_files = list_csv_files(cleaned_dir)
        if not csv_files:
            print(f"[WARN] No CSV files found in: {cleaned_dir}")
            return 0

        loaded: List[Tuple[str, int]] = []
        skipped: List[str] = []

        for csv_path in csv_files:
            table = table_name_from_csv(csv_path)

            if only and table not in only:
                skipped.append(table)
                continue
            if table in skip:
                skipped.append(table)
                continue

            try:
                t, rows = load_one_csv(
                    engine=engine,
                    csv_path=csv_path,
                    schema=schema,
                    if_exists=if_exists,
                    chunksize_req=chunksize,
                    verbose=True,
                )
                loaded.append((t, rows))
            except Exception as e:
                print(f"[ERROR] failed loading {csv_path.name} -> {schema}.{table}: {e}")
                return 1

        print("\n=== Summary ===")
        print(f"Loaded tables: {len(loaded)}")
        for t, rows in loaded:
            print(f" - {schema}.{t}: {rows} rows")

        print(f"Skipped tables: {len(skipped)}")
        if skipped:
            print(" - " + ", ".join(skipped))

        total_rows = sum(r for _, r in loaded)
        print(f"Total rows loaded: {total_rows}")
        print("\nDone.")
        return 0

    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
