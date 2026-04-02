
-- UNKNOWN placeholder product — used for rows where product code cannot be resolved
INSERT INTO raw_legacy.tbsstock (col_1, col_3, col_16, col_20, col_21, col_28, col_32, col_33)
VALUES (
    'UNKNOWN',          -- col_1: product_code
    '不明商品',           -- col_3: product_name (不明商品 = Unknown Product)
    'UNKNOWN',          -- col_16: unit
    0.00000000,         -- col_20: cost
    0.00000000,         -- col_21: price
    0.00000000,         -- col_28: min_stock
    '1900-01-01',       -- col_32: create_date
    '1900-01-01'        -- col_33: update_date
) ON CONFLICT (col_1) DO NOTHING;
