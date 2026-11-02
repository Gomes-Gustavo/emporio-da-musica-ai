"""Order lookup: a customer only sees their own orders, and day counts come from code."""

from datetime import date

import pytest

from emporio.data import load_store
from emporio.tools import get_customer_orders

CUSTOMERS = load_store().customers
BRUNO_WITH_ORDER, BRUNO_WITHOUT_ORDER = 11, 43  # share one e-mail


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr("emporio.tools._today", lambda: date(2026, 3, 22))


def test_delivered_order_shows_status_tracking_and_days_since_delivery():
    result = get_customer_orders(CUSTOMERS[3].email, order_id=1)

    assert result["customer"] == {"name": "Pedro Henrique Oliveira"}
    assert result["orders"] == [
        {
            "order_id": 1,
            "order_date": "2025-10-15",
            "status": "entregue",
            "total_brl": 11499.0,
            "payment_method": "PIX",
            "items": [{"product": "Martin D-28 Dreadnought Natural", "quantity": 1}],
            "tracking_code": "BRAB1234567BR",
            "estimated_delivery": "2025-10-25",
            "days_since_estimated_delivery": 148,  # computed in code against the frozen date
            "notes": None,
        }
    ]


def test_customer_sees_all_their_orders_most_recent_first():
    orders = get_customer_orders(CUSTOMERS[3].email)["orders"]

    assert [o["order_id"] for o in orders] == [19, 1]


def test_shipped_order_past_its_estimate_has_positive_days():
    order = get_customer_orders(CUSTOMERS[2].email, order_id=8)["orders"][0]

    assert order["status"] == "enviado"
    assert order["days_since_estimated_delivery"] == 22  # estimated 2026-02-28


def test_order_not_shipped_has_no_tracking_or_delivery_estimate():
    order = get_customer_orders(CUSTOMERS[8].email, order_id=13)["orders"][0]

    assert order["status"] == "pendente"
    assert order["tracking_code"] is None
    assert order["estimated_delivery"] is None
    assert order["days_since_estimated_delivery"] is None


def test_cancelled_order_carries_the_reason():
    order = get_customer_orders(CUSTOMERS[17].email, order_id=18)["orders"][0]

    assert order["status"] == "cancelado"
    assert order["notes"] == "Item fora de estoque no momento do pedido"


def test_total_is_the_recorded_one_not_recomputed_from_current_prices():
    order = get_customer_orders(CUSTOMERS[12].email, order_id=3)["orders"][0]

    assert order["total_brl"] == 3450.0  # the items cost 3498.00 at today's prices


@pytest.mark.parametrize("contact", ["(67) 98432-1098", "67984321098", "+55 67 98432-1098"])
def test_phone_is_accepted_in_common_formats(contact):
    assert get_customer_orders(contact)["customer"] == {"name": "Pedro Henrique Oliveira"}


def test_email_ignores_case_and_surrounding_spaces():
    assert get_customer_orders("  PEDRO.OLIVEIRA@JMAIL.COM ")["customer"] == {"name": "Pedro Henrique Oliveira"}


def test_unknown_contact_gets_an_error_and_no_data():
    for contact in ["ninguem@jmail.com", "(67) 90000-0000", "98432-1098", ""]:
        assert get_customer_orders(contact) == {"error": "no customer found with this contact"}


def test_order_of_another_customer_is_not_revealed():
    # order 2 exists, but belongs to someone else: same answer as an order that does not exist
    other = get_customer_orders(CUSTOMERS[3].email, order_id=2)
    missing = get_customer_orders(CUSTOMERS[3].email, order_id=9999)

    assert other == missing == {"error": "order not found for this customer"}


def test_shared_email_asks_for_the_phone_number():
    result = get_customer_orders(CUSTOMERS[BRUNO_WITH_ORDER].email)

    assert "phone number" in result["error"]
    assert "orders" not in result


def test_phone_tells_apart_customers_who_share_an_email():
    with_order = get_customer_orders(CUSTOMERS[BRUNO_WITH_ORDER].phone)
    without_order = get_customer_orders(CUSTOMERS[BRUNO_WITHOUT_ORDER].phone)

    assert [o["order_id"] for o in with_order["orders"]] == [10]
    assert without_order["orders"] == []


def test_only_the_customer_name_is_returned_about_the_customer():
    result = get_customer_orders(CUSTOMERS[3].email)

    assert set(result["customer"]) == {"name"}
