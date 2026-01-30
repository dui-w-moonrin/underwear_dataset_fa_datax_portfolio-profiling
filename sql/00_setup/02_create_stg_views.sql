-- 02_create_stg_views.sql
-- stg views: normalize names to snake_case, trim blanks to NULL,
-- and normalize *ID-like* keys that may appear as "1.0" (CSV float artifacts).
--
-- Key rule (applied to *_id columns):
-- - NULL / empty -> NULL
-- - If value looks numeric like 123 or 123.0 / 123.00 -> cast to bigint text => "123"
-- - Else keep original text
--
-- This prevents FK checks from falsely reporting orphans due to "1.0" vs "1".

create schema if not exists stg;

-- =========================
-- customers
-- =========================
create or replace view stg.customers as
select
  case
    when "CustomerID" is null or btrim("CustomerID") = '' then null
    when "CustomerID" ~ '^\d+(\.0+)?$' then ("CustomerID"::numeric)::bigint::text
    else btrim("CustomerID")
  end                                          as customer_id,
  nullif(btrim("CustomerName"), '')            as customer_name,
  nullif(btrim("Region"), '')                  as region,
  nullif(btrim("Country"), '')                 as country,
  nullif(btrim("PriceCategory"), '')           as price_category,
  nullif(btrim("CustomerClass"), '')           as customer_class,
  nullif(btrim("LeadSource"), '')              as lead_source,
  nullif(btrim("Discontinued"), '')            as discontinued
from raw.customers;

-- =========================
-- employees
-- =========================
create or replace view stg.employees as
select
  case
    when "EmployeeID" is null or btrim("EmployeeID") = '' then null
    when "EmployeeID" ~ '^\d+(\.0+)?$' then ("EmployeeID"::numeric)::bigint::text
    else btrim("EmployeeID")
  end                                          as employee_id,
  nullif(btrim("EmployeeName"), '')            as employee_name
from raw.employees;

-- =========================
-- inventory_transactions
-- =========================
create or replace view stg.inventory_transactions as
select
  case
    when "TransactionID" is null or btrim("TransactionID") = '' then null
    when "TransactionID" ~ '^\d+(\.0+)?$' then ("TransactionID"::numeric)::bigint::text
    else btrim("TransactionID")
  end                                          as transaction_id,

  case
    when "ProductID" is null or btrim("ProductID") = '' then null
    when "ProductID" ~ '^\d+(\.0+)?$' then ("ProductID"::numeric)::bigint::text
    else btrim("ProductID")
  end                                          as product_id,

  case
    when "PurchaseOrderID" is null or btrim("PurchaseOrderID") = '' then null
    when "PurchaseOrderID" ~ '^\d+(\.0+)?$' then ("PurchaseOrderID"::numeric)::bigint::text
    else btrim("PurchaseOrderID")
  end                                          as purchase_order_id,

  case
    when "MissingID" is null or btrim("MissingID") = '' then null
    when "MissingID" ~ '^\d+(\.0+)?$' then ("MissingID"::numeric)::bigint::text
    else btrim("MissingID")
  end                                          as missing_id,

  nullif(btrim("TransactionDate"), '')         as transaction_date,
  nullif(btrim("UnitPurchasePrice"), '')       as unit_purchase_price,
  nullif(btrim("QuantityOrdered"), '')         as quantity_ordered,
  nullif(btrim("QuantityReceived"), '')        as quantity_received,
  nullif(btrim("QuantityMissing"), '')         as quantity_missing
from raw.inventory_transactions;

-- =========================
-- order_details
-- =========================
create or replace view stg.order_details as
select
  case
    when "OrderDetailID" is null or btrim("OrderDetailID") = '' then null
    when "OrderDetailID" ~ '^\d+(\.0+)?$' then ("OrderDetailID"::numeric)::bigint::text
    else btrim("OrderDetailID")
  end                                          as order_detail_id,

  case
    when "OrderID" is null or btrim("OrderID") = '' then null
    when "OrderID" ~ '^\d+(\.0+)?$' then ("OrderID"::numeric)::bigint::text
    else btrim("OrderID")
  end                                          as order_id,

  case
    when "ProductID" is null or btrim("ProductID") = '' then null
    when "ProductID" ~ '^\d+(\.0+)?$' then ("ProductID"::numeric)::bigint::text
    else btrim("ProductID")
  end                                          as product_id,

  nullif(btrim("QuantitySold"), '')            as quantity_sold,
  nullif(btrim("UnitSalesPrice"), '')          as unit_sales_price
from raw.order_details;

-- =========================
-- orders
-- =========================
create or replace view stg.orders as
select
  case
    when "OrderID" is null or btrim("OrderID") = '' then null
    when "OrderID" ~ '^\d+(\.0+)?$' then ("OrderID"::numeric)::bigint::text
    else btrim("OrderID")
  end                                          as order_id,

  case
    when "CustomerID" is null or btrim("CustomerID") = '' then null
    when "CustomerID" ~ '^\d+(\.0+)?$' then ("CustomerID"::numeric)::bigint::text
    else btrim("CustomerID")
  end                                          as customer_id,

  case
    when "EmployeeID" is null or btrim("EmployeeID") = '' then null
    when "EmployeeID" ~ '^\d+(\.0+)?$' then ("EmployeeID"::numeric)::bigint::text
    else btrim("EmployeeID")
  end                                          as employee_id,

  -- IMPORTANT: fixes "1.0" vs "1" mismatch for FK join
  case
    when "ShippingMethodID" is null or btrim("ShippingMethodID") = '' then null
    when "ShippingMethodID" ~ '^\d+(\.0+)?$' then ("ShippingMethodID"::numeric)::bigint::text
    else btrim("ShippingMethodID")
  end                                          as shipping_method_id,

  nullif(btrim("OrderDate"), '')               as order_date,
  nullif(btrim("ShipDate"), '')                as ship_date,
  nullif(btrim("FreightCharge"), '')           as freight_charge
from raw.orders;

-- =========================
-- payment_methods
-- =========================
create or replace view stg.payment_methods as
select
  case
    when "PaymentMethodID" is null or btrim("PaymentMethodID") = '' then null
    when "PaymentMethodID" ~ '^\d+(\.0+)?$' then ("PaymentMethodID"::numeric)::bigint::text
    else btrim("PaymentMethodID")
  end                                          as payment_method_id,
  nullif(btrim("PaymentMethod"), '')           as payment_method
from raw.payment_methods;

-- =========================
-- payments
-- =========================
create or replace view stg.payments as
select
  case
    when "PaymentID" is null or btrim("PaymentID") = '' then null
    when "PaymentID" ~ '^\d+(\.0+)?$' then ("PaymentID"::numeric)::bigint::text
    else btrim("PaymentID")
  end                                          as payment_id,

  case
    when "OrderID" is null or btrim("OrderID") = '' then null
    when "OrderID" ~ '^\d+(\.0+)?$' then ("OrderID"::numeric)::bigint::text
    else btrim("OrderID")
  end                                          as order_id,

  -- IMPORTANT: fixes "1.0" vs "1" mismatch for FK join
  case
    when "PaymentMethodID" is null or btrim("PaymentMethodID") = '' then null
    when "PaymentMethodID" ~ '^\d+(\.0+)?$' then ("PaymentMethodID"::numeric)::bigint::text
    else btrim("PaymentMethodID")
  end                                          as payment_method_id,

  nullif(btrim("PaymentDate"), '')             as payment_date,
  nullif(btrim("PaymentAmount"), '')           as payment_amount
from raw.payments;

-- =========================
-- products
-- =========================
create or replace view stg.products as
select
  case
    when "ProductID" is null or btrim("ProductID") = '' then null
    when "ProductID" ~ '^\d+(\.0+)?$' then ("ProductID"::numeric)::bigint::text
    else btrim("ProductID")
  end                                          as product_id,
  nullif(btrim("ProductName"), '')             as product_name,
  nullif(btrim("Color"), '')                   as color,
  nullif(btrim("ModelDescription"), '')        as model_description,
  nullif(btrim("FabricDescription"), '')       as fabric_description,
  nullif(btrim("Category"), '')                as category,
  nullif(btrim("Gender"), '')                  as gender,
  nullif(btrim("ProductLine"), '')             as product_line,
  nullif(btrim("Weight"), '')                  as weight,
  nullif(btrim("Size"), '')                    as size,
  nullif(btrim("PackSize"), '')                as pack_size,
  nullif(btrim("Status"), '')                  as status,
  nullif(btrim("InventoryDate"), '')           as inventory_date,
  nullif(btrim("PurchasePrice"), '')           as purchase_price
from raw.products;

-- =========================
-- purchase_orders
-- =========================
create or replace view stg.purchase_orders as
select
  case
    when "PurchaseOrderID" is null or btrim("PurchaseOrderID") = '' then null
    when "PurchaseOrderID" ~ '^\d+(\.0+)?$' then ("PurchaseOrderID"::numeric)::bigint::text
    else btrim("PurchaseOrderID")
  end                                          as purchase_order_id,

  case
    when "SupplierID" is null or btrim("SupplierID") = '' then null
    when "SupplierID" ~ '^\d+(\.0+)?$' then ("SupplierID"::numeric)::bigint::text
    else btrim("SupplierID")
  end                                          as supplier_id,

  case
    when "EmployeeID" is null or btrim("EmployeeID") = '' then null
    when "EmployeeID" ~ '^\d+(\.0+)?$' then ("EmployeeID"::numeric)::bigint::text
    else btrim("EmployeeID")
  end                                          as employee_id,

  -- IMPORTANT: fixes "1.0" vs "1" mismatch for FK join
  case
    when "ShippingMethodID" is null or btrim("ShippingMethodID") = '' then null
    when "ShippingMethodID" ~ '^\d+(\.0+)?$' then ("ShippingMethodID"::numeric)::bigint::text
    else btrim("ShippingMethodID")
  end                                          as shipping_method_id,

  nullif(btrim("OrderDate"), '')               as order_date
from raw.purchase_orders;

-- =========================
-- shipping_methods
-- =========================
create or replace view stg.shipping_methods as
select
  case
    when "ShippingMethodID" is null or btrim("ShippingMethodID") = '' then null
    when "ShippingMethodID" ~ '^\d+(\.0+)?$' then ("ShippingMethodID"::numeric)::bigint::text
    else btrim("ShippingMethodID")
  end                                          as shipping_method_id,
  nullif(btrim("ShippingMethod"), '')          as shipping_method
from raw.shipping_methods;

-- =========================
-- suppliers
-- =========================
create or replace view stg.suppliers as
select
  case
    when "SupplierID" is null or btrim("SupplierID") = '' then null
    when "SupplierID" ~ '^\d+(\.0+)?$' then ("SupplierID"::numeric)::bigint::text
    else btrim("SupplierID")
  end                                          as supplier_id,
  nullif(btrim("SupplierName"), '')            as supplier_name
from raw.suppliers;
