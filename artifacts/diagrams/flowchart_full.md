````mermaid
flowchart LR
  %% ======================
  %% SALES ORDER → CASH
  %% ======================
  subgraph S["🛒 SALES ORDER → CASH"]
    C[Customers] --> O[Orders]
    E[Employees] --> O
    SM[Shipping Methods] --> O

    O --> OD[Order Details]
    P[Products] --> OD

    PM[Payment Methods] --> PAY[Payments]
    O --> PAY
  end

  %% ======================
  %% PROCURE → STOCK
  %% ======================
  subgraph R["📦 PROCURE → STOCK"]
    SUP[Suppliers] --> PO[Purchase Orders]
    E --> PO
    SM --> PO

    PO --> IT[Inventory Transactions]
    P --> IT
  end
````