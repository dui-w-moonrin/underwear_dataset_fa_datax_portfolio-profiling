# Import CSV into PostgreSQL (Raw + Staging Views)

This project supports two reproducible import paths:

- **Option A (SQL-first / Manual):** Create schemas + import CSV into `raw` using DBeaver or `psql \copy`, then create `stg` views.
- **Option B (Fastlane / Python):** One command rebuild (create DB + raw tables + load CSV + create `stg` views).

---

## Prerequisites

- PostgreSQL running locally
- A target database: `underwear_fa_profiling` (new database; does not reuse existing default DB)
- Project folder structure:
  - `raw_data/*.csv` (11 files)
  - `sql/00_setup/*.sql`
  - `python/01_load_raw_to_postgres.py` (for Option B)

---

## Option A — SQL-first / Manual Import

### Step A1 — Create schemas + raw tables

Run:

- `sql/00_setup/01_create_schemas.sql`

This creates:
- schema `raw` (for raw CSV as-is)
- schema `stg` (for staging views / normalized column naming)

> Note: **Raw columns preserve original CSV headers** (often CamelCase). In PostgreSQL, quoted identifiers are case-sensitive, so `"CustomerID"` is different from `CustomerID`.  
> To avoid quoting everywhere, we create `stg` views with snake_case column names (e.g., `customer_id`).

### Step A2 — Import CSV into `raw` schema

#### Option A2.1 — Using `psql \copy` (recommended CLI)

Examples (adjust `{ABS_PATH}` to your local repo path):

```sql
\copy raw.orders from '{ABS_PATH}/raw_data/orders.csv'
with (format csv, header true, encoding 'UTF8');

\copy raw.customers from '{ABS_PATH}/raw_data/customers.csv'
with (format csv, header true, encoding 'UTF16');

\copy raw.employees from '{ABS_PATH}/raw_data/employees.csv'
with (format csv, header true, encoding 'UTF16');
```

Encoding note:
- `customers.csv`, `employees.csv` => **UTF-16**
- most other files => **UTF-8** (often works with `UTF8`; if BOM exists, `UTF8` still works in many setups)

#### Option A2.2 — Using DBeaver Import Wizard

1. Right-click `raw.<table>` → **Import Data**
2. Select the matching CSV from `raw_data/`
3. Set encoding:
   - UTF-16 for `customers.csv`, `employees.csv`
   - UTF-8 for others
4. Run import

### Step A3 — Create `stg` views (normalized naming)

Run:

- `sql/00_setup/02_create_stg_views.sql`

After this, prefer querying `stg.*` to avoid quoted identifiers.

### Step A4 — Smoke test

```sql
select count(*) from raw.orders;
select order_id, customer_id, order_date from stg.orders limit 5;
```

---

## Option B — Fastlane / Python (one-command rebuild)

Run:

```bash
python python/01_load_raw_to_postgres.py
```

What this script does:
1. Creates (or rebuilds) database `underwear_fa_profiling`
2. Creates schemas + raw tables
3. Loads all 11 CSV files into `raw.*`
4. Creates `stg` views for normalized column naming

> If `DROP DATABASE` fails due to active sessions (e.g., DBeaver connections), close/disconnect the DB or use the script version that terminates existing sessions before dropping.

---

## Recommended Practice

- Use **Option A** to demonstrate SQL-first fundamentals and reproducibility.
- Use **Option B** to speed up iteration during profiling + scorecard development.
