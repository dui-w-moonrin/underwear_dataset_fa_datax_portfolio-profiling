# Recon Buckets & Exception List (06)

This document summarizes cross-table relationship health (FK-style integrity) found during profiling of the **Underwear (11-table)** dataset, plus a **date-format note** that affects reproducible parsing.

> **FA intent:** Provide an auditable triage view of what is broken vs unknown, how big the impact is, and what to do next (hypotheses, impacts, recommended actions, and UAT questions).

---

## 0) Scope & Definitions

### What this report covers
- Cross-table relationship checks at **stg** layer (joinability / traceability)
- Bucket-style prioritization (A/B/C = most meaningful relationships to explain quickly)
- Date-format note (because date columns are stored as **text** in stg)

### What this report does NOT cover (by design)
- Full data cleansing / standardization of all fields (optional extension)
- Building a business KPI model or dashboard

---

## 1) Relationship Health: Terms (must read)

When checking `child_fk -> parent_pk`, we classify each child row into:

- **FK NULL**: child FK is NULL → relationship is **unknown** (cannot join)
- **Matched**: child FK is NOT NULL and exists in parent PK → relationship is **valid**
- **Orphan**: child FK is NOT NULL but missing in parent PK → relationship is **broken**

> Key idea:  
> - **Orphan = broken link** (data contradicts the parent table)  
> - **NULL-FK = unknown link** (data is missing; parent may exist but we can’t join)

---

## 2) Executive Summary (Buckets A/B/C)

### 2.1 Bucket Table (Correct Interpretation)

|Bucket|Relationship                                                                  |Base Rows|FK NULL Rows|FK Non-NULL Rows|Matched Rows|Orphan Rows|NULL %|Severity|
|------|------------------------------------------------------------------------------|--------:|-----------:|---------------:|-----------:|----------:|-----:|--------|
|**A** |`orders.shipping_method_id → shipping_methods.shipping_method_id`             |2,286    |8           |2,278           |2,278       |0          |0.35% |Low     |
|**B** |`payments.payment_method_id → payment_methods.payment_method_id`              |686      |1           |685             |685         |0          |0.15% |Low     |
|**C** |`inventory_transactions.purchase_order_id → purchase_orders.purchase_order_id`|20,951   |3,345       |17,606          |17,606      |0          |15.97%|High    |

### 2.2 What the table means (one-liners)
- **A (Orders ↔ Shipping Methods)**: join is **almost fully usable**; only **8 orders** have unknown shipping method (NULL FK)
- **B (Payments ↔ Payment Methods)**: join is **almost fully usable**; only **1 payment** has unknown method (NULL FK)
- **C (Inventory Tx ↔ Purchase Orders)**: a meaningful portion (**~16%**) of inventory transactions cannot be tied to a PO → procurement traceability is partially missing

---

## 3) Evidence Pointers (Where numbers come from)

Primary outputs:
- `artifacts/scorecard.csv`
- `artifacts/scorecard_100.csv`
- `sql/10_scorecard/05_fk_orphans.sql` (FK checks)

Recommended “proof query” pattern per relationship:

```sql
select
  count(*) as base_rows,
  count(*) filter (where c.fk_col is null) as fk_null_rows,
  count(*) filter (where c.fk_col is not null) as fk_non_null_rows,
  count(*) filter (where c.fk_col is not null and p.pk_col is not null) as matched_rows,
  count(*) filter (where c.fk_col is not null and p.pk_col is null) as orphan_rows
from stg.child_table c
left join stg.parent_table p
  on c.fk_col = p.pk_col;
```

> Tip: This avoids the common mistake of calling “missing match” an orphan when it’s actually “NULL FK”.

---

## 4) Bucket Details (Impact + Action + UAT)

### A — Orders ↔ Shipping Methods

**Relationship:** `stg.orders.shipping_method_id → stg.shipping_methods.shipping_method_id`  
**Result:** 8 NULL-FK, 2,278 matched, 0 orphans.

**Impact**
- Shipping-method analysis is **almost completely reliable**
- Only **8 orders** cannot be categorized by shipping method

**Recommended actions**
- Confirm what NULL means:
  - cancelled orders?
  - test / legacy import?
  - “shipping method set later” workflow?
- Define a rule:
  - exclude these 8 rows from shipping-method breakdown
  - OR allow “Unknown” category

**UAT questions**
- Do we expect every order to have a shipping method at creation time?
- Is shipping method allowed to be assigned later (late binding)?

---

### B — Payments ↔ Payment Methods

**Relationship:** `stg.payments.payment_method_id → stg.payment_methods.payment_method_id`  
**Result:** 1 NULL-FK, 685 matched, 0 orphans.

**Impact**
- Payment-method breakdown is usable
- Only 1 record is “unknown method”

**Recommended actions**
- Clarify NULL semantics:
  - cash/other/manual?
  - incomplete entry?

**UAT questions**
- Is payment method mandatory for payment posting?
- Can it be unknown temporarily then updated?

---

### C — Inventory Transactions ↔ Purchase Orders

**Relationship:** `stg.inventory_transactions.purchase_order_id → stg.purchase_orders.purchase_order_id`  
**Result:** 3,345 NULL-FK, 17,606 matched, 0 orphans.

**Impact**
- ~16% of inventory movements cannot be tied back to procurement documents (PO)
- Limits:
  - PO-based reconciliation (receiving completeness)
  - supplier performance analysis
  - procurement-to-stock audit trail

**Likely hypotheses (data-story)**
- Manual adjustments not tied to PO
- Opening balance loads
- Returns / write-offs / transfers represented without PO linkage

**Recommended actions**
- If business expects PO traceability:
  - treat as data capture issue (missing PO reference)
- If adjustments are expected:
  - require/derive a `transaction_type` and document allowed reasons for NULL PO

**UAT questions**
- Which inventory movements must be PO-backed vs allowed as “adjustments”?
- If NULL PO is allowed, what categories must exist?

---

## 5) Date Format Note (for README + reproducibility)

### 5.1 Current state in DB
- In `stg.*` views, date columns are still **TEXT** (from raw CSV), e.g.:
  - `orders.order_date`, `orders.ship_date`
  - `payments.payment_date`
  - `products.inventory_date`
  - `inventory_transactions.transaction_date`
  - `purchase_orders.order_date`

### 5.2 Observed format
- Many values look like US-style strings: **M/D/YYYY** (e.g., `7/10/2003`)
- Some files may include variants; therefore parsing must be explicit if casting to `date`

### 5.3 Recommendation (FA-friendly)
- Keep `stg` as TEXT for profiling (transparent and cheap)
- Add optional layer later:
  - a `stg_cast` view, or
  - a `dq.try_parse_date()` helper
- Document the parsing rule used, so others can reproduce results

---

---

## 6) Additional Profiling Anomalies (single-table signals)

> These are **profiling observations** (not fixes). They help scope follow-up validation rules and UAT questions.

### 6.1 Orders — temporal anomaly
- **OrderDate > ShipDate:** detected **12 orders** where `order_date` is later than `ship_date`.
  - Typical interpretation: bad source timestamp, swapped fields, timezone/import issue, or re-shipment workflow recorded incorrectly.
  - FA follow-up: confirm business rule — *Is ShipDate allowed to be earlier than OrderDate in any legitimate scenario?*

### 6.2 Payments — amount outlier (tail risk)
- `payments.payment_amount` has a long right tail; max payment is ~**20,534.7** while median is ~**602.6**.
  - Profiling stance: not “wrong” by itself, but worth tagging for review (e.g., bulk orders, currency/unit mismatch, or data entry issues).

### 6.3 OrderDetails / InventoryTransactions — extreme quantities
- `order_details.quantity_sold` can be as high as **612** (most values are much smaller).
- `inventory_transactions.quantity_ordered/received` can be as high as **1,475**, and `quantity_missing` up to **732**.
  - FA follow-up: define what “bulk” looks like vs what should be flagged as suspicious (threshold-based rules).

### 6.4 Products — high NULL concentration in descriptive attributes
- `products.color` shows a very high NULL frequency (most rows), while other descriptive fields (e.g., gender count is relatively high) suggest taxonomy inconsistencies.
  - FA follow-up: decide which attributes are **required** for analytics (e.g., Category/Gender/Size) vs optional.


## 6) Severity rubric (simple)

- **High**: affects major workflow linkage and impact > ~5–10%
- **Medium**: major linkage but impact 1–5%
- **Low**: small impact <1% or acceptable by business rule

Current severity calls:
- A = Low (NULL-FK only 0.35%)
- B = Low (NULL-FK only 0.15%)
- C = High (NULL-FK ~15.97%)

---

## 7) Next steps (suggested order)

1) Keep this doc + scorecard as “profiling complete”
2) If extending:
   - standardize date parsing
   - normalize numeric formats (thousand separators, currency)
3) If moving to reconciliation/UAT:
   - define business scenarios (orders-to-payments, PO-to-inventory)
   - add UAT test cases referencing buckets A/B/C
