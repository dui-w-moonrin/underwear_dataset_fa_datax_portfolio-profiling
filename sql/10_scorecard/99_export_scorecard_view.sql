-- 99_export_scorecard_view.sql
-- Convenience view to export as artifacts/scorecard.csv

create schema if not exists dq;

create or replace view dq.scorecard_v as
select
  table_schema,
  table_name,
  row_count,
  col_count,
  null_cells,
  total_cells,
  overall_null_pct,
  suspected_pk,
  pk_null_pct,
  pk_duplicate_rows,
  date_min,
  date_max,
  neg_value_flags,
  fk_orphan_rows,
  updated_at
from dq.scorecard_table
order by table_schema, table_name;