# ER Diagram — Full (As-is) — Underwear Dataset (11 Tables)

This document captures the dataset ER **as provided (as-is)**, plus a **Mermaid ER version** (text-based) so the diagram is reproducible and easy to review in PRs.

---

## 1) ER Diagram

![ER Diagram](/artifacts/diagrams/er-diagram-full-as-is.png "ER Diagram")

---

## 2) ER Diagram (Mermaid — Reproducible)

> Paste this block into https://mermaid.live (or render in GitHub Markdown that supports Mermaid).

```mermaid
erDiagram
  CUSTOMERS ||--o{ ORDERS : "CustomerID"
  EMPLOYEES ||--o{ ORDERS : "EmployeeID"
  SHIPPING_METHODS ||--o{ ORDERS : "ShippingMethodID"

  ORDERS ||--o{ ORDER_DETAILS : "OrderID"
  PRODUCTS ||--o{ ORDER_DETAILS : "ProductID"

  ORDERS ||--o{ PAYMENTS : "OrderID"
  PAYMENT_METHODS ||--o{ PAYMENTS : "PaymentMethodID"

  SUPPLIERS ||--o{ PURCHASE_ORDERS : "SupplierID"
  EMPLOYEES ||--o{ PURCHASE_ORDERS : "EmployeeID"
  SHIPPING_METHODS ||--o{ PURCHASE_ORDERS : "ShippingMethodID"

  PURCHASE_ORDERS ||--o{ INVENTORY_TRANSACTIONS : "PurchaseOrderID"
  PRODUCTS ||--o{ INVENTORY_TRANSACTIONS : "ProductID"

  CUSTOMERS {
    int CustomerID PK
    string CustomerName
    string Region
    string Country
    string PriceCategory
    string CustomerClass
    string LeadSource
    string Discontinued
  }

  EMPLOYEES {
    int EmployeeID PK
    string EmployeeName
  }

  SHIPPING_METHODS {
    int ShippingMethodID PK
    string ShippingMethod
  }

  PAYMENT_METHODS {
    int PaymentMethodID PK
    string PaymentMethod
  }

  ORDERS {
    int OrderID PK
    int CustomerID FK
    int EmployeeID FK
    int ShippingMethodID FK
    date OrderDate
    date ShipDate
    float FreightCharge
  }

  ORDER_DETAILS {
    int OrderDetailID PK
    int OrderID FK
    int ProductID FK
    int QuantitySold
    float UnitSalesPrice
  }

  PAYMENTS {
    int PaymentID PK
    int OrderID FK
    int PaymentMethodID FK
    date PaymentDate
    float PaymentAmount
  }

  SUPPLIERS {
    int SupplierID PK
    string SupplierName
  }

  PURCHASE_ORDERS {
    int PurchaseOrderID PK
    int SupplierID FK
    int EmployeeID FK
    int ShippingMethodID FK
    date OrderDate
  }

  INVENTORY_TRANSACTIONS {
    int TransactionID PK
    int ProductID FK
    int PurchaseOrderID FK
    int MissingID
    date TransactionDate
    float UnitPurchasePrice
    int QuantityOrdered
    int QuantityReceived
    int QuantityMissing
  }

  PRODUCTS {
    int ProductID PK
    string ProductName
    string Color
    string ModelDescription
    string FabricDescription
    string Category
    string Gender
    string ProductLine
    float Weight
    string Size
    string PackSize
    string Status
    date InventoryDate
    float PurchasePrice
  }
```

---

## 3) Tables Overview (Row Counts / “Weight”)

This helps readers interpret the ER quickly: **big tables** are event/transaction-heavy, while **small tables** are reference/lookup.

### A) Large / transactional (fact-like)
- `order_details` — **105,757**
- `inventory_transactions` — **20,951**
- `orders` — **2,286**
- `payments` — **686**

### B) Reference / lookup (dimension-like)
- `products` — **4,183** (mid-sized master table)
- `customers` — **225**
- `purchase_orders` — **232**
- `employees` — **15**
- `suppliers` — **2**
- `shipping_methods` — **4**
- `payment_methods` — **3**

> Source: `artifacts/scorecard.csv` (row_count)

---

## 4) Relationship List (As-is)

### Sales / Order-to-Cash
- `orders.customer_id` → `customers.customer_id`
- `orders.employee_id` → `employees.employee_id`
- `orders.shipping_method_id` → `shipping_methods.shipping_method_id`
- `order_details.order_id` → `orders.order_id`
- `order_details.product_id` → `products.product_id`
- `payments.order_id` → `orders.order_id`
- `payments.payment_method_id` → `payment_methods.payment_method_id`

### Procure / Purchase-to-Stock
- `purchase_orders.supplier_id` → `suppliers.supplier_id`
- `purchase_orders.employee_id` → `employees.employee_id`
- `purchase_orders.shipping_method_id` → `shipping_methods.shipping_method_id`
- `inventory_transactions.purchase_order_id` → `purchase_orders.purchase_order_id`
- `inventory_transactions.product_id` → `products.product_id`

---

## 4) Naming / Quoting Note (SQL Practicality)

The raw CSV uses **CamelCase** headers (e.g., `OrderID`). In PostgreSQL:
- unquoted identifiers are folded to lowercase
- therefore, referencing CamelCase columns requires **double quotes**: `"OrderID"`

This repo avoids that friction by exposing **`stg` views with normalized lowercase snake_case** (e.g., `order_id`), so all scorecard SQL stays clean.


### References
- ER image: `artifacts/diagrams/er_kaggle_as_is.png`
- Scorecard output: `artifacts/scorecard.csv`
