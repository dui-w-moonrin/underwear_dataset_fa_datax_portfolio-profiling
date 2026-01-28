-- 02_create_stg_views.sql
-- stg views: normalize names to snake_case and do light trimming
-- (casting types can be added later; keep it simple first)

create or replace view stg.customers as
select
  nullif(trim("CustomerID"), '')          as customer_id,
  nullif(trim("CustomerName"), '')        as customer_name,
  nullif(trim("Region"), '')              as region,
  nullif(trim("Country"), '')             as country,
  nullif(trim("PriceCategory"), '')       as price_category,
  nullif(trim("CustomerClass"), '')       as customer_class,
  nullif(trim("LeadSource"), '')          as lead_source,
  nullif(trim("Discontinued"), '')        as discontinued
from raw.customers;

create or replace view stg.employees as
select
  nullif(trim("EmployeeID"), '')          as employee_id,
  nullif(trim("EmployeeName"), '')        as employee_name
from raw.employees;

create or replace view stg.inventory_transactions as
select
  nullif(trim("TransactionID"), '')       as transaction_id,
  nullif(trim("ProductID"), '')           as product_id,
  nullif(trim("PurchaseOrderID"), '')     as purchase_order_id,
  nullif(trim("MissingID"), '')           as missing_id,
  nullif(trim("TransactionDate"), '')     as transaction_date,
  nullif(trim("UnitPurchasePrice"), '')   as unit_purchase_price,
  nullif(trim("QuantityOrdered"), '')     as quantity_ordered,
  nullif(trim("QuantityReceived"), '')    as quantity_received,
  nullif(trim("QuantityMissing"), '')     as quantity_missing
from raw.inventory_transactions;

create or replace view stg.order_details as
select
  nullif(trim("OrderDetailID"), '')       as order_detail_id,
  nullif(trim("OrderID"), '')             as order_id,
  nullif(trim("ProductID"), '')           as product_id,
  nullif(trim("QuantitySold"), '')        as quantity_sold,
  nullif(trim("UnitSalesPrice"), '')      as unit_sales_price
from raw.order_details;

create or replace view stg.orders as
select
  nullif(trim("OrderID"), '')             as order_id,
  nullif(trim("CustomerID"), '')          as customer_id,
  nullif(trim("EmployeeID"), '')          as employee_id,
  nullif(trim("ShippingMethodID"), '')    as shipping_method_id,
  nullif(trim("OrderDate"), '')           as order_date,
  nullif(trim("ShipDate"), '')            as ship_date,
  nullif(trim("FreightCharge"), '')       as freight_charge
from raw.orders;

create or replace view stg.payment_methods as
select
  nullif(trim("PaymentMethodID"), '')     as payment_method_id,
  nullif(trim("PaymentMethod"), '')       as payment_method
from raw.payment_methods;

create or replace view stg.payments as
select
  nullif(trim("PaymentID"), '')           as payment_id,
  nullif(trim("OrderID"), '')             as order_id,
  nullif(trim("PaymentMethodID"), '')     as payment_method_id,
  nullif(trim("PaymentDate"), '')         as payment_date,
  nullif(trim("PaymentAmount"), '')       as payment_amount
from raw.payments;

create or replace view stg.products as
select
  nullif(trim("ProductID"), '')           as product_id,
  nullif(trim("ProductName"), '')         as product_name,
  nullif(trim("Color"), '')               as color,
  nullif(trim("ModelDescription"), '')    as model_description,
  nullif(trim("FabricDescription"), '')   as fabric_description,
  nullif(trim("Category"), '')            as category,
  nullif(trim("Gender"), '')              as gender,
  nullif(trim("ProductLine"), '')         as product_line,
  nullif(trim("Weight"), '')              as weight,
  nullif(trim("Size"), '')                as size,
  nullif(trim("PackSize"), '')            as pack_size,
  nullif(trim("Status"), '')              as status,
  nullif(trim("InventoryDate"), '')       as inventory_date,
  nullif(trim("PurchasePrice"), '')       as purchase_price
from raw.products;

create or replace view stg.purchase_orders as
select
  nullif(trim("PurchaseOrderID"), '')     as purchase_order_id,
  nullif(trim("SupplierID"), '')          as supplier_id,
  nullif(trim("EmployeeID"), '')          as employee_id,
  nullif(trim("ShippingMethodID"), '')    as shipping_method_id,
  nullif(trim("OrderDate"), '')           as order_date
from raw.purchase_orders;

create or replace view stg.shipping_methods as
select
  nullif(trim("ShippingMethodID"), '')    as shipping_method_id,
  nullif(trim("ShippingMethod"), '')      as shipping_method
from raw.shipping_methods;

create or replace view stg.suppliers as
select
  nullif(trim("SupplierID"), '')          as supplier_id,
  nullif(trim("SupplierName"), '')        as supplier_name
from raw.suppliers;
