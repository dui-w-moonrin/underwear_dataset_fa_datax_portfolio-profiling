WITH
/* 1) base_orders: WHERE ก่อนให้เล็ก + เป็นเหตุผลจริง (data quality / business rules)
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
    AND o.is_orderdate_gt_shipdate = FALSE         -- ตัดเคสเวลาเพี้ยน
    AND o.ship_lead_days BETWEEN 0 AND 30          -- ตัด lead time ผิดปกติ (ปรับได้)
    AND COALESCE(o.freight_charge, 0) >= 0         -- ตัดค่าขนส่งติดลบ
),

/* 2) customers: ลดก่อน (active only + คอลัมน์ที่ใช้จริง)
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
  WHERE COALESCE(c.discontinued, 0) = 0            -- ตัดลูกค้าที่เลิกใช้แล้ว
),

/* 3) orders_filtered: คุม business scope เพิ่มอีกชั้น (join แบบเล็กกับเล็ก)
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
    ON c.customer_id = bo.customer_id              -- ตัด order ของลูกค้าที่ discontinued ไปแล้ว
),

/* 4) od_agg: ลด order_details (ตารางใหญ่) ด้วย aggregation ก่อน JOIN
      grain: 1 row / order_id */
od_agg AS (
  SELECT
    od.order_id,
    COUNT(*) AS line_count,
    SUM(od.quantity_sold)::numeric AS item_qty,
    SUM(od.quantity_sold * od.unit_sales_price)::numeric(18,2) AS gross_sales
  FROM clean.order_details od
  JOIN o
    ON o.order_id = od.order_id                    -- semi-join: ดึงเฉพาะ order ที่ผ่าน filter แล้ว
  GROUP BY od.order_id
),

/* 5) p_agg: ลด payments ให้เหลือ 1 row / order_id ก่อน JOIN
      หมายเหตุ: ถ้า payment_amount เป็น numeric แล้ว SUM ได้เลย
      ถ้ายังเป็น text ให้ใช้สูตร cast แบบปลอดภัย (comment ไว้ให้)
*/
p_agg AS (
  SELECT
    p.order_id,
    COUNT(*) AS payment_cnt,
    SUM(p.payment_amount)::numeric(18,2) AS paid_amount

    -- ถ้ายังเป็น text ใช้อันนี้แทนได้:
    -- SUM(
    --   COALESCE(
    --     NULLIF(regexp_replace(p.payment_amount::text, '[^0-9\.\-]', '', 'g'), '')::numeric,
    --     0
    --   )
    -- )::numeric(18,2) AS paid_amount

  FROM clean.payments p
  JOIN o
    ON o.order_id = p.order_id                     -- semi-join
  GROUP BY p.order_id
),

/* 6) fact_order: ประกอบเป็น order-level fact (grain = 1 row / order_id) */
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

SELECT
  f.*,

  /* windows: ใช้เฉพาะ order-level fact แล้ว (ไม่บวม) */
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
