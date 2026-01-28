-- 00_create_scorecard_tables.sql
-- Create DQ tables to store scorecard outputs (safe to re-run)

create schema if not exists dq;

create table if not exists dq.scorecard_table (
  table_schema text not null,
  table_name   text not null,
  row_count    bigint,
  col_count    int,

  null_cells        bigint,
  total_cells       bigint,
  overall_null_pct  numeric(9,4),

  suspected_pk      text,
  pk_null_pct       numeric(9,4),
  pk_duplicate_rows bigint,

  date_min date,
  date_max date,

  neg_value_flags bigint,

  fk_orphan_rows bigint,

  updated_at timestamptz not null default now(),
  primary key (table_schema, table_name)
);

create table if not exists dq.fk_orphans_detail (
  child_schema text not null,
  child_table  text not null,
  child_fk_col text not null,
  parent_schema text not null,
  parent_table  text not null,
  parent_pk_col text not null,

  orphan_rows bigint not null,
  checked_at  timestamptz not null default now(),

  primary key (child_schema, child_table, child_fk_col, parent_schema, parent_table, parent_pk_col)
);