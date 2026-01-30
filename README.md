# Underwear Dataset — FA Profiling Portfolio
WATCHARAPONG 'DUI' MOONRIN

## About Dataset
![Dataset cover](/images/dataset_cover.jpg "Dataset Cover")

> This dataset originates from a wholesale company specializing in the marketing and sales of underwear, referred to as "the Company" henceforth. It represents a subset of the Company's comprehensive database, encompassing data on purchases, sales, orders, customers, prices, and much more, spanning a specific period. The dataset is organized across 11 tables, varying in size from a handful to over 100,000 rows. Thanks to primary and secondary indices linking these tables, the dataset offers an excellent opportunity to hone skills in SQL, data analysis, visualization, and machine learning. A table outlining the relationships between them is provided for clarity.

**source:** [https://www.kaggle.com/datasets/hserdaraltan/underwear-data-with-11-tables-and-up-to-100k-rows](https://www.kaggle.com/datasets/hserdaraltan/underwear-data-with-11-tables-and-up-to-100k-rows)

## Goal
Build a **Quality Scorecard** for SQL-first Data FA-style profiling:
- table-level completeness & basic sanity checks
- **aggregated cross-table FK orphan checks**

## Why this matters for FA
A Data Functional Analyst is responsible for ensuring data delivered to business users and downstream platforms is **accurate, consistent, and auditable**. This portfolio focuses on the core FA workflow:

- **Data integrity across tables (functional correctness):** detect broken relationships (e.g., FK orphans) that silently corrupt downstream reporting and reconciliation.
- **Data quality metrics for decision-making:** provide a scorecard that helps teams prioritize issues (completeness, uniqueness, sanity flags) before building analytics or regulatory outputs.
- **Validation-ready evidence (SQL-first):** each metric is backed by reproducible SQL checks and clear documentation, mirroring real FA collaboration with Data Engineers and UAT stakeholders.

This mirrors FA responsibilities such as data requirements, mapping logic, validation rules, and supporting UAT with traceable evidence.


## Tools

### Major
- Python — VS Code
- SQL — PostgreSQL, DBeaver
- Git — version control

### Minor
- MS Excel / Google Sheets / Rainbow CSV (VS Code) for quick CSV browsing and note-taking
- [mermaid.live](https://mermaid.live) or [app.eraser.io](https://app.eraser.io) for quick Mermaid diagram editing

## Deliverable
- `artifacts/scorecard.csv` — raw scorecard export (table-level + aggregated FK orphan checks)
- `artifacts/scorecard_100.csv` — scorecard with `dq_score_0_100` (replaces `updated_at` for overview scanning)

## Repo Structure
- `raw_data/` raw CSV inputs (11 tables)
- `sql/` setup + scorecard SQL checks
- `python/` helper scripts (optional fast lane)
- `docs/` flow/lineage + how-to + exception brief
- `images/` image references
- `artifacts/` outputs

## How to Reproduce
See
 `docs/01_import_csv_howto_md` and `docs/02_scorecard_howto.md`.


## Dataset Scorecard (Preview)
![ER Diagram](/images/er_kaggle_as_is.png "initial ER Diagram for all 11 tables relationship")

Full details in `docs/03_er_full_as_is.md`g

|table_schema|table_name            |row_count|col_count|null_cells|total_cells|overall_null_pct|suspected_pk      |pk_null_pct|pk_duplicate_rows|date_min  |date_max  |neg_value_flags|fk_orphan_rows|dq_score_0_100|
|------------|----------------------|---------|---------|----------|-----------|----------------|------------------|-----------|-----------------|----------|----------|---------------|--------------|--------------|
|stg         |customers             |225      |8        |4         |1800       |0.2222          |customer_id       |0.0        |0                |          |          |               |              |100           |
|stg         |employees             |15       |2        |0         |30         |0.0             |employee_id       |0.0        |0                |          |          |               |              |100           |
|stg         |inventory_transactions|20951    |9        |46433     |188559     |24.6252         |transaction_id    |0.0        |0                |2003-10-15|2005-12-15|0.0            |0.0           |80            |
|stg         |order_details         |105757   |5        |0         |528785     |0.0             |order_detail_id   |0.0        |0                |          |          |0.0            |0.0           |100           |
|stg         |orders                |2286     |7        |8         |16002      |0.05            |order_id          |0.0        |0                |2001-10-20|2005-12-28|0.0            |0.0           |100           |
|stg         |payment_methods       |3        |2        |0         |6          |0.0             |payment_method_id |0.0        |0                |          |          |               |              |100           |
|stg         |payments              |686      |5        |2         |3430       |0.0583          |payment_id        |0.0        |0                |2003-10-10|2003-12-30|0.0            |0.0           |100           |
|stg         |products              |4183     |14       |4144      |58562      |7.0763          |product_id        |0.0        |0                |2003-10-15|2005-11-23|0.0            |              |94            |
|stg         |purchase_orders       |232      |5        |5         |1160       |0.431           |purchase_order_id |0.0        |0                |2003-10-15|2005-11-29|               |0.0           |100           |
|stg         |shipping_methods      |4        |2        |0         |8          |0.0             |shipping_method_id|0.0        |0                |          |          |               |              |100           |
|stg         |suppliers             |2        |2        |0         |4          |0.0             |supplier_id       |0.0        |0                |          |          |               |              |100           |

- Full scorecard (raw): `artifacts/scorecard.csv`
- Full scorecard (with score): `artifacts/scorecard_100.csv`
- Full table statistics: `docs/tablestats/README.md`, `docs/03_table_stats.md` and `docs/tablestats/*.csv`
- How the scorecard is generated: `docs/02_scorecard_howto.md`

### Scoring rule (simple / explainable)
`dq_score_0_100` starts at **100** and subtracts penalties:
- Completeness: overall null % (cap 30)
- PK health: PK null % (cap 30) and PK duplicates (cap 30; heavier impact)
- Numeric sanity: negative-value flags (cap 20)
- Referential integrity: FK orphan ratio (cap 40; orphan_rows / row_count)
- Date usability: small penalty if only date_min or date_max is present (cap 5)

The goal is not “perfect math”, but an **auditable prioritization signal** for FA/DE collaboration.

## Flow & Lineage (Preview)
![Flowchart overview](/artifacts/diagrams/flowchart_full.png "Flowchart overview")

Full details (Mermaid + left/right breakdown): `docs/04_flowchart_mermaid.md`.


## Recon Buckets (Preview)

> many rows have **missing FK values (NULL)**, so relationships cannot be interpreted downstream.

|Bucket|Relationship                                                                  |Base Rows|FK NULL Rows|FK Non-NULL Rows|Matched Rows|Orphan Rows|NULL %|Severity|
|------|------------------------------------------------------------------------------|--------:|-----------:|---------------:|-----------:|----------:|-----:|--------|
|**A** |`orders.shipping_method_id → shipping_methods.shipping_method_id`             |2,286    |8           |2,278           |2,278       |0          |0.35% |Low     |
|**B** |`payments.payment_method_id → payment_methods.payment_method_id`              |686      |1           |685             |685         |0          |0.15% |Low     |
|**C** |`inventory_transactions.purchase_order_id → purchase_orders.purchase_order_id`|20,951   |3,345       |17,606          |17,606      |0          |15.97%|High    |

**Interpretation**
- **Matched Rows** = FK present (non-NULL) and found in parent table (valid relationship)
- **Orphan Rows** = FK present (non-NULL) but missing in parent table (broken relationship) → **0** for A/B/C
- **FK NULL Rows** = relationship is **unknown** (cannot join / cannot infer method/order context)

**Why C is high**
- ~16% of inventory transactions have no purchase_order_id, so those movements cannot be tied back to procurement documents.

## Date format note (important)

- In `raw`/`stg`, date fields are stored as **text** (CSV source), not native `date/timestamp`.
- Observed formats include US-style **M/D/YYYY** (e.g., `10/13/2003`) and other variants.
- Therefore, any `date_min` / `date_max` in the scorecard is computed via a **safe parsing rule** (try-parse) and should be treated as a profiling signal, not a guaranteed canonical date type.

Full breakdown and hypotheses: `docs/05_recon_buckets_and_exception_list.md`