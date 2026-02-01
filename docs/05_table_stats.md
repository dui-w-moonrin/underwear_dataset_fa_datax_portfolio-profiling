# Table Statistics — Underwear Dataset (11 tables)

## Overview
- Total tables: 11 (stg views)
- Largest tables: order_details (~105k), inventory_transactions (~20k), products (~4k), orders (~2.3k)
- Primary business flow: Purchase → Inventory → Orders → Payments



## Notes
- Source CSV date fields are text. For table stats, dates shown in `date_min/date_max` are parsed into ISO format (`YYYY-MM-DD`) during profiling.


### Customers
**Role:**
- Customer master (who buys). Used to segment orders/payments by region, class, price tier, and lead source.

|#rows   |#Column|
|--------|-------|
|225     |8      |     

|Data Type|Column         |key|#Distinct|
|---------|---------------|---|---------|
|int      |CustomerID     |PK |225      |  
|string   |CustomerName   |   |225      |
|string   |Region         |   |87       |
|string   |Country        |   |2        |
|string   |PriceCategory  |   |7        |
|string   |CustomerClass  |   |7        |
|string   |LeadSource     |   |9        |
|string   |Discontinued   |   |2        |

**dictionary**
full dict list in 
`artifacts/tabledictionaries/stg__customers__country__dict.csv`
`artifacts/tabledictionaries/stg__customers__class__dict.csv`
`artifacts/tabledictionaries/stg__discontinued__dict.csv`
`artifacts/tabledictionaries/stg__lead_source__dict.csv`
`artifacts/tabledictionaries/stg__price_category__dict.csv`
`artifacts/tabledictionaries/stg__region__dict.csv`


### Employees
**Role:**
- Reference table (small lookup).

|#rows   |#Column|
|--------|-------|
|15      |2      | 

|Data Type|Column         |Key|#Distinct|
|---------|---------------|---|---------|
|int      |EmployeeID     |PK |15       |  
|string   |EmployeeName   |   |15       |

**dictionary**
full dict list in 
`artifacts/tabledictionaries/stg__employees_employee_name__dict.csv`

### InventoryTransactions
**Role:**
- Inventory movement / receiving log tied to purchase orders and products. Useful to validate PO→inventory integrity and quantify missing/received gaps.

|#rows   |#Column|
|--------|-------|
|20951   |9      | 


|Data Type|Column           |Key|#Distinct|NULL |
|---------|-----------------|---|---------|-----|
|int      |TransactionID    |PK |20951    |     |
|int      |ProductID        |FK |4140     |     |
|int      |PurchaseOrderID  |FK |223      |3345 |
|int      |MissingID        |   |28       |18757|
|date     |TransactionDate  |   |181      |     |
|float    |UnitPurchasePrice|   |253      |1151 |  
|int      |QuantityOrdered  |   |269      |2195 |
|int      |QuantityReceived |   |269      |2227 |
|int      |QuantityMissing  |   |94       |18757|
***#dictinct include [NULL] (if exist)***

|FIELD          |date_min  |date_max  |
|---------------|----------|----------|
|TransactionDate|2003-05-29|2006-04-05|


|FIELD|UnitPurchasePrice |QuantityOrdered  |QuantityReceived  |QuantityMissing  |
|-----|------------------|-----------------|------------------|-----------------|
|count|19800.0           |18756.0          |18724.0           |2194.0           |
|mean |4.486483838383839 |40.93932608232032|40.992576372569964|8.185050136736555|
|std  |2.0208867039237695|51.79282033738611|51.88784385488549 |32.72340431538817|
|min  |0.0               |0.0              |0.0               |0.0              |
|25%  |3.3               |10.0             |10.0              |0.0              |
|50%  |4.3               |30.0             |30.0              |1.0              |
|75%  |5.35              |50.0             |50.0              |2.0              |
|max  |14.5              |1475.0           |1475.0            |732.0            |

### OrderDetails
**Role:**
- Order line items (the sales fact grain). Drives product-level revenue/volume analysis and is the largest sales-related table.

|#rows   |#Column|
|--------|-------|
|105757  |5      |

|Data Type|Column        |Key|#Distinct|
|---------|--------------|---|---------|
|int      |OrderDetailID |PK |105757   |
|int      |OrderID       |FK |2286     |
|int      |ProductID     |FK |4042     |
|int      |QuantitySold  |   |165      |
|float    |UnitSalesPrice|   |237      |

**Stats**
|FIELD|QuantitySold      |UnitSalesPrice    |
|-----|------------------|------------------|
|count|105757.0          |105757.0          |
|mean |6.467713721077565 |6.789183411027166 |
|std  |9.572007686182564 |3.0611225612125867|
|min  |0.0               |0.0               |
|25%  |1.0               |4.8               |
|50%  |4.0               |6.3               |
|75%  |10.0              |8.2               |
|max  |612.0             |35.0              |

### Orders
**Role:**
- Order header (order lifecycle + shipping link). Parent table for order_details and payments; anchors date-based analysis.

|#rows   |#Column|
|--------|-------|
|2286    |7      |

|Data Type|Column          |Key|#Distinct|
|---------|----------------|---|---------|
|int      |OrderID         |PK |2286     |
|int      |CustomerID      |FK |222      |
|int      |EmployeeID      |FK |10       |
|int      |ShippingMethodID|FK |3        |
|date     |OrderDate       |   |746      |
|date     |ShipDate        |   |755      |
|float    |FreightCharge   |   |34       |

|FIELD    |date_min  |date_max  |
|---------|----------|----------|
|OrderDate|2003-07-11|2006-04-20|
|ShipDate |2001-10-11|2006-04-20|

OrderDate > ShipDate|
--------------------+
                  12|

## PaymentMethods
**Role:**
- Reference table (small lookup).

|#rows|#Column|
|-----|-------|
|3    |2      |

|Data Type|Column          |Key|#Distinct|
|---------|----------------|---|---------|
|int      |PaymentMethodID |PK |3        |
|string   |PaymentMethod   |   |3        |

**dictionary**
|col_value    |cnt|
|-------------|---|
|Bank Transfer|1  |
|Cash         |1  |
|On Credit    |1  |

### Payments
**Role:**
- Payment events against orders (cashflow). Supports order-to-cash checks and payment method distribution; includes amount/date.

|#rows|#Column|
|-----|-------|
|686  |5      |

|Data Type|Column          |Key|#Distinct|NULL |
|---------|----------------|---|---------|-----|
|int      |PaymentID       |PK |686      |     |
|int      |OrderID         |FK |658      |     |
|int      |PaymentMethodID |FK |3        |1    |
|date     |PaymentDate     |   |225      |     |
|float    |PaymentAmount   |   |673      |1    |

***#dictinct include [NULL] (if exist)***

|FIELD      |date_min  |date_max  |
|-----------|----------|----------|
|PaymentDate|2003-04-06|2005-09-10|


**Stats**
|FIELD|PaymentAmount     |
|-----|------------------|
|count|685.0             |
|mean |1224.7577372262774|
|std  |1788.0821604715966|
|min  |0.0               |
|25%  |167.59            |
|50%  |602.6             |
|75%  |1542.5            |
|max  |20534.7           |
***noticeable outlier (max 20543.7)***

### Products
**Role:**
- Product master (SKU attributes). Joins to order_details and inventory_transactions; enables category/gender/size segmentation and price analysis.

|#rows|#Column|
|-----|-------|
|4183 |14     |

|Data Type|Column           |Key|#Distinct|NULL |
|---------|-----------------|---|---------|-----|
|int      |ProductID        |PK |4183     |     |
|string   |ProductName      |   |4183     |     |
|string   |Color            |   |19       |4107 |
|string   |ModelDescription |   |106      |10   |
|string   |FabricDescription|   |335      |13   |
|string   |Category         |   |10       |     |
|string   |Gender           |   |12       |     |
|string   |ProductLine      |   |2        |     |
|float    |Weight           |   |705      |     |
|string   |Size             |   |25       |14   |
|string   |PackSize         |   |2        |     |
|string   |Status           |   |2        |     |
|date     |InventoryDate    |   |112      |     |
|float    |PurchasePrice    |   |231      |     |  

***#dictinct include [NULL] (if exist)***
***#[NULL] in color column is interested to look out***
***gender column number is high and is interested***


**dictionary**
full dict list in 
`artifacts/tabledictionaries/stg__products_color__dict.csv`
`artifacts/tabledictionaries/stg__products_model_description__dict.csv`
`artifacts/tabledictionaries/stg__products_fabric_description__dict.csv`
`artifacts/tabledictionaries/stg__category__dict.csv`
`artifacts/tabledictionaries/stg__gender__dict.csv`
`artifacts/tabledictionaries/stg__products_product_line__dict.csv`
`artifacts/tabledictionaries/stg__products_size__dict.csv`
`artifacts/tabledictionaries/stg__products_pack_size__dict.csv`
`artifacts/tabledictionaries/stg__products_status__dict.csv`

|FIELD        |date_min  |date_max  |
|-------------|----------|----------|
|InventoryDate|2003-07-10|2006-04-18|

**Stats**
|FIELD|PurchasePrice     |
|-----|------------------|
|count|4183.0            |
|mean |4.486679416686588 |
|std  |2.1074685448203985|
|min  |0.35              |
|25%  |3.35              |
|50%  |4.3               |
|75%  |5.4               |
|max  |14.0              |

### PurchaseOrders
**Role:**
- Purchase order header (procurement). Parent for inventory_transactions; links to supplier, employee, and shipping method.

|#rows|#Column|
|-----|-------|
|232  |5      |

|Data Type|Column           |Key|#Distinct|NULL |
|---------|-----------------|---|---------|-----|
|int      |PurchaseOrderID  |PK |232      |     |
|int      |SupplierID       |FK |2        |     |
|int      |EmployeeID       |FK |6        |     |
|int      |ShippingMethodID |FK |4        |5    |
|date     |OrderDate        |   |138      |     |
***#dictinct include [NULL] (if exist)***

|FIELD    |date_min  |date_max  |
|---------|----------|----------|
|OrderDate|2003-09-16|2006-04-05|

## ShippingMethods
**Role:**
- Reference table (small lookup).

|#rows|#Column|
|-----|-------|
|4    |2      |

|Data Type|Column           |Key|#Distinct|NULL |
|---------|-----------------|---|---------|-----|
|int      |ShippingMethodID |PK |4        |     |
|string   |ShippingMethod   |   |4        |     |

**dictionary**
|col_value           |cnt|
|--------------------|---|
|Container           |1  |
|Door to Door Service|1  |
|Ex Works            |1  |
|Truck               |1  |

### Suppliers
**Role:**
- Supplier reference (who supplies POs). Joins to purchase_orders for procurement grouping.

|#rows|#Column|
|-----|-------|
|2    |2      |     

|Data Type|Column           |Key|#Distinct|NULL |
|---------|-----------------|---|---------|-----|
|int      |SupplierID       |PK |2        |     |
|string   |SupplierName     |   |2        |     |

**dictionary**
|col_value    |cnt|
|-------------|---|
|S1           |1  |
|S2           |1  |