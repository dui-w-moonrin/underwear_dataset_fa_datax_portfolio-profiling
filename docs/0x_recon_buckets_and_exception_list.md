# Recon Buckets & Exception List (0x)

This document summarizes **cross-table integrity breaks** discovered during profiling of the Underwear (11-table) dataset, plus a related **date-format anomaly** that affects reproducible parsing.

> **Purpose (FA-style):** provide an auditable, SQL-backed triage view of what is broken, how big the impact is, and what a Functional Analyst would do next (hypotheses, impact, and recommended actions for DE / source owners / UAT).

---

## 1) Executive Summary

### Key Findings (Top 3 buckets)

|Bucket |Relationship                                                                    |Orphan Rows|Base Rows|Base Table             |Orphan %|Severity|
|-------|--------------------------------------------------------------------------------|-----------|---------|-----------------------|--------|--------|
| **A** | `orders.shipping_method_id → shipping_methods.shipping_method_id`              | 2,278     | 2,286   |orders                 | 99.65% | High   |
| **B** | `payments.payment_method_id → payment_methods.payment_method_id`               | 685       | 686     |payments               | 99.85% | High   |
| **C** | `inventory_transactions.purchase_order_id → purchase_orders.purchase_order_id` | 17,606    | 20,951  |inventory_transactions | 84.03% | High   |

**Interpretation:** these are not “small exceptions.” They indicate **systematic mapping gaps** (lookup domains incomplete or incompatible), which would break downstream reconciliation, attribution, and any BI or regulatory-style reporting that assumes referential integrity.

---

## 2) How “Recon Buckets” are defined

### 2.1 Definition
A **Recon Bucket** groups a major integrity break where:

- a column behaves like a foreign key (FK),
- but values in the child table do **not** exist in the parent table (lookup/dimension),
- resulting in **orphan rows**.

This is tracked in:
- `dq.fk_orphans_detail` (by relationship)
- aggregated into `artifacts/scorecard.csv` / `artifacts/scorecard_100.csv` (by table)

### 2.2 Core check (conceptual SQL)
For a relationship `child.fk → parent.pk`, the orphan count is:

```sql
select count(*) as orphan_rows
from child c
left join parent p
  on c.fk = p.pk
where c.fk is not null
  and p.pk is null;
```

> Note: This project reports **aggregated orphan rows** by table in the scorecard, and relationship-level details in `dq.fk_orphans_detail`.

---

## 3) Bucket A — Shipping Method mapping is missing for most Orders

### 3.1 Relationship
- **Child:** `stg.orders.shipping_method_id`
- **Parent:** `stg.shipping_methods.shipping_method_id`

### 3.2 Impact
- Orphan rows: **2,278**
- Base rows: **2,286 orders**
- Orphan ratio: **~99.65%**

**Why it matters:**
- Any reporting that slices orders by shipping method will be **incorrect or impossible** (nearly all orders have an unmapped shipping method).
- Lead-time / shipping KPI segmentation becomes unreliable.

### 3.3 Top orphan FK values (exceptions)
Observed orphan FK values and counts (sample/top):

| shipping_method_id | orphan_rows |
|-------------------:|------------:|
| 1                  | 2,276       |
| 3                  | 2           |

> Interpretation: orphan values are heavily concentrated, suggesting a domain mismatch (e.g., lookup table missing expected IDs, or IDs not normalized/cast consistently).

### 3.4 Hypotheses (FA triage)
1. **Lookup table incomplete**: `shipping_methods` may be missing domain values referenced by orders.
2. **Type/casting mismatch in staging**: FK values might be numeric in one table but text in another, or CamelCase identifiers required quoting and were normalized inconsistently.
3. **Source-system semantics mismatch**: the field in orders might not be a true FK (could be a code from another domain).

### 3.5 Recommended next actions
- **Validate domain values**: list distinct `orders.shipping_method_id` vs `shipping_methods.shipping_method_id` and compare.
- **Confirm intended semantics** in Kaggle ER notes / dataset description: is it a strict FK or “free-text code” originally?
- If this were a real source system: **raise a DQ ticket** to source owner / DE to backfill or correct shipping_methods mapping.

---

## 4) Bucket B — Payment Method mapping is missing for most Payments

### 4.1 Relationship
- **Child:** `stg.payments.payment_method_id`
- **Parent:** `stg.payment_methods.payment_method_id`

### 4.2 Impact
- Orphan rows: **685**
- Base rows: **686 payments**
- Orphan ratio: **~99.85%**

**Why it matters:**
- Payment method distribution (cash/card/etc.) becomes unusable.
- Downstream reconciliation that depends on payment method rules cannot be trusted.

### 4.3 Top orphan FK values (exceptions)

| payment_method_id | orphan_rows |
|------------------:|------------:|
| 1                 | 648         |
| 2                 | 37          |

> Interpretation: most payments refer to a small set of unmapped method IDs. This strongly suggests `payment_methods` is incomplete or uses a different ID domain.

### 4.4 Hypotheses (FA triage)
1. **Lookup table is not the real parent** (wrong join key/domain).
2. **Lookup domain mismatch** (IDs differ; maybe payment_methods uses another key).
3. **Staging normalization issue** (e.g., trimming/typing causes mismatch).

### 4.5 Recommended next actions
- Compare `distinct payment_method_id` values between payments and payment_methods.
- Verify whether payment_methods contains the expected IDs (1,2,...) or uses non-numeric / different key.
- If fixing: add missing domain rows or remap payment method IDs consistently.

---

## 5) Bucket C — Many Inventory Transactions cannot be traced to Purchase Orders

### 5.1 Relationship
- **Child:** `stg.inventory_transactions.purchase_order_id`
- **Parent:** `stg.purchase_orders.purchase_order_id`

### 5.2 Impact
- Orphan rows: **17,606**
- Base rows: **20,951 inventory_transactions**
- Orphan ratio: **~84.03%**

**Why it matters:**
- Stock movement traceability is broken for most transactions.
- Any “procurement → receiving → inventory” audit trail becomes unreliable.

### 5.3 Top orphan FK values (exceptions)
Top offending `purchase_order_id` values with orphan rows (sample/top):

| purchase_order_id | orphan_rows |
|----:|----:|
| 175 | 689 |
| 121 | 452 |
| 307 | 414 |
| 148 | 412 |
| 308 | 366 |
| 46  | 352 |
| 54  | 349 |
| 313 | 331 |
| 309 | 330 |
| 156 | 291 |
| 52  | 287 |
| 284 | 286 |
| 57  | 282 |
| 88  | 263 |
| 74  | 253 |
| 69  | 250 |
| 303 | 249 |
| 129 | 246 |
| 183 | 230 |
| 154 | 230 |
| 107 | 223 |
| 294 | 214 |
| 100 | 194 |
| 25  | 194 |
| 195 | 184 |
| 167 | 183 |
| 75  | 182 |
| 279 | 177 |
| 39  | 176 |
| 286 | 173 |

> Interpretation: orphan values are spread across many PO IDs—this can indicate a broader mismatch between inventory_transactions and purchase_orders domains, not just a few missing rows.

### 5.4 Hypotheses (FA triage)
1. **Partial/filtered extract**: purchase_orders table may be a subset, while inventory_transactions references the full domain.
2. **Not all inventory transactions originate from purchase orders**: some may come from adjustments/returns/transfers; the field may be optional or overloaded.
3. **Key mismatch**: purchase_order_id in inventory_transactions might reference a different identifier than purchase_orders primary key.

### 5.5 Recommended next actions
- Split transactions by `transaction_type` (if available) to see if orphan ratio is concentrated in specific categories.
- Validate whether orphan rows have `purchase_order_id` values that are out of the purchase_orders date range.
- If real system: align with business owner on whether PO linkage is required for all transaction types.

---

## 6) Date Format Drift — parsing anomalies in date fields

### 6.1 Symptom
While generating date ranges, strict parsing can fail on values like:

- `10/13/2003`

This value suggests **MM/DD/YYYY** format (because “13” cannot be a month), while other values are in ISO-like format.

### 6.2 Why it matters
- **Reproducibility risk:** strict casts may throw errors and stop pipelines.
- **Profiling distortion:** date_min/date_max can be incorrect if parsing fails silently or inconsistently.
- **Downstream impact:** lead time metrics, period grouping, and temporal validation become unreliable.

### 6.3 How this project handles it (profiling scope)
- Profiling uses a **tolerant parsing approach** to avoid hard failures when mixed formats exist.
- When a field is too inconsistent, date_min/date_max may be partially unavailable or flagged for follow-up.

### 6.4 Recommended next actions (if moving toward cleaning/ELT extra)
- Standardize all date fields to ISO `YYYY-MM-DD` (or proper `DATE` types) in a cleaned layer.
- Keep an **exception list** of unparseable date strings for source correction / rule decisions.
- Document the chosen rule: prefer ISO, then detect MM/DD/YYYY, then fallback to NULL + exception logging.

---

## 7) Evidence pointers (where to look in the repo)

- Relationship-level orphans:
  - `dq.fk_orphans_detail` (table in PostgreSQL created by the SQL pack)
- Scorecard outputs:
  - `artifacts/scorecard.csv` (raw)
  - `artifacts/scorecard_100.csv` (with `dq_score_0_100`)
- SQL checks:
  - `sql/10_scorecard/05_fk_orphans.sql`
  - `sql/10_scorecard/03_date_range.sql` (tolerant parsing and date-range extraction)

---

## 8) Notes / Scope boundary

This repo is a **profiling-first FA portfolio**. It intentionally prioritizes:

- explainable, auditable integrity checks
- reproducible SQL evidence
- exception-oriented reporting for triage and UAT conversations

Full cleaning/standardization is treated as an optional extension (extra folder), not a required dependency for the profiling deliverables.
