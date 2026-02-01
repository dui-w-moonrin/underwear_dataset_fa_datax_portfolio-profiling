# SQL reference
This document as as sql guide and reference how to find table stats and their dictionaries

## DISTINCT
get a duplicate distinct list with count number

```
select
  col_value,
  count(*) as cnt
from (
  select
    coalesce(nullif(trim(<col>), ''), '[NULL]') as col_value
  from stg.<table_name>
) x
group by 1
order by cnt desc, col_value;
```
### example

```
select
  col_value,
  count(*) as cnt
from (
  select
    coalesce(nullif(trim(region), ''), '[NULL]') as col_value
  from stg.customers
) x
group by 1
order by cnt desc, col_value;
```

## SUM #DISTINCT INCLUDE NULL
```
with norm as (
  select coalesce(nullif(trim(<col>), ''), '[NULL]') as v
  from stg.<table_name>
)
select
  count(distinct v) as distinct_including_null,
  count(*) filter (where v = '[NULL]') as null_rows_in_column
from norm
```
### example
```
with norm as (
  select coalesce(nullif(trim(order_id), ''), '[NULL]') as v
  from stg.order_details
)
select
  count(distinct v) as distinct_including_null,
  count(*) filter (where v = '[NULL]') as null_rows_in_column
from norm;
```


## Export dictionary output to CSV (psql \copy)

If you want to store dictionaries as files (so README/docs stay short), you can export any query to CSV:

```
\copy (
  select
    col_value,
    count(*) as cnt
  from (
    select coalesce(nullif(trim(<col_name>), ''), '[NULL]') as col_value
    from stg.<table_name>
  ) x
  group by 1
  order by cnt desc, col_value
) to 'artifacts/tabledictionaries/<table_name>__<col_name>.csv' with (format csv, header true);
```

## MIN-MAX DATE
get a min and max date of certain column at certain table
```
select
  min(to_date(<date_col>, 'FMMM/FMDD/YYYY')) as date_min,
  max(to_date(<date_col>, 'FMMM/FMDD/YYYY')) as date_max
from stg.<table_name>
where <date_col> is not null and trim(<date_col>) <> '';
```

### example

```
select
  min(to_date(order_date, 'FMMM/FMDD/YYYY')) as date_min,
  max(to_date(order_date, 'FMMM/FMDD/YYYY')) as date_max
from stg.orders
where order_date ~ '^\d{1,2}/\d{1,2}/\d{4}$';
```

### OrderDate > ShipDate
check bad rows order after ship, how many order date > ship date 

```
select
  count(*) as bad_rows_order_after_ship
from stg.orders
where order_date ~ '^\d{1,2}/\d{1,2}/\d{4}$'
  and ship_date  ~ '^\d{1,2}/\d{1,2}/\d{4}$'
  and to_date(order_date, 'FMMM/FMDD/YYYY') > to_date(ship_date, 'FMMM/FMDD/YYYY');
```
