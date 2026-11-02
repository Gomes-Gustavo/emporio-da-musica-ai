"""Tools the agent can call. They return plain dicts, so the model reads exactly what the store system says."""

import unicodedata
from datetime import date

from emporio.data import Order, Product, Promotion, Store, load_store

PIX_DISCOUNT_PERCENT = 5
MAX_RESULTS = 10
MAX_ALTERNATIVES = 3
STATUS_LABELS = {"discontinued": "descontinuado", "coming_soon": "em breve"}
ORDER_STATUS = {
    "pending": "pendente",
    "confirmed": "confirmado",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}
PAYMENT_METHODS = {
    "pix": "PIX",
    "debit": "cartão de débito",
    "boleto": "boleto",
    "credit_3x": "cartão de crédito em 3x",
    "credit_6x": "cartão de crédito em 6x",
    "credit_12x": "cartão de crédito em 12x",
}


def _today() -> date:
    return date.today()  # a function, so tests can fix the date


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


def _digits(text: str) -> str:
    return "".join(c for c in text if c.isdigit())


def _customers_matching(store: Store, contact: str) -> list:
    contact = contact.strip()
    if "@" in contact:
        return [c for c in store.customers.values() if c.email.lower() == contact.lower()]
    # the last 11 digits (area code + number) ignore formatting and a "+55" prefix
    phone = _digits(contact)[-11:]
    return [c for c in store.customers.values() if phone and _digits(c.phone)[-11:] == phone]


def _order_view(store: Store, order: Order, today: date) -> dict:
    return {
        "order_id": order.order_id,
        "order_date": order.order_date.isoformat(),
        "status": ORDER_STATUS.get(order.status, order.status),
        "total_brl": order.total_brl,
        "payment_method": PAYMENT_METHODS.get(order.payment_method, order.payment_method),
        "items": [{"product": store.products[i.product_id].name, "quantity": i.quantity} for i in order.items],
        "tracking_code": order.tracking_code,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        # days since the estimated delivery date: positive means the date has passed
        "days_since_estimated_delivery": (today - order.estimated_delivery).days if order.estimated_delivery else None,
        "notes": order.notes,
    }


def get_customer_orders(email_or_phone: str, order_id: int | None = None) -> dict:
    """Look up a customer's orders (status, tracking, delivery estimate, items, total).

    Use it for order status and for returns. The customer must give the e-mail or phone number of their
    registration, and only their own orders are returned. If the e-mail is shared by more than one customer,
    the result asks for the phone number.

    Args:
        email_or_phone: The customer's e-mail or phone number, in any common format.
        order_id: Only this order. Leave empty to list all the customer's orders, most recent first.

    Returns:
        The customer's name and their orders. days_since_estimated_delivery counts the days since the
        estimated delivery date; for a delivered order it is the time since the customer received it.
    """
    store = load_store()
    customers = _customers_matching(store, email_or_phone)
    if not customers:
        return {"error": "no customer found with this contact"}
    if len(customers) > 1:
        return {"error": "this e-mail belongs to more than one customer: ask for the phone number"}

    customer = customers[0]
    orders = sorted(
        (o for o in store.orders.values() if o.customer_id == customer.customer_id),
        key=lambda o: o.order_date,
        reverse=True,
    )
    if order_id is not None:
        orders = [o for o in orders if o.order_id == order_id]
        if not orders:
            # same answer for an order that does not exist and one that belongs to someone else
            return {"error": "order not found for this customer"}

    today = _today()
    return {"customer": {"name": customer.name}, "orders": [_order_view(store, o, today) for o in orders]}
