-- 05_fk_orphans.sql
-- FK checks with normalization + mismatch quantification
-- Goal:
--   - fk_orphan_rows in scorecard = orphan_rows_norm (business orphan)
--   - keep orphan_rows_raw + fixable_by_normalize_rows for evidence

create schema if not exists dq;

-- 1) Helper: normalize "ID-like" text (handles 1.0 -> 1)
create or replace function dq.norm_id(x text)
returns text
language sql
immutable
as $$
  select nullif(
           regexp_replace(trim(x), '\.0$', ''),  -- drop trailing ".0"
           ''
         );
$$;

-- 2) Ensure detail table has extra columns (safe, no-op if already exists)
do $$
begin
  -- detail table may already exist from your 00_create_scorecard_tables.sql
  if to_regclass('dq.fk_orphans_detail') is not null then
    alter table dq.fk_orphans_detail
      add column if not exists base_rows bigint,
      add column if not exists null_fk_rows bigint,
      add column if not exists orphan_rows_raw bigint,
      add column if not exists orphan_rows_norm bigint,
      add column if not exists fixable_by_normalize_rows bigint;
  end if;

  -- optional: add a column in scorecard for mismatch (lightweight, 1 column)
  if to_regclass('dq.scorecard_table') is not null then
    alter table dq.scorecard_table
      add column if not exists fk_fixable_by_normalize_rows bigint;
  end if;
end $$;

-- 3) Run checks
do $$
declare
  rel record;
  t_schema text := 'stg';
  sql text;

  base_rows bigint;
  null_fk_rows bigint;
  orphan_raw bigint;
  orphan_norm bigint;
  fixable bigint;
begin

  for rel in
    select * from (values
      ('orders',                 'customer_id',        'customers',        'customer_id'),
      ('orders',                 'employee_id',        'employees',        'employee_id'),
      ('orders',                 'shipping_method_id', 'shipping_methods', 'shipping_method_id'),
      ('order_details',          'order_id',           'orders',           'order_id'),
      ('order_details',          'product_id',         'products',         'product_id'),
      ('payments',               'order_id',           'orders',           'order_id'),
      ('payments',               'payment_method_id',  'payment_methods',  'payment_method_id'),
      ('purchase_orders',        'supplier_id',        'suppliers',        'supplier_id'),
      ('purchase_orders',        'employee_id',        'employees',        'employee_id'),
      ('purchase_orders',        'shipping_method_id', 'shipping_methods', 'shipping_method_id'),
      ('inventory_transactions', 'product_id',         'products',         'product_id'),
      ('inventory_transactions', 'purchase_order_id',  'purchase_orders',  'purchase_order_id')
    ) as x(child_table, child_fk_col, parent_table, parent_pk_col)
  loop

    -- One query returns all metrics for this relationship
    sql := format($q$
      with base as (
        select
          c.%1$I as fk_raw,
          dq.norm_id(c.%1$I) as fk_norm
        from %2$I.%3$I c
      ),
      p_raw as (
        select %4$I as pk_raw, dq.norm_id(%4$I) as pk_norm
        from %2$I.%5$I
      ),
      j as (
        select
          b.fk_raw,
          b.fk_norm,
          pr.pk_raw as hit_raw,
          pn.pk_raw as hit_norm
        from base b
        left join p_raw pr
          on b.fk_raw is not null
         and b.fk_raw = pr.pk_raw
        left join p_raw pn
          on b.fk_norm is not null
         and b.fk_norm = pn.pk_norm
      )
      select
        count(*) filter (where fk_raw is not null)::bigint                                  as base_rows,
        count(*) filter (where fk_raw is null)::bigint                                      as null_fk_rows,
        count(*) filter (where fk_raw is not null and hit_raw is null)::bigint              as orphan_rows_raw,
        count(*) filter (where fk_raw is not null and fk_norm is not null and hit_norm is null)::bigint
                                                                                             as orphan_rows_norm,
        count(*) filter (where fk_raw is not null and hit_raw is null and hit_norm is not null)::bigint
                                                                                             as fixable_by_normalize_rows
      from j;
    $q$,
      rel.child_fk_col,            -- %1
      t_schema, rel.child_table,   -- %2 %3
      rel.parent_pk_col,           -- %4
      rel.parent_table             -- %5
    );

    execute sql into base_rows, null_fk_rows, orphan_raw, orphan_norm, fixable;

    -- Upsert detail row
    insert into dq.fk_orphans_detail(
      child_schema, child_table, child_fk_col,
      parent_schema, parent_table, parent_pk_col,
      orphan_rows, checked_at,
      base_rows, null_fk_rows, orphan_rows_raw, orphan_rows_norm, fixable_by_normalize_rows
    )
    values (
      t_schema, rel.child_table, rel.child_fk_col,
      t_schema, rel.parent_table, rel.parent_pk_col,
      orphan_norm, now(),                -- keep legacy orphan_rows = norm (business orphan)
      base_rows, null_fk_rows, orphan_raw, orphan_norm, fixable
    )
    on conflict (child_schema, child_table, child_fk_col, parent_schema, parent_table, parent_pk_col)
    do update set
      orphan_rows = excluded.orphan_rows,
      checked_at = excluded.checked_at,
      base_rows = excluded.base_rows,
      null_fk_rows = excluded.null_fk_rows,
      orphan_rows_raw = excluded.orphan_rows_raw,
      orphan_rows_norm = excluded.orphan_rows_norm,
      fixable_by_normalize_rows = excluded.fixable_by_normalize_rows;

  end loop;

  -- Roll up per child table into scorecard
  update dq.scorecard_table s
  set
    fk_orphan_rows = d.orphan_rows_norm,
    fk_fixable_by_normalize_rows = d.fixable_by_normalize_rows,
    updated_at = now()
  from (
    select
      child_schema as table_schema,
      child_table  as table_name,
      sum(orphan_rows_norm)::bigint as orphan_rows_norm,
      sum(fixable_by_normalize_rows)::bigint as fixable_by_normalize_rows
    from dq.fk_orphans_detail
    group by child_schema, child_table
  ) d
  where s.table_schema = d.table_schema
    and s.table_name   = d.table_name;

end $$;
