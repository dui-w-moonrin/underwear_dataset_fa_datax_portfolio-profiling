from __future__ import annotations

import os
from pathlib import Path
from io import StringIO
import pandas as pd
import psycopg
from psycopg import sql as psql

from dotenv import load_dotenv
load_dotenv()  # auro read .env from root

def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Missing env var: {name}")
    return v

HOST = require_env("PGHOST")
PORT = int(require_env("PGPORT"))
USER = require_env("PGUSER")
PASSWORD = require_env("PGPASSWORD")
MAINT_DB = require_env("PGMAINTDB")
TARGET_DB = require_env("PGDB")

RAW_DIR = Path("raw_data")

SQL_SETUP_DIR = Path("sql/00_setup")
SCHEMAS_SQL = SQL_SETUP_DIR / "01_create_schemas.sql"
STG_VIEWS_SQL_FILE = SQL_SETUP_DIR / "02_create_stg_views.sql"

# Kaggle files: customers/employees are UTF-16; most others UTF-8 with BOM.
ENCODING_MAP = {
    "customers.csv": "utf-16",
    "employees.csv": "utf-16",
}
DEFAULT_ENCODING = "utf-8-sig"  # handles UTF-8 BOM nicely

TABLE_FILES = {
    "customers": "customers.csv",
    "employees": "employees.csv",
    "inventory_transactions": "inventory_transactions.csv",
    "order_details": "order_details.csv",
    "orders": "orders.csv",
    "payment_methods": "payment_methods.csv",
    "payments": "payments.csv",
    "products": "products.csv",
    "purchase_orders": "purchase_orders.csv",
    "shipping_methods": "shipping_methods.csv",
    "suppliers": "suppliers.csv",
}


def conn_str(dbname: str) -> str:
    return f"host={HOST} port={PORT} dbname={dbname} user={USER} password={PASSWORD}"


def run_sql_file(con: psycopg.Connection, path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path.as_posix()}")
    sql_text = path.read_text(encoding="utf-8")
    with con.cursor() as cur:
        cur.execute(sql_text)
    con.commit()
    print(f"✅ ran sql: {path.as_posix()}")


def drop_and_create_database():
    """
    Rebuild TARGET_DB safely.
    - Terminates other sessions on TARGET_DB (fixes 'database is being accessed by other users')
    - Drops and recreates DB
    """
    with psycopg.connect(conn_str(MAINT_DB), autocommit=True) as con:
        with con.cursor() as cur:
            # terminate sessions
            cur.execute(
                """
                select pg_terminate_backend(pid)
                from pg_stat_activity
                where datname = %s
                  and pid <> pg_backend_pid();
                """,
                (TARGET_DB,),
            )

            # drop if exists + create
            cur.execute(psql.SQL("drop database if exists {}").format(psql.Identifier(TARGET_DB)))
            cur.execute(psql.SQL("create database {}").format(psql.Identifier(TARGET_DB)))

    print(f"✅ rebuilt database: {TARGET_DB}")


def copy_df_to_table(con: psycopg.Connection, df: pd.DataFrame, full_table: str):
    """
    Fast load using COPY from an in-memory CSV buffer (UTF-8).
    Works for any original file encoding because pandas already decoded it.
    """
    buf = StringIO()
    df.to_csv(buf, index=False)  # header included
    buf.seek(0)

    cols = list(df.columns)
    col_list = ", ".join([f'"{c}"' for c in cols])  # raw columns are quoted
    copy_sql = f'copy {full_table} ({col_list}) from stdin with (format csv, header true);'

    with con.cursor() as cur:
        cur.execute(f"truncate table {full_table};")
        with cur.copy(copy_sql) as cp:
            cp.write(buf.getvalue())
    con.commit()


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"raw_data folder not found: {RAW_DIR.resolve()}")

    # 0) rebuild database
    drop_and_create_database()

    # 1) connect target db
    with psycopg.connect(conn_str(TARGET_DB)) as con:
        # 2) run create schemas/tables (raw + stg schema + raw tables)
        run_sql_file(con, SCHEMAS_SQL)

        # 3) load csv into raw.*
        for table, filename in TABLE_FILES.items():
            path = RAW_DIR / filename
            if not path.exists():
                raise FileNotFoundError(f"missing file: {path}")

            enc = ENCODING_MAP.get(filename, DEFAULT_ENCODING)
            df = pd.read_csv(path, encoding=enc)
            copy_df_to_table(con, df, f"raw.{table}")
            print(f"✅ loaded raw.{table}: {len(df):,} rows (encoding={enc})")

        # 4) run stg views (นี่แหละที่ต้องเป็นเวอร์ชัน normalize *_id)
        run_sql_file(con, STG_VIEWS_SQL_FILE)

    print("🎉 All done. raw tables + stg views are ready.")


if __name__ == "__main__":
    main()
