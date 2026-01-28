-- 03_date_range.sql
-- date_min/date_max for key date columns
-- Robust date parsing (handles ambiguous DD/MM vs MM/DD) and never crashes scorecard.

create schema if not exists dq;

create or replace function dq.try_parse_date(v text)
returns date
language plpgsql
immutable
as $$
declare
  d date;
  p1 int;
  p2 int;
begin
  if v is null or btrim(v) = '' then
    return null;
  end if;

  begin
    -- ISO: YYYY-MM-DD
    if v ~ '^\d{4}-\d{2}-\d{2}$' then
      return v::date;
    end if;

    -- YYYY/MM/DD
    if v ~ '^\d{4}/\d{2}/\d{2}$' then
      return replace(v,'/','-')::date;
    end if;

    -- DD-MM-YYYY or MM-DD-YYYY (ambiguous -> decide by >12 heuristic)
    if v ~ '^\d{2}-\d{2}-\d{4}$' then
      p1 := split_part(v,'-',1)::int;
      p2 := split_part(v,'-',2)::int;

      if p1 > 12 then
        d := to_date(v,'DD-MM-YYYY');
      elsif p2 > 12 then
        d := to_date(v,'MM-DD-YYYY');
      else
        -- ambiguous like 03-07-2003 -> choose DD-MM by default
        d := to_date(v,'DD-MM-YYYY');
      end if;

      return d;
    end if;

    -- DD/MM/YYYY or MM/DD/YYYY (ambiguous -> decide by >12 heuristic)
    if v ~ '^\d{2}/\d{2}/\d{4}$' then
      p1 := split_part(v,'/',1)::int;
      p2 := split_part(v,'/',2)::int;

      if p1 > 12 then
        d := to_date(v,'DD/MM/YYYY');
      elsif p2 > 12 then
        d := to_date(v,'MM/DD/YYYY'); -- fixes values like 10/13/2003
      else
        -- ambiguous like 03/07/2003 -> choose DD/MM by default
        d := to_date(v,'DD/MM/YYYY');
      end if;

      return d;
    end if;

    return null;

  exception when others then
    -- if anything weird slips through, never crash scorecard
    return null;
  end;
end $$;

do $$
declare
  m record;
  t_schema text := 'stg';
  sql text;
  col_exprs text;
begin
  -- Map: table -> date columns to consider for date range.
  -- Adjust these column names if your stg views differ.
  for m in
    select * from (values
      ('orders',                 array['order_date','ship_date']),
      ('payments',               array['payment_date']),
      ('purchase_orders',        array['order_date']),
      ('inventory_transactions', array['transaction_date']),
      ('products',               array['inventory_date'])
    ) as x(table_name, date_cols)
  loop
    if not exists (
      select 1 from information_schema.tables
      where table_schema = t_schema and table_name = m.table_name
    ) then
      continue;
    end if;

    -- Build a list of dq.try_parse_date(col) expressions: dq.try_parse_date(col1), dq.try_parse_date(col2) ...
    select string_agg(format('dq.try_parse_date(%I)', c), ', ')
    into col_exprs
    from unnest(m.date_cols) as c;

    -- If no columns specified, skip
    if col_exprs is null then
      continue;
    end if;

    sql := format($q$
      with parsed as (
        select
          least(%s) as dt_least,
          greatest(%s) as dt_greatest
        from %I.%I
      ),
      agg as (
        select min(dt_least) as date_min, max(dt_greatest) as date_max
        from parsed
      )
      update dq.scorecard_table s
      set date_min = a.date_min, date_max = a.date_max, updated_at = now()
      from agg a
      where s.table_schema = %L and s.table_name = %L;
    $q$,
      col_exprs, col_exprs,
      t_schema, m.table_name,
      t_schema, m.table_name
    );

    execute sql;
  end loop;
end $$;
