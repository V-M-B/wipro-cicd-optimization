-- Reference data: 40 products (8 per category), stock for each, 12 customers, 7 coupons.
INSERT INTO products (id, sku, name, category, unit_price, active, created_at) VALUES
    ('prd-0001', 'ELE-1001', 'Wireless Mouse',            'ELECTRONICS',  24.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0002', 'ELE-1002', 'Mechanical Keyboard',       'ELECTRONICS',  89.50, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0003', 'ELE-1003', 'USB-C Charger 65W',         'ELECTRONICS',  39.00, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0004', 'ELE-1004', '27in Monitor',              'ELECTRONICS', 249.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0005', 'ELE-1005', 'Noise Cancelling Headset',  'ELECTRONICS', 159.95, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0006', 'ELE-1006', 'HDMI Cable 2m',             'ELECTRONICS',   7.49, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0007', 'ELE-1007', 'Webcam 1080p',              'ELECTRONICS',  54.25, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0008', 'ELE-1008', 'Portable SSD 1TB',          'ELECTRONICS', 119.00, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0009', 'GRO-2001', 'Basmati Rice 5kg',          'GROCERY',      12.75, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0010', 'GRO-2002', 'Olive Oil 1L',              'GROCERY',       9.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0011', 'GRO-2003', 'Ground Coffee 500g',        'GROCERY',       8.45, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0012', 'GRO-2004', 'Green Tea 100 bags',        'GROCERY',       4.20, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0013', 'GRO-2005', 'Dark Chocolate 200g',       'GROCERY',       3.15, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0014', 'GRO-2006', 'Almonds 1kg',               'GROCERY',      15.60, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0015', 'GRO-2007', 'Pasta 500g',                'GROCERY',       1.85, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0016', 'GRO-2008', 'Honey 500g',                'GROCERY',       6.30, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0017', 'APP-3001', 'Cotton T-Shirt',            'APPAREL',      14.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0018', 'APP-3002', 'Denim Jeans',               'APPAREL',      49.90, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0019', 'APP-3003', 'Rain Jacket',               'APPAREL',      79.00, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0020', 'APP-3004', 'Running Shoes',             'APPAREL',      95.50, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0021', 'APP-3005', 'Wool Socks 3-pack',         'APPAREL',      11.25, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0022', 'APP-3006', 'Baseball Cap',              'APPAREL',      17.80, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0023', 'APP-3007', 'Leather Belt',              'APPAREL',      29.95, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0024', 'APP-3008', 'Winter Gloves',             'APPAREL',      22.40, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0025', 'HOM-4001', 'Ceramic Mug',               'HOME',          6.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0026', 'HOM-4002', 'Bath Towel Set',            'HOME',         34.50, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0027', 'HOM-4003', 'Desk Lamp',                 'HOME',         27.75, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0028', 'HOM-4004', 'Non-stick Pan 28cm',        'HOME',         42.00, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0029', 'HOM-4005', 'Storage Box',               'HOME',          9.25, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0030', 'HOM-4006', 'Scented Candle',            'HOME',         12.10, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0031', 'HOM-4007', 'Cushion Cover',             'HOME',          8.80, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0032', 'HOM-4008', 'Wall Clock',                'HOME',         19.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0033', 'TOY-5001', 'Building Blocks 500pc',     'TOYS',         44.99, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0034', 'TOY-5002', 'Puzzle 1000pc',             'TOYS',         18.50, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0035', 'TOY-5003', 'Remote Control Car',        'TOYS',         64.00, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0036', 'TOY-5004', 'Plush Bear',                'TOYS',         15.75, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0037', 'TOY-5005', 'Board Game',                'TOYS',         32.25, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0038', 'TOY-5006', 'Kite',                      'TOYS',         12.95, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0039', 'TOY-5007', 'Art Set',                   'TOYS',         21.60, TRUE, '2025-01-01T00:00:00Z'),
    ('prd-0040', 'TOY-5008', 'Discontinued Yo-Yo',        'TOYS',          2.50, FALSE, '2025-01-01T00:00:00Z');

INSERT INTO stock_items (sku, on_hand, reserved)
SELECT sku,
       CASE
           WHEN sku = 'ELE-1008' THEN 0
           WHEN sku = 'TOY-5008' THEN 3
           ELSE 200 + (CAST(substring(sku FROM 5) AS INTEGER) % 7) * 50
       END,
       0
FROM products;

INSERT INTO customers (id, name, email, tier, region, created_at) VALUES
    ('cus-0001', 'Asha Rao',        'asha.rao@example.com',        'STANDARD', 'NORTH', '2025-01-02T00:00:00Z'),
    ('cus-0002', 'Ben Carter',      'ben.carter@example.com',      'SILVER',   'NORTH', '2025-01-02T00:00:00Z'),
    ('cus-0003', 'Chen Wei',        'chen.wei@example.com',        'GOLD',     'NORTH', '2025-01-02T00:00:00Z'),
    ('cus-0004', 'Divya Menon',     'divya.menon@example.com',     'PLATINUM', 'SOUTH', '2025-01-02T00:00:00Z'),
    ('cus-0005', 'Elena Rossi',     'elena.rossi@example.com',     'STANDARD', 'SOUTH', '2025-01-02T00:00:00Z'),
    ('cus-0006', 'Farhan Ali',      'farhan.ali@example.com',      'SILVER',   'SOUTH', '2025-01-02T00:00:00Z'),
    ('cus-0007', 'Grace Kim',       'grace.kim@example.com',       'GOLD',     'EAST',  '2025-01-02T00:00:00Z'),
    ('cus-0008', 'Hiro Tanaka',     'hiro.tanaka@example.com',     'PLATINUM', 'EAST',  '2025-01-02T00:00:00Z'),
    ('cus-0009', 'Isabel Gomez',    'isabel.gomez@example.com',    'STANDARD', 'EAST',  '2025-01-02T00:00:00Z'),
    ('cus-0010', 'Jonas Berg',      'jonas.berg@example.com',      'SILVER',   'WEST',  '2025-01-02T00:00:00Z'),
    ('cus-0011', 'Kavya Iyer',      'kavya.iyer@example.com',      'GOLD',     'WEST',  '2025-01-02T00:00:00Z'),
    ('cus-0012', 'Liam O''Neill',   'liam.oneill@example.com',     'STANDARD', 'WEST',  '2025-01-02T00:00:00Z');

INSERT INTO coupons (code, type, amount, min_spend, max_discount, valid_from, expires_on, active) VALUES
    ('WELCOME10', 'PERCENTAGE',    10.00, NULL,   50.00, NULL,         '2099-12-31', TRUE),
    ('SAVE5',     'FIXED_AMOUNT',   5.00, 25.00,  NULL,  NULL,         NULL,         TRUE),
    ('BIG20',     'PERCENTAGE',    20.00, 200.00, 100.00, NULL,        '2099-12-31', TRUE),
    ('FREESHIP',  'FREE_SHIPPING',  0.00, 30.00,  NULL,  NULL,         NULL,         TRUE),
    ('EXPIRED15', 'PERCENTAGE',    15.00, NULL,   NULL,  '2020-01-01', '2020-12-31', TRUE),
    ('FUTURE25',  'PERCENTAGE',    25.00, NULL,   NULL,  '2099-01-01', NULL,         TRUE),
    ('RETIRED5',  'FIXED_AMOUNT',   5.00, NULL,   NULL,  NULL,         NULL,         FALSE);
