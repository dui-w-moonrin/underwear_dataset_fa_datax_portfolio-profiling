# Generate Data Quality Scorecard (SQL Pack + Optional Python Runner)

This doc explains **how `artifacts/scorecard.csv` is produced**, using two reproducible paths:

- **Option A (SQL-first / Manual):** Run the SQL pack step-by-step (good for auditability and learning).
- **Option B (Fastlane / Python):** One command runs the same SQL pack and exports `artifacts/scorecard.csv`.

> This project is SQL-first. The Python runner is only a convenience wrapper around the same SQL checks.

---

## Prerequisites

### Database
- PostgreSQL running locally
- Target DB (example): `underwear_fa_profiling`
- Required schemas/views (created earlier):
  - `raw` tables (loaded from `raw_data/*.csv`)
  - `stg` views (created by `sql/00_setup/02_create_stg_views.sql`)

> Import/loading is documented separately in `docs/01_import_csv.md`.

### Repo structure (expected)
- `sql/00_setup/`
- `sql/10_scorecard/`
- `raw_data/*.csv`
- `artifacts/` (output folder)
- `python/02_generate_scorecard.py` (Option B runner)

---

## Connection configuration

You can configure database access by environment variables. Use placeholders and set them to your own values.

### Recommended env vars
- `PGHOST` (example: `localhost`)
- `PGPORT` (example: `5432`)
- `PGDATABASE` (example: `underwear_fa_profiling`)
- `PGUSER` (example: `postgres`)
- `PGPASSWORD` (your password)

### PowerShell example
```powershell
$env:PGHOST="localhost"
$env:PGPORT="5432"
$env:PGDATABASE="underwear_fa_profiling"
$env:PGUSER="{your_username}"
$env:PGPASSWORD="{your_password}"
```

> If you prefer, you may store secrets in your OS keychain instead of environment variables.  
> For public repos, **do not commit passwords**.

---

## Option A — SQL-first (Manual)

### Step A1) Ensure scorecard tables exist
Run:
- `sql/10_scorecard/00_create_scorecard_tables.sql`

This creates/ensures the `dq` schema and the scorecard tables used to store results.

### Step A2) Run the profiling SQL pack in order
Run each script below (in this order):

1. `sql/10_scorecard/01_nulls.sql`  
   - Populates:
     - `row_count`, `col_count`
     - `null_cells`, `total_cells`, `overall_null_pct`

2. `sql/10_scorecard/02_pk_dupes.sql`  
   - Populates:
     - `suspected_pk`, `pk_null_pct`, `pk_duplicate_rows`

3. `sql/10_scorecard/03_date_range.sql`  
   - Populates:
     - `date_min`, `date_max`
   - **Note (format drift):** This dataset contains mixed date formats (e.g. `YYYY-MM-DD` and `MM/DD/YYYY`).  
     The script uses a tolerant parser (`dq.try_parse_date`) to avoid crashing the run and returns `NULL` for unparseable values.

4. `sql/10_scorecard/04_negative_flags.sql`  
   - Populates:
     - `neg_value_flags` (numeric sanity checks; definition in the SQL file)

5. `sql/10_scorecard/05_fk_orphans.sql`  
   - Populates:
     - `fk_orphan_rows` in the table scorecard
     - `dq.fk_orphans_detail` with orphan counts per FK relationship (used in Phase 3 exception brief)

### Step A3) Export to CSV (scorecard.csv)
Export the final view/table to `artifacts/scorecard.csv`.

If you use `psql`:
```sql
\copy (
  select
    table_schema, table_name,
    row_count, col_count,
    null_cells, total_cells, overall_null_pct,
    suspected_pk, pk_null_pct, pk_duplicate_rows,
    date_min, date_max,
    neg_value_flags,
    fk_orphan_rows,
    updated_at
  from dq.scorecard_table
  order by table_schema, table_name
) to 'artifacts/scorecard.csv' csv header;
```

If you use DBeaver:
- Run the `select ...` query above
- Export result grid → CSV → save as `artifacts/scorecard.csv`

---

## Option B — Python runner (Fastlane)

### Step B1) Python environment
Create a venv and install dependencies.

**Minimal requirements (recommended):**
- `psycopg[binary]`

Optional (only if your runner uses them):
- `pandas`
- `sqlalchemy` (not required for this project if using psycopg directly)

Example:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install "psycopg[binary]"
```

> If your network blocks PyPI SSL verification, fix your system certificate chain first (Bitdefender / corporate MITM / OS root store).  
> Do **not** disable SSL verification as a workaround in production.

### Step B2) Run one command to generate the scorecard
```powershell
python python/02_generate_scorecard.py
```

Expected output:
- `artifacts/scorecard.csv`

What it does (high level):
1. Connects to PostgreSQL using your env vars
2. Runs the SQL pack under `sql/10_scorecard/` in the correct order
3. Exports the scorecard to CSV

---

## Notes & gotchas

### 1) Quoted identifiers (CamelCase)
If any raw tables or columns were imported with CamelCase (e.g., `CustomerID`), PostgreSQL requires quotes:
- `"CustomerID"` is different from `customerid`

This project avoids the pain by exposing normalized `stg` views (snake_case) for profiling.  
See: `sql/00_setup/02_create_stg_views.sql`.

### 2) Date format drift
Some date fields contain mixed formats such as `MM/DD/YYYY` (e.g., `10/13/2003`) and ISO-like formats.  
`03_date_range.sql` uses `dq.try_parse_date()` to parse common formats safely.

### 3) FK orphan details (Phase 3)
`05_fk_orphans.sql` writes a relationship-level summary table:
- `dq.fk_orphans_detail`

Use it to explain *which FK relationship* is failing, not only the table-level totals shown in the scorecard.

Example:
```sql
select * from dq.fk_orphans_detail order by orphan_rows desc;
```

---

## Outputs

- **Primary artifact:** `artifacts/scorecard.csv`
- **Support tables:**
  - `dq.scorecard_table` (main table-level scorecard data)
  - `dq.fk_orphans_detail` (relationship-level orphan summary)
