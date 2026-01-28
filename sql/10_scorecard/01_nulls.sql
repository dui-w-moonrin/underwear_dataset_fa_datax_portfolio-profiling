-- 01_nulls.sql
-- Fill row_count/col_count/null_cells/overall_null_pct for stg.* views

do $$
declare
  r record;
  cols_sql text;
  sql text;
begin
  -- Ensure all stg views exist in scorecard_table
  for r in
    select table_schema, table_name
    from information_schema.tables
    where table_schema = 'stg'
      and table_type = 'VIEW'
    order by table_name
  loop
    insert into dq.scorecard_table (table_schema, table_name)
    values (r.table_schema, r.table_name)
    on conflict (table_schema, table_name) do nothing;
  end loop;

  -- For each stg view, compute null_cells dynamically
  for r in
    select table_schema, table_name
    from information_schema.tables
    where table_schema = 'stg'
      and table_type = 'VIEW'
    order by table_name
  loop
    select string_agg(
             format('count(*) filter (where %I is null)', column_name),
             ' + '
           )
    into cols_sql
    from information_schema.columns
    where table_schema = r.table_schema
      and table_name   = r.table_name;

    if cols_sql is null then cols_sql := '0'; end if;

    sql := format($q$
      with base as (
        select
          count(*)::bigint as row_count,
          (select count(*)::int
           from information_schema.columns
           where table_schema = %L and table_name = %L) as col_count,
          (%s)::bigint as null_cells
        from %I.%I
      )
      update dq.scorecard_table s
      set
        row_count = b.row_count,
        col_count = b.col_count,
        null_cells = b.null_cells,
        total_cells = (b.row_count * b.col_count)::bigint,
        overall_null_pct = case
          when (b.row_count * b.col_count) = 0 then null
          else round((b.null_cells::numeric / (b.row_count * b.col_count)::numeric) * 100, 4)
        end,
        updated_at = now()
      from base b
      where s.table_schema = %L
        and s.table_name = %L;
    $q$,
      r.table_schema, r.table_name,
      cols_sql,
      r.table_schema, r.table_name,
      r.table_schema, r.table_name
    );

    execute sql;
  end loop;
end $$;