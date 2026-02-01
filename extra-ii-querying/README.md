## CTE-first SQL Pattern: Reduce Before Join (Order-Level Fact + Simple Windows)

This query demonstrates a practical pattern to keep joins efficient and results correct:

- **Filter early** (reduce rows before joining).
- **Aggregate “many-to-one” tables first** (`order_details`, `payments`) so they become **1 row per `order_id`**.
- **Join at the correct grain** (order-level) to avoid row explosion.
- Add **simple window functions** at the end to tell a customer-level time story.

### What this query outputs (1 row per order)
For each `order_id`, the query returns:
- Customer attributes (name, region/country, class/price category)
- Order dates + ship lead time
- Order metrics: `line_count`, `item_qty`, `gross_sales`, `freight_charge`, `order_total`
- Payment metrics: `payment_cnt`, `paid_amount`, `unpaid_amount`
- Window metrics: order sequence per customer, days since previous order, running spend per customer

---

## Step-by-step blocks (CTE by CTE)

### 1) `base_orders` — Filter early using data-quality/business rules
Goal: Reduce `orders` before any heavy joins, and keep only credible records.

- Require both dates (`order_date`, `ship_date`)
- Remove inconsistent dates (order date after ship date)
- Keep reasonable lead times
- Drop negative freight

### 2) `c` — Reduce customers (active only + only needed columns)
Goal: Avoid carrying unused columns and exclude inactive customers early.

### 3) `o` — Scope orders to active customers
Goal: Keep orders only for active customers (small join: orders ↔ customers).

### 4) `od_agg` — Aggregate `order_details` to order grain
Goal: Convert the largest table (`order_details`) into **1 row per order** before joining.

### 5) `p_agg` — Aggregate `payments` to order grain
Goal: Convert payments into **1 row per order** before joining.

### 6) `fact_order` — Assemble the order-level fact table
Goal: Join only at **order grain** (no row explosion), compute totals, and calculate unpaid amount.

### 7) Final SELECT — Add simple windows
Goal: Add customer-level time narrative on top of the order-level fact:
- `order_seq` = nth order for this customer
- `days_since_prev_order` = gap from previous order
- `customer_running_spend` = cumulative spend over time

---

## SQL (copy/paste)

```sql
WITH
/* 1) base_orders: filter early + meaningful rules
      grain: 1 row / order_id */
base_orders AS (
  SELECT
    o.order_id,
    o.customer_id,
    o.employee_id,
    o.order_date::date AS order_date,
    o.ship_date::date  AS ship_date,
    COALESCE(o.freight_charge, 0)::numeric(18,2) AS freight_charge,
    o.ship_lead_days
  FROM clean.orders o
  WHERE o.order_date IS NOT NULL
    AND o.ship_date  IS NOT NULL
    AND o.is_orderdate_gt_shipdate = FALSE
    AND o.ship_lead_days BETWEEN 0 AND 30
    AND COALESCE(o.freight_charge, 0) >= 0
),

/* 2) c: reduce customers (active only + keep only what we need)
      grain: 1 row / customer_id */
c AS (
  SELECT
    c.customer_id,
    c.customer_name,
    c.region,
    c.country,
    c.customer_class,
    c.price_category
  FROM clean.customers c
  WHERE COALESCE(c.discontinued, 0) = 0
),

/* 3) o: keep orders only for active customers
      grain: 1 row / order_id */
o AS (
  SELECT
    bo.order_id,
    bo.customer_id,
    bo.employee_id,
    bo.order_date,
    bo.ship_date,
    bo.freight_charge,
    bo.ship_lead_days
  FROM base_orders bo
  JOIN c
    ON c.customer_id = bo.customer_id
),

/* 4) od_agg: aggregate order_details BEFORE join (prevents row explosion)
      grain: 1 row / order_id */
od_agg AS (
  SELECT
    od.order_id,
    COUNT(*) AS line_count,
    SUM(od.quantity_sold)::numeric AS item_qty,
    SUM(od.quantity_sold * od.unit_sales_price)::numeric(18,2) AS gross_sales
  FROM clean.order_details od
  JOIN o
    ON o.order_id = od.order_id
  GROUP BY od.order_id
),

/* 5) p_agg: aggregate payments BEFORE join
      grain: 1 row / order_id */
p_agg AS (
  SELECT
    p.order_id,
    COUNT(*) AS payment_cnt,
    SUM(p.payment_amount)::numeric(18,2) AS paid_amount
  FROM clean.payments p
  JOIN o
    ON o.order_id = p.order_id
  GROUP BY p.order_id
),

/* 6) fact_order: order-level fact table (grain stays 1 row / order_id) */
fact_order AS (
  SELECT
    o.order_id,
    o.order_date,
    o.ship_date,
    o.customer_id,

    c.customer_name,
    c.region,
    c.country,
    c.customer_class,
    c.price_category,

    o.ship_lead_days,

    COALESCE(od.line_count, 0) AS line_count,
    COALESCE(od.item_qty, 0) AS item_qty,
    COALESCE(od.gross_sales, 0)::numeric(18,2) AS gross_sales,

    o.freight_charge,
    (COALESCE(od.gross_sales, 0) + o.freight_charge)::numeric(18,2) AS order_total,

    COALESCE(p.paid_amount, 0)::numeric(18,2) AS paid_amount,
    COALESCE(p.payment_cnt, 0) AS payment_cnt,

    ((COALESCE(od.gross_sales, 0) + o.freight_charge) - COALESCE(p.paid_amount, 0))::numeric(18,2)
      AS unpaid_amount

  FROM o
  LEFT JOIN od_agg od ON od.order_id = o.order_id
  LEFT JOIN p_agg  p  ON p.order_id  = o.order_id
  JOIN c              ON c.customer_id = o.customer_id
)

/* 7) final: simple windows over the order-level fact */
SELECT
  f.*,

  ROW_NUMBER() OVER (
    PARTITION BY f.customer_id
    ORDER BY f.order_date, f.order_id
  ) AS order_seq,

  (f.order_date - LAG(f.order_date) OVER (
     PARTITION BY f.customer_id
     ORDER BY f.order_date, f.order_id
   )) AS days_since_prev_order,

  SUM(f.order_total) OVER (
    PARTITION BY f.customer_id
    ORDER BY f.order_date, f.order_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )::numeric(18,2) AS customer_running_spend

FROM fact_order f
ORDER BY f.order_date DESC, f.order_id DESC;
```
