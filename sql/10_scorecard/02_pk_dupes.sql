-- 02_pk_dupes.sql
-- suspected_pk + pk_null_pct + pk_duplicate_rows (per table)

do $$
declare
  m record;
  t_schema text := 'stg';
  t_name text;
  pk_col text;
  sql text;
begin
  for m in
    select * from (values
      ('customers',              'customer_id'),
      ('employees',              'employee_id'),
      ('inventory_transactions', 'transaction_id'),
      ('order_details',          'order_detail_id'),
      ('orders',                 'order_id'),
      ('payment_methods',        'payment_method_id'),
      ('payments',               'payment_id'),
      ('products',               'product_id'),
      ('purchase_orders',        'purchase_order_id'),
      ('shipping_methods',       'shipping_method_id'),
      ('suppliers',              'supplier_id')
    ) as x(table_name, pk_col)
  loop
    t_name := m.table_name;
    pk_col := m.pk_col;

    if not exists (
      select 1 from information_schema.tables
      where table_schema = t_schema and table_name = t_name
    ) then continue; end if;

    update dq.scorecard_table
    set suspected_pk = pk_col, updated_at = now()
    where table_schema = t_schema and table_name = t_name;

    sql := format($q$
      with base as (
        select count(*)::bigint as row_cnt
        from %I.%I
      ),
      pk_stats as (
        select
          count(*) filter (where %I is null)::bigint as pk_null_rows,
          coalesce((
            select sum(cnt - 1)::bigint
            from (
              select %I, count(*) as cnt
              from %I.%I
              where %I is not null
              group by %I
              having count(*) > 1
            ) d
          ), 0)::bigint as pk_duplicate_rows
        from %I.%I
      )
      update dq.scorecard_table s
      set
        pk_null_pct = case
          when b.row_cnt = 0 then null
          else round((p.pk_null_rows::numeric / b.row_cnt::numeric) * 100, 4)
        end,
        pk_duplicate_rows = p.pk_duplicate_rows,
        updated_at = now()
      from base b, pk_stats p
      where s.table_schema = %L and s.table_name = %L;
    $q$,
      t_schema, t_name,
      pk_col,
      pk_col, t_schema, t_name, pk_col, pk_col,
      t_schema, t_name,
      t_schema, t_name
    );

    execute sql;
  end loop;
end $$;