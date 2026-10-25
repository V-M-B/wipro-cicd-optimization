CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at DESC);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_order_lines_order ON order_lines (order_id);
CREATE INDEX idx_order_lines_sku ON order_lines (sku);
CREATE INDEX idx_products_category ON products (category);
