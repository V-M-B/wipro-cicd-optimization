from __future__ import annotations

import pytest

from app.io import csv_io


def test_validate_orders_ok(client, tiny_orders):
    body = client.post("/csv/orders/validate", json={"content": csv_io.write_orders(tiny_orders)}).json()
    assert body == {"valid": True, "count": 8, "errors": []}


def test_validate_customers_ok(client, tiny_customers):
    body = client.post("/csv/customers/validate", json={"content": csv_io.write_customers(tiny_customers)}).json()
    assert body == {"valid": True, "count": 4, "errors": []}


def test_validate_products_ok(client, tiny_products):
    body = client.post("/csv/products/validate", json={"content": csv_io.write_products(tiny_products)}).json()
    assert body["count"] == 5


@pytest.mark.parametrize(
    ("endpoint", "content", "field"),
    [
        ("/csv/customers/validate", "id,name,email,tier,region\nC1,A,bad,GOLD,NORTH\n", "email"),
        ("/csv/products/validate", "id,sku,name,category,unit_price,active\nP1,S1,L,HOME,-2,true\n", "unit_price"),
        (
            "/csv/orders/validate",
            "order_id,customer_id,status,created_at,coupon_code,total,sku,quantity,unit_price\n"
            "O1,C1,PAID,2025-01-01,,10,A,0,10\n",
            "quantity",
        ),
    ],
)
def test_validate_reports_errors(client, endpoint, content, field):
    body = client.post(endpoint, json={"content": content}).json()
    assert body["valid"] is False
    assert body["errors"] == [{"line": 2, "field": field, "message": body["errors"][0]["message"]}]


def test_validate_missing_columns(client):
    body = client.post("/csv/orders/validate", json={"content": "order_id\nO1\n"}).json()
    assert body["valid"] is False
    assert body["errors"][0]["field"] is None
