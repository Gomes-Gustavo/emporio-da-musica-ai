"""The data audit findings (notebooks/01_data_audit.ipynb) as checks the loader must keep true."""

from datetime import date

import pytest

from emporio.data import load_store


@pytest.fixture(scope="module")
def store():
    return load_store()


def test_loads_every_row_of_every_table(store):
    assert len(store.categories) == 9
    assert len(store.customers) == 50
    assert len(store.products) == 65
    assert len(store.promotions) == 25
    assert len(store.orders) == 20
    assert sum(len(order.items) for order in store.orders.values()) == 22


def test_values_are_typed_not_raw_strings(store):
    product = store.products[95]
    assert product.name == "Takamine GD20 Dreadnought Natural"
    assert product.price_brl == 2199.0
    assert product.stock_quantity == 5
    assert isinstance(product.specs, dict)  # specs is a JSON column, kept as a dictionary
    assert store.orders[1].order_date == date(2025, 10, 15)
    assert store.orders[1].estimated_delivery == date(2025, 10, 25)


def test_every_reference_resolves(store):
    assert all(p.category_id in store.categories for p in store.products.values())
    assert all(p.product_id in store.products for p in store.promotions)
    assert all(o.customer_id in store.customers for o in store.orders.values())
    assert all(i.product_id in store.products for o in store.orders.values() for i in o.items)


def test_tracking_and_delivery_exist_only_for_shipped_and_delivered_orders(store):
    for order in store.orders.values():
        shipped = order.status in ("shipped", "delivered")
        assert (order.tracking_code is not None) == shipped
        assert (order.estimated_delivery is not None) == shipped


def test_notes_exist_only_for_cancelled_orders(store):
    for order in store.orders.values():
        assert (order.notes is not None) == (order.status == "cancelled")


def test_only_four_promotions_are_active_and_the_takamine_one_is_not(store):
    active = {p.product_id for p in store.promotions if p.is_active}
    assert active == {90, 94, 121, 127}
    assert 95 not in active
