import os
from pathlib import Path
from io import StringIO
import pandas as pd
import psycopg


# ---------- CONFIG ----------
HOST = os.getenv("PGHOST", "localhost")
PORT = int(os.getenv("PGPORT", "5432"))
USER = os.getenv("PGUSER", "postgres")
PASSWORD = os.getenv("PGPASSWORD", "postgres")  # เปลี่ยนตามเครื่องน้องดุ๋ย
MAINT_DB = os.getenv("PGMAINTDB", "postgres")   # maintenance db
TARGET_DB = os.getenv("PGDB", "underwear_fa_profiling")

RAW_DIR = Path("raw_data")

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


RAW_DDL = """
create schema if not exists raw;
create schema if not exists stg;

create table if not exists raw.customers (
  "CustomerID" text,
  "CustomerName" text,
  "Region" text,
  "Country" text,
  "PriceCategory" text,
  "CustomerClass" text,
  "LeadSource" text,
  "Discontinued" text
);

create table if not exists raw.employees (
  "EmployeeID" text,
  "EmployeeName" text
);

create table if not exists raw.inventory_transactions (
  "TransactionID" text,
  "ProductID" text,
  "PurchaseOrderID" text,
  "MissingID" text,
  "TransactionDate" text,
  "UnitPurchasePrice" text,
  "QuantityOrdered" text,
  "QuantityReceived" text,
  "QuantityMissing" text
);

create table if not exists raw.order_details (
  "OrderDetailID" text,
  "OrderID" text,
  "ProductID" text,
  "QuantitySold" text,
  "UnitSalesPrice" text
);

create table if not exists raw.orders (
  "OrderID" text,
  "CustomerID" text,
  "EmployeeID" text,
  "ShippingMethodID" text,
  "OrderDate" text,
  "ShipDate" text,
  "FreightCharge" text
);

create table if not exists raw.payment_methods (
  "PaymentMethodID" text,
  "PaymentMethod" text
);

create table if not exists raw.payments (
  "PaymentID" text,
  "OrderID" text,
  "PaymentMethodID" text,
  "PaymentDate" text,
  "PaymentAmount" text
);

create table if not exists raw.products (
  "ProductID" text,
  "ProductName" text,
  "Color" text,
  "ModelDescription" text,
  "FabricDescription" text,
  "Category" text,
  "Gender" text,
  "ProductLine" text,
  "Weight" text,
  "Size" text,
  "PackSize" text,
  "Status" text,
  "InventoryDate" text,
  "PurchasePrice" text
);

create table if not exists raw.purchase_orders (
  "PurchaseOrderID" text,
  "SupplierID" text,
  "EmployeeID" text,
  "ShippingMethodID" text,
  "OrderDate" text
);

create table if not exists raw.shipping_methods (
  "ShippingMethodID" text,
  "ShippingMethod" text
);

create table if not exists raw.suppliers (
  "SupplierID" text,
  "SupplierName" text
);
"""


STG_VIEWS_SQL = """
create or replace view stg.customers as
select
  nullif(trim("CustomerID"), '')          as customer_id,
  nullif(trim("CustomerName"), '')        as customer_name,
  nullif(trim("Region"), '')              as region,
  nullif(trim("Country"), '')             as country,
  nullif(trim("PriceCategory"), '')       as price_category,
  nullif(trim("CustomerClass"), '')       as customer_class,
  nullif(trim("LeadSource"), '')          as lead_source,
  nullif(trim("Discontinued"), '')        as discontinued
from raw.customers;

create or replace view stg.employees as
select
  nullif(trim("EmployeeID"), '')          as employee_id,
  nullif(trim("EmployeeName"), '')        as employee_name
from raw.employees;

create or replace view stg.inventory_transactions as
select
  nullif(trim("TransactionID"), '')       as transaction_id,
  nullif(trim("ProductID"), '')           as product_id,
  nullif(trim("PurchaseOrderID"), '')     as purchase_order_id,
  nullif(trim("MissingID"), '')           as missing_id,
  nullif(trim("TransactionDate"), '')     as transaction_date,
  nullif(trim("UnitPurchasePrice"), '')   as unit_purchase_price,
  nullif(trim("QuantityOrdered"), '')     as quantity_ordered,
  nullif(trim("QuantityReceived"), '')    as quantity_received,
  nullif(trim("QuantityMissing"), '')     as quantity_missing
from raw.inventory_transactions;

create or replace view stg.order_details as
select
  nullif(trim("OrderDetailID"), '')       as order_detail_id,
  nullif(trim("OrderID"), '')             as order_id,
  nullif(trim("ProductID"), '')           as product_id,
  nullif(trim("QuantitySold"), '')        as quantity_sold,
  nullif(trim("UnitSalesPrice"), '')      as unit_sales_price
from raw.order_details;

create or replace view stg.orders as
select
  nullif(trim("OrderID"), '')             as order_id,
  nullif(trim("CustomerID"), '')          as customer_id,
  nullif(trim("EmployeeID"), '')          as employee_id,
  nullif(trim("ShippingMethodID"), '')    as shipping_method_id,
  nullif(trim("OrderDate"), '')           as order_date,
  nullif(trim("ShipDate"), '')            as ship_date,
  nullif(trim("FreightCharge"), '')       as freight_charge
from raw.orders;

create or replace view stg.payment_methods as
select
  nullif(trim("PaymentMethodID"), '')     as payment_method_id,
  nullif(trim("PaymentMethod"), '')       as payment_method
from raw.payment_methods;

create or replace view stg.payments as
select
  nullif(trim("PaymentID"), '')           as payment_id,
  nullif(trim("OrderID"), '')             as order_id,
  nullif(trim("PaymentMethodID"), '')     as payment_method_id,
  nullif(trim("PaymentDate"), '')         as payment_date,
  nullif(trim("PaymentAmount"), '')       as payment_amount
from raw.payments;

create or replace view stg.products as
select
  nullif(trim("ProductID"), '')           as product_id,
  nullif(trim("ProductName"), '')         as product_name,
  nullif(trim("Color"), '')               as color,
  nullif(trim("ModelDescription"), '')    as model_description,
  nullif(trim("FabricDescription"), '')   as fabric_description,
  nullif(trim("Category"), '')            as category,
  nullif(trim("Gender"), '')              as gender,
  nullif(trim("ProductLine"), '')         as product_line,
  nullif(trim("Weight"), '')              as weight,
  nullif(trim("Size"), '')                as size,
  nullif(trim("PackSize"), '')            as pack_size,
  nullif(trim("Status"), '')              as status,
  nullif(trim("InventoryDate"), '')       as inventory_date,
  nullif(trim("PurchasePrice"), '')       as purchase_price
from raw.products;

create or replace view stg.purchase_orders as
select
  nullif(trim("PurchaseOrderID"), '')     as purchase_order_id,
  nullif(trim("SupplierID"), '')          as supplier_id,
  nullif(trim("EmployeeID"), '')          as employee_id,
  nullif(trim("ShippingMethodID"), '')    as shipping_method_id,
  nullif(trim("OrderDate"), '')           as order_date
from raw.purchase_orders;

create or replace view stg.shipping_methods as
select
  nullif(trim("ShippingMethodID"), '')    as shipping_method_id,
  nullif(trim("ShippingMethod"), '')      as shipping_method
from raw.shipping_methods;

create or replace view stg.suppliers as
select
  nullif(trim("SupplierID"), '')          as supplier_id,
  nullif(trim("SupplierName"), '')        as supplier_name
from raw.suppliers;
"""


def conn_str(dbname: str) -> str:
    return f"host={HOST} port={PORT} dbname={dbname} user={USER} password={PASSWORD}"


def create_database_if_needed():
    with psycopg.connect(conn_str(MAINT_DB), autocommit=True) as con:
        with con.cursor() as cur:
            cur.execute("select 1 from pg_database where datname = %s", (TARGET_DB,))
            exists = cur.fetchone() is not None
            if exists:
                # recreate clean
                cur.execute(f"drop database {TARGET_DB};")
            cur.execute(f"create database {TARGET_DB};")
            print(f"✅ created database: {TARGET_DB}")


def copy_df_to_table(con, df: pd.DataFrame, full_table: str):
    """
    Fast load using COPY from an in-memory CSV buffer (UTF-8).
    Works for any original file encoding because pandas already decoded it.
    """
    buf = StringIO()
    df.to_csv(buf, index=False)  # header included
    buf.seek(0)

    cols = list(df.columns)
    col_list = ", ".join([f'"{c}"' for c in cols])  # raw columns are quoted
    sql = f'copy {full_table} ({col_list}) from stdin with (format csv, header true);'

    with con.cursor() as cur:
        cur.execute(f"truncate table {full_table};")
        with cur.copy(sql) as cp:
            cp.write(buf.getvalue())
    con.commit()


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"raw_data folder not found: {RAW_DIR.resolve()}")

    create_database_if_needed()

    with psycopg.connect(conn_str(TARGET_DB)) as con:
        with con.cursor() as cur:
            cur.execute(RAW_DDL)
            con.commit()
            print("✅ created schemas + raw tables")

        for table, filename in TABLE_FILES.items():
            path = RAW_DIR / filename
            if not path.exists():
                raise FileNotFoundError(f"missing file: {path}")

            enc = ENCODING_MAP.get(filename, DEFAULT_ENCODING)
            df = pd.read_csv(path, encoding=enc)
            copy_df_to_table(con, df, f"raw.{table}")
            print(f"✅ loaded raw.{table}: {len(df):,} rows (encoding={enc})")

        with con.cursor() as cur:
            cur.execute(STG_VIEWS_SQL)
            con.commit()
            print("✅ created stg views")

    print("🎉 All done. You can now query stg.* without quoted identifiers.")


if __name__ == "__main__":
    main()