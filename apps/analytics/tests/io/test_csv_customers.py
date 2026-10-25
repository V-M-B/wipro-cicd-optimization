from __future__ import annotations

import io

import pytest

from app.generated.schemas import CustomerTier, Region
from app.io import csv_io

HEADER = "id,name,email,tier,region\n"


def test_round_trip_tiny(tiny_customers):
    text = csv_io.write_customers(tiny_customers)
    assert text.splitlines()[0] == "id,name,email,tier,region"
    assert csv_io.read_customers(text) == tiny_customers


def test_round_trip_generated(small_dataset):
    assert csv_io.read_customers(csv_io.write_customers(small_dataset.customers)) == small_dataset.customers


def test_read_from_file_object():
    stream = io.StringIO(HEADER + "C1,Asha Rao,asha@example.com,gold,north\n")
    (customer,) = csv_io.read_customers(stream)
    assert customer.tier is CustomerTier.GOLD
    assert customer.region is Region.NORTH


def test_extra_columns_and_column_order_are_tolerated():
    text = "region,email,id,notes,tier,name\nWEST,a@b.com,C7,vip,SILVER,Ann\n"
    (customer,) = csv_io.read_customers(text)
    assert (customer.id, customer.name, customer.region) == ("C7", "Ann", Region.WEST)


def test_blank_lines_are_ignored():
    text = HEADER + "C1,A,a@b.com,STANDARD,EAST\n,,,,\n\nC2,B,b@b.com,STANDARD,EAST\n"
    assert [c.id for c in csv_io.read_customers(text)] == ["C1", "C2"]


def test_names_with_commas_are_quoted():
    customers = csv_io.read_customers(HEADER + 'C1,"Rao, Asha",a@b.com,GOLD,SOUTH\n')
    assert customers[0].name == "Rao, Asha"
    assert '"Rao, Asha"' in csv_io.write_customers(customers)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        (",A,a@b.com,GOLD,NORTH", "id"),
        ("C1,,a@b.com,GOLD,NORTH", "name"),
        ("C1,A,not-an-email,GOLD,NORTH", "email"),
        ("C1,A,a@b.com,DIAMOND,NORTH", "tier"),
        ("C1,A,a@b.com,GOLD,CENTRAL", "region"),
    ],
)
def test_invalid_field_reported_with_line(row, field):
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_customers(HEADER + row + "\n")
    (error,) = excinfo.value.errors
    assert (error.line, error.field) == (2, field)


def test_all_errors_are_collected():
    text = HEADER + "C1,A,bad,GOLD,NORTH\nC2,B,b@b.com,GOLD,MARS\nC1,C,c@b.com,GOLD,NORTH\n"
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_customers(text)
    assert [(e.line, e.field) for e in excinfo.value.errors] == [(2, "email"), (3, "region"), (4, "id")]
    assert "duplicate id 'C1'" in excinfo.value.errors[-1].message


def test_max_errors_caps_collection():
    rows = "".join(f"C{i},A,bad,GOLD,NORTH\n" for i in range(10))
    with pytest.raises(csv_io.CsvValidationError) as excinfo:
        csv_io.read_customers(HEADER + rows, max_errors=3)
    assert len(excinfo.value.errors) == 3


def test_missing_columns():
    with pytest.raises(csv_io.CsvValidationError, match="missing required column\\(s\\): tier, region"):
        csv_io.read_customers("id,name,email\nC1,A,a@b.com\n")


def test_empty_input():
    with pytest.raises(csv_io.CsvValidationError, match="missing header row"):
        csv_io.read_customers("")


def test_too_many_fields():
    with pytest.raises(csv_io.CsvValidationError, match="too many fields"):
        csv_io.read_customers(HEADER + "C1,A,a@b.com,GOLD,NORTH,extra\n")


def test_header_only_gives_empty_list():
    assert csv_io.read_customers(HEADER) == []
