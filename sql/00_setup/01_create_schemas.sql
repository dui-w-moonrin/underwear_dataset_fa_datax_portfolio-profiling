-- 01_create_schemas.sql
create schema if not exists raw;
create schema if not exists stg;

-- RAW TABLES (as-is from Kaggle CSV headers)
create table if not exists raw.customers (
  "CustomerID" text,
  "CustomerName" text,
  "Region" text,
  "Country" text,
  "PriceCategory" text,
  "CustomerClass" text,
  "LeadSource" text,
  "Discontinued" text
);

create table if not exists raw.employees (
  "EmployeeID" text,
  "EmployeeName" text
);

create table if not exists raw.inventory_transactions (
  "TransactionID" text,
  "ProductID" text,
  "PurchaseOrderID" text,
  "MissingID" text,
  "TransactionDate" text,
  "UnitPurchasePrice" text,
  "QuantityOrdered" text,
  "QuantityReceived" text,
  "QuantityMissing" text
);

create table if not exists raw.order_details (
  "OrderDetailID" text,
  "OrderID" text,
  "ProductID" text,
  "QuantitySold" text,
  "UnitSalesPrice" text
);

create table if not exists raw.orders (
  "OrderID" text,
  "CustomerID" text,
  "EmployeeID" text,
  "ShippingMethodID" text,
  "OrderDate" text,
  "ShipDate" text,
  "FreightCharge" text
);

create table if not exists raw.payment_methods (
  "PaymentMethodID" text,
  "PaymentMethod" text
);

create table if not exists raw.payments (
  "PaymentID" text,
  "OrderID" text,
  "PaymentMethodID" text,
  "PaymentDate" text,
  "PaymentAmount" text
);

create table if not exists raw.products (
  "ProductID" text,
  "ProductName" text,
  "Color" text,
  "ModelDescription" text,
  "FabricDescription" text,
  "Category" text,
  "Gender" text,
  "ProductLine" text,
  "Weight" text,
  "Size" text,
  "PackSize" text,
  "Status" text,
  "InventoryDate" text,
  "PurchasePrice" text
);

create table if not exists raw.purchase_orders (
  "PurchaseOrderID" text,
  "SupplierID" text,
  "EmployeeID" text,
  "ShippingMethodID" text,
  "OrderDate" text
);

create table if not exists raw.shipping_methods (
  "ShippingMethodID" text,
  "ShippingMethod" text
);

create table if not exists raw.suppliers (
  "SupplierID" text,
  "SupplierName" text
);
