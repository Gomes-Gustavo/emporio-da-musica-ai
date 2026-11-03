"""Catalog tools: prices, promotions and availability as the store manual requires."""

import pytest

from emporio.data import load_store
from emporio.tools import _installments, get_product, search_products


def test_price_without_active_promotion_offers_the_pix_discount():
    takamine = get_product("Takamine GD20")

    assert takamine["name"] == "Takamine GD20 Dreadnought Natural"
    assert takamine["price"] == {
        "list_price_brl": 2199.0,
        "promotion": None,
        "final_price_brl": 2199.0,
        "pix_price_brl": 2089.05,  # 5% off the list price
        "credit_card_installments": {"max_installments": 12, "installment_brl": 183.25},
    }
    # the 12% offer ended: the agent must say so, not apply it
    assert takamine["ended_promotions"] == [{"description": "Oferta Especial", "discount_percent": 12}]


def test_active_promotion_lowers_the_price_and_removes_the_pix_discount():
    crafter = get_product("90")

    assert crafter["price"] == {
        "list_price_brl": 2399.0,
        "promotion": {"description": "Desconto Exclusivo", "discount_percent": 18},
        "final_price_brl": 1967.18,
        "pix_price_brl": None,  # promotions do not stack (manual 6.2)
        "credit_card_installments": {"max_installments": 12, "installment_brl": 163.93},
    }


def test_installments_follow_the_promotional_price():
    # Kalani KAL-700T: 359.00 with 10% off = 323.10. 4x is 80.775 (>= 80), 5x is 64.62 (< 80).
    # The model used to answer "up to 10x" here; the manual's section 3.1 allows 4x.
    assert get_product("127")["price"]["credit_card_installments"] == {
        "max_installments": 4,
        "installment_brl": 80.78,
    }


@pytest.mark.parametrize(
    "price, installments, installment",
    [
        (49.99, 1, 49.99),  # no installment may be under R$ 50
        (100.00, 2, 50.00),
        (149.99, 2, 75.00),  # 3x would be 49.997
        (150.00, 3, 50.00),
        (319.99, 3, 106.66),  # 4x would be 79.9975, under the R$ 80 of the 4x-6x range
        (320.00, 4, 80.00),
        (400.00, 5, 80.00),
        (480.00, 6, 80.00),
        (699.99, 6, 116.67),  # 7x would be 99.9986, under the R$ 100 of the 7x-12x range
        (700.00, 7, 100.00),
        (1199.99, 11, 109.09),  # 12x would be 99.9992
        (1200.00, 12, 100.00),
        (11499.00, 12, 958.25),
    ],
)
def test_installment_minimums_by_range(price, installments, installment):
    # manual 3.1: up to 3x from R$ 50 per installment, 4x to 6x from R$ 80, 7x to 12x from R$ 100
    assert _installments(price) == {"max_installments": installments, "installment_brl": installment}


def test_half_a_cent_rounds_up():
    # 429.90 * 0.95 = 408.405: float round() gives 408.40, a shopper expects 408.41
    assert get_product("tagima memphis")["price"]["pix_price_brl"] == 408.41


def test_every_discount_in_the_catalog_rounds_half_up_to_the_cent():
    # the oracle is integer arithmetic on cents, so it shares no code (and no float) with the tool
    checked = 0
    for product in load_store().products.values():
        price = get_product(str(product.product_id))["price"]
        cents = round(price["list_price_brl"] * 100)
        if price["promotion"]:
            expected = (cents * (100 - price["promotion"]["discount_percent"]) + 50) // 100
            assert round(price["final_price_brl"] * 100) == expected, product.name
        else:
            assert round(price["pix_price_brl"] * 100) == (cents * 95 + 50) // 100, product.name
        checked += 1
    assert checked == 65


@pytest.mark.parametrize(
    "product_id, availability",
    [
        (81, "disponível"),
        (96, "esgotado"),  # active, zero stock
        (113, "descontinuado"),
        (130, "em breve"),  # coming soon, yet it has stock
        (136, "descontinuado"),  # discontinued, yet it has stock: status wins
    ],
)
def test_availability_follows_status_then_stock(product_id, availability):
    assert get_product(str(product_id))["availability"] == availability


def test_unavailable_product_comes_with_available_alternatives_from_its_category():
    store = load_store()

    alternatives = get_product("96")["alternatives"]

    assert 1 <= len(alternatives) <= 3
    for alternative in alternatives:
        assert alternative["availability"] == "disponível"
        assert store.products[alternative["product_id"]].category_id == store.products[96].category_id


def test_available_product_has_no_alternatives():
    assert "alternatives" not in get_product("81")


def test_guitars_up_to_1000_lists_only_available_options_cheapest_first():
    result = search_products(category="Violões", max_price=1000)

    prices = [p["price"]["final_price_brl"] for p in result["products"]]
    assert result["total_matches"] == 12  # 14 under R$ 1000, minus one sold out and one discontinued
    assert len(prices) == 10  # the list is capped, the total says how many exist
    assert prices == sorted(prices)
    assert max(prices) <= 1000
    assert {p["availability"] for p in result["products"]} == {"disponível"}


def test_max_price_applies_to_the_promotional_price():
    names = [p["name"] for p in search_products(category="Ukuleles", max_price=440)["products"]]

    assert "Ohana CK-20 Concert Natural" in names  # listed at 549, 439.20 with 20% off


def test_in_stock_only_false_includes_unavailable_products():
    result = search_products(category="Violões", max_price=1000, in_stock_only=False)

    assert result["total_matches"] == 14


def test_query_ignores_case_and_accents():
    result = search_products(query="AÇO crafter")

    assert [p["name"] for p in result["products"]] == ["Crafter HT-100 Folk Aço Natural"]


def test_unknown_category_returns_the_valid_ones():
    result = search_products(category="saxofones")

    assert result["error"] == "unknown category"
    assert "Violões" in result["valid_categories"]


def test_category_without_products_returns_no_matches():
    assert search_products(category="Cordas Orquestrais") == {"total_matches": 0, "products": []}


def test_product_is_found_by_id_or_by_words_of_its_name():
    assert get_product("95")["name"] == get_product("takamine gd20")["name"]


def test_unknown_product_is_reported_not_guessed():
    assert get_product("Stradivarius") == {"error": "product not found"}
    assert get_product("9999") == {"error": "product not found"}


def test_ambiguous_name_lists_the_candidates():
    result = get_product("Yamaha")

    assert result["error"] == "ambiguous name"
    assert len(result["matches"]) >= 2


def test_each_product_has_at_most_one_active_promotion():
    # the tools take the first active promotion; this guards that assumption
    active = [p.product_id for p in load_store().promotions if p.is_active]

    assert len(active) == len(set(active))
