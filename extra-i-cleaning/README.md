# extra-i-cleaning — Lightweight ETL/ELT (Rule-based, Non-official)

> This folder is an **extra** deliverable to demonstrate **basic ETL/ELT capability** with explicit, rule-based transformations.
> These rules are **not official accounting / payment rules** and are **not** tied to any production schema or enterprise policy.
>
> We use **Python (pandas)** to clean and standardize the raw CSVs, producing a “query-ready” cleaned layer:
>
> - `extra-i-cleaning/cleaned_data/*.csv`

---

## 1) Objective

This layer aims to make the dataset consistent enough to:
- Load into a database (e.g., Postgres) and query reliably
- Demonstrate an ETL/ELT workflow (Extract → Transform/Clean → Load)
- Prepare for `extra-ii-querying/` where we showcase **SQL-first thinking** (control grain, reduce row explosion before joins, apply windows at the end)

> We **do not** try to make `cleaned_data` “production-perfect.”  
> The goal is to prove process understanding and produce data that is clean enough for clear, reproducible queries.

---

## 2) Scope

### ✅ In scope
- Standardize **table names** and **column names** to `snake_case`
- Standardize core **data types** using simple, deterministic rules:
  - Columns ending with `ID` → cast to string
  - Columns ending with `Date` → parse from `mm-dd-yyyy`, export as ISO `YYYY-MM-DD`
- Conservative NULL handling:
  - Do **not** guess missing keys / money / quantities
  - Impute `"unknown"` for selected descriptive attributes that do not affect financial correctness (e.g., `products.color`)
- Generate a small `cleaning_report.csv` for traceability

### ❌ Out of scope
- No deep business logic fixes (e.g., returns/discounts ledger logic)
- No “auto-correct” for complex anomalies beyond safe standardization
- No imputation of monetary values (amount/price)
- No cross-table merges; still “one table → one cleaned CSV”
- Not fixing every issue (avoids bloat and avoids silently fabricating data)

---

## 3) Rules

### 3.1 Naming standardization
**Table names**
- Derived from file names (stem), converted to `snake_case`
- Example: `OrderDetails.csv` → `order_details.csv`

**Column names**
- All columns converted to `snake_case`
- Example: `CustomerID` → `customer_id`, `TransactionDate` → `transaction_date`

**Why**
- `snake_case` is convenient for SQL and avoids quoting issues.

---

### 3.2 ID columns (ending with `ID`)
**Rule**
- Any column ending with `ID` → after `snake_case`, this becomes `*_id`
- Cast all `*_id` columns to pandas `string` dtype

**Why**
- IDs are identifiers, not measures
- Safer for leading zeros and exports
- Easier validation of formats later

**NULL policy**
- If an ID is NULL: **do not impute**. Keep NULL and handle via flags/exceptions downstream.

---

### 3.3 Date columns (ending with `Date`)
**Rule**
- Any column ending with `Date` → after `snake_case`, this becomes `*_date`
- Source format: `mm-dd-yyyy`
- Parse to datetime in pandas, then export to CSV as ISO `YYYY-MM-DD`

**Error handling**
- If parsing fails: keep as NULL (NaT) and count failures in `cleaning_report.csv`

---

## 4) NULL handling policy (by category)

Principle: **Do not “invent” values just to reduce NULLs.** Prefer traceable flags.

### 4.1 Key fields (PK/FK — mostly `*_id`)
- Keep NULL (do not fill)
- Explain/segment later with flags or exception lists

Example:
- `inventory_transactions.purchase_order_id` has many NULLs → indicates records not linked to a PO (could be internal movement or missing linkage)

---

### 4.2 Monetary fields (e.g., `payment_amount`, `unit_purchase_price`)
- Keep NULL
- Never fill with 0 (0 has a different meaning than unknown)

---

### 4.3 Quantity fields (e.g., `quantity_ordered`, `quantity_received`, `quantity_missing`)
- Keep NULL (conservative)
- Optional imputation (e.g., missing → 0) is only acceptable when the business definition is explicitly “no event,” and should be accompanied by an imputation flag (not used here)

---

### 4.4 Descriptive attributes (string fields used for grouping)
- Allowed to fill with `"unknown"` when it does not affect financial correctness and improves usability for grouping.

Example:
- `products.color` has heavy NULLs → fill NULL with `"unknown"` to keep group-by results readable.

---

## 5) Temporal anomaly policy (Orders)

**Observed anomaly**
- `order_date > ship_date` occurs in a small number of rows.

**Rule**
- Do **not** auto-correct by swapping or overwriting dates (avoid fabricating data).
- Keep raw values and add a flag:
  - `is_orderdate_gt_shipdate` (boolean)
- Optionally add an analytic helper:
  - `ship_lead_days = (ship_date - order_date).days` (can be negative)

This enables downstream filtering and exception reporting without silently changing source values.

---

## 6) Outputs

After running the script, you get:

1) **Cleaned CSVs**
- `extra-i-cleaning/cleaned_data/*.csv`
  - `snake_case` table/column names
  - `*_id` columns as string
  - `*_date` columns exported as `YYYY-MM-DD`

2) **Cleaning report**
- `extra-i-cleaning/artifacts/cleaning_report.csv`
  - row/column counts per table
  - detected source encoding (useful for UTF-16 files)
  - counts of ID/date columns standardized
  - invalid date parse counts
  - orders anomaly count (`order_date > ship_date`) if applicable

---

## 7) How to run

From repo root:

```bash
python extra-i-cleaning/python/01_cleaning.py
```

The script runs in batch mode (reads all `raw_data/*.csv`) and writes outputs automatically.

---

## 8) Why this matters for extra-ii-querying

With a “query-ready” cleaned layer:
- IDs are consistent (string) → joins are stable
- dates are standardized → time filters and windows are easier
- anomalies are flagged → reports can include/exclude exception rows explicitly

This supports showcasing **SQL-first concepts** in `extra-ii-querying/`.
