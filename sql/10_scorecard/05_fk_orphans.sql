-- 05_fk_orphans.sql
-- Option A FK orphan checks (detail + rollup per child table)

create schema if not exists dq;

do $$
declare
  rel record;
  t_schema text := 'stg';
  sql text;
  orphan_cnt bigint;
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
    sql := format($q$
      select count(*)::bigint
      from %I.%I c
      left join %I.%I p
        on c.%I = p.%I
      where c.%I is not null
        and p.%I is null;
    $q$,
      t_schema, rel.child_table,
      t_schema, rel.parent_table,
      rel.child_fk_col, rel.parent_pk_col,
      rel.child_fk_col,
      rel.parent_pk_col
    );

    execute sql into orphan_cnt;

    insert into dq.fk_orphans_detail(
      child_schema, child_table, child_fk_col,
      parent_schema, parent_table, parent_pk_col,
      orphan_rows, checked_at
    )
    values (
      t_schema, rel.child_table, rel.child_fk_col,
      t_schema, rel.parent_table, rel.parent_pk_col,
      orphan_cnt, now()
    )
    on conflict (child_schema, child_table, child_fk_col, parent_schema, parent_table, parent_pk_col)
    do update set orphan_rows = excluded.orphan_rows, checked_at = excluded.checked_at;
  end loop;

  update dq.scorecard_table s
  set fk_orphan_rows = d.orphan_rows, updated_at = now()
  from (
    select child_schema as table_schema, child_table as table_name, sum(orphan_rows)::bigint as orphan_rows
    from dq.fk_orphans_detail
    group by child_schema, child_table
  ) d
  where s.table_schema = d.table_schema
    and s.table_name = d.table_name;
end $$;