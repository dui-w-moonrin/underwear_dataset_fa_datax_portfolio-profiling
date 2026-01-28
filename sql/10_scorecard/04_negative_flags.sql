-- 04_negative_flags.sql
-- Count rows containing negative values in key numeric columns

create schema if not exists dq;

create or replace function dq.try_parse_numeric(v text)
returns numeric
language sql
immutable
as $$
  select case
    when v is null then null
    when v ~ '^-?\d+(\.\d+)?$' then v::numeric
    else null
  end;
$$;

do $$
declare
  m record;
  t_schema text := 'stg';
  sql text;
  any_neg_expr text;
begin
  for m in
    select * from (values
      ('orders',                 array['freight_charge']),
      ('payments',               array['payment_amount']),
      ('order_details',          array['quantity_sold','unit_sales_price']),
      ('inventory_transactions', array['unit_purchase_price','quantity_ordered','quantity_received','quantity_missing']),
      ('products',               array['purchase_price','weight'])
    ) as x(table_name, num_cols)
  loop
    if not exists (
      select 1 from information_schema.tables
      where table_schema = t_schema and table_name = m.table_name
    ) then continue; end if;

    select string_agg(format('(dq.try_parse_numeric(%I) < 0)', c), ' OR ')
    into any_neg_expr
    from unnest(m.num_cols) as c;

    if any_neg_expr is null then any_neg_expr := 'false'; end if;

    sql := format($q$
      with agg as (
        select count(*)::bigint as neg_rows
        from %I.%I
        where %s
      )
      update dq.scorecard_table s
      set neg_value_flags = a.neg_rows, updated_at = now()
      from agg a
      where s.table_schema = %L and s.table_name = %L;
    $q$,
      t_schema, m.table_name,
      any_neg_expr,
      t_schema, m.table_name
    );

    execute sql;
  end loop;
end $$;