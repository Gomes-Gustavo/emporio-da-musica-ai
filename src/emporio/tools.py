"""Tools the agent can call. They return plain dicts, so the model reads exactly what the store system says."""

import unicodedata

from emporio.data import Product, Promotion, Store, load_store

PIX_DISCOUNT_PERCENT = 5
MAX_RESULTS = 10
MAX_ALTERNATIVES = 3
STATUS_LABELS = {"discontinued": "descontinuado", "coming_soon": "em breve"}


def _norm(text: str) -> str:
    """Lowercase and strip accents, so 'Aço' matches 'aco'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _is_available(product: Product) -> bool:
    return product.status == "active" and product.stock_quantity > 0


def _availability(product: Product) -> str:
    if product.status != "active":
        return STATUS_LABELS.get(product.status, product.status)
    return "disponível" if product.stock_quantity > 0 else "esgotado"


def _promotions(store: Store, product: Product, active: bool) -> list[Promotion]:
    return [p for p in store.promotions if p.product_id == product.product_id and p.is_active == active]


def _pricing(store: Store, product: Product) -> dict:
    """Original price, discount and final price, always together (manual 6.2)."""
    # the audit found no product with two active promotions, so the first one is the only one
    promotion = next(iter(_promotions(store, product, active=True)), None)
    final = product.price_brl
    if promotion:
        final = round(product.price_brl * (1 - promotion.discount_percent / 100), 2)
    return {
        "list_price_brl": product.price_brl,
        "promotion": (
            {"description": promotion.description, "discount_percent": promotion.discount_percent}
            if promotion
            else None
        ),
        "final_price_brl": final,
        # promotions do not stack: the PIX discount applies to the list price only
        "pix_price_brl": None if promotion else round(product.price_brl * (1 - PIX_DISCOUNT_PERCENT / 100), 2),
    }


def _summary(store: Store, product: Product) -> dict:
    return {
        "product_id": product.product_id,
        "name": product.name,
        "category": store.categories[product.category_id].name,
        "availability": _availability(product),
        "price": _pricing(store, product),
    }


def _detail(store: Store, product: Product) -> dict:
    detail = _summary(store, product) | {
        "description": product.description,
        "specs": product.specs,
        "stock_quantity": product.stock_quantity,
        "ended_promotions": [
            {"description": p.description, "discount_percent": p.discount_percent}
            for p in _promotions(store, product, active=False)
        ],
    }
    if not _is_available(product):
        target = _pricing(store, product)["final_price_brl"]
        similar = sorted(
            (p for p in store.products.values() if p.category_id == product.category_id and _is_available(p)),
            key=lambda p: abs(_pricing(store, p)["final_price_brl"] - target),
        )
        detail["alternatives"] = [_summary(store, p) for p in similar[:MAX_ALTERNATIVES]]
    return detail


def _matches(store: Store, product: Product, query: str) -> bool:
    """Every word of the query must appear in the product's name, description or category."""
    text = _norm(f"{product.name} {product.description} {store.categories[product.category_id].name}")
    return all(word in text for word in _norm(query).split())


def search_products(
    query: str = "", category: str = "", max_price: float | None = None, in_stock_only: bool = True
) -> dict:
    """Search the catalog. Use it for options, prices and availability: never state them without calling it.

    Args:
        query: Words from the brand, model or description, e.g. "yamaha nylon". Empty matches everything.
        category: Category name, e.g. "Violões", "Guitarras", "Baixos", "Ukuleles". Empty means all categories.
        max_price: Highest price the customer will pay, in BRL. It is compared with the promotional price.
        in_stock_only: When true (default) only products that can be bought now are listed.

    Returns:
        total_matches and up to 10 products, cheapest first. Each has its availability and price details.
    """
    store = load_store()
    category_ids = None
    if category:
        category_ids = {c.category_id for c in store.categories.values() if _norm(category) in _norm(c.name)}
        if not category_ids:
            return {"error": "unknown category", "valid_categories": [c.name for c in store.categories.values()]}

    found = [
        (product, _summary(store, product))
        for product in store.products.values()
        if (category_ids is None or product.category_id in category_ids)
        and _matches(store, product, query)
        and (not in_stock_only or _is_available(product))
    ]
    results = sorted(
        (summary for _, summary in found if max_price is None or summary["price"]["final_price_brl"] <= max_price),
        key=lambda summary: summary["price"]["final_price_brl"],
    )
    return {"total_matches": len(results), "products": results[:MAX_RESULTS]}


def get_product(name_or_id: str) -> dict:
    """Get one product with its price, promotion, specs and availability.

    Use it for a specific instrument ("Quanto custa o Takamine GD20?"). If the product is not available,
    the result lists similar available products as alternatives.

    Args:
        name_or_id: The product id (digits only) or words from its name, e.g. "takamine gd20".
    """
    store = load_store()
    key = name_or_id.strip()
    if key.isdigit():
        product = store.products.get(int(key))
        return _detail(store, product) if product else {"error": "product not found"}

    found = [p for p in store.products.values() if _matches(store, p, key)]
    if not found:
        return {"error": "product not found"}
    if len(found) > 1:
        return {"error": "ambiguous name", "matches": [_summary(store, p) for p in found[:MAX_RESULTS]]}
    return _detail(store, found[0])
