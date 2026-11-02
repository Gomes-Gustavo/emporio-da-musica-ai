"""Load the store CSVs into typed records, applying the decisions of the data audit."""

import csv
import json
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path

# assumes a repository checkout (data/ sits two levels above this file);
# shipping the data inside the package is the upgrade path if this is ever installed.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Category:
    category_id: int
    name: str
    description: str


@dataclass(frozen=True)
class Customer:
    customer_id: int
    name: str
    phone: str
    email: str
    city: str


@dataclass(frozen=True)
class Product:
    product_id: int
    name: str
    category_id: int
    description: str
    price_brl: float
    stock_quantity: int
    status: str
    specs: dict  # kept as a dictionary: its keys depend on the product category
    created_at: date


@dataclass(frozen=True)
class Promotion:
    promotion_id: int
    product_id: int
    discount_percent: int
    description: str
    is_active: bool


@dataclass(frozen=True)
class OrderItem:
    product_id: int
    quantity: int


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: int
    order_date: date
    status: str
    total_brl: float  # the recorded total: never recomputed from current prices
    payment_method: str
    tracking_code: str | None  # None means "not shipped yet", not "unknown"
    estimated_delivery: date | None
    notes: str | None  # only cancelled orders carry one: the reason
    items: tuple[OrderItem, ...]


@dataclass(frozen=True)
class Store:
    categories: dict[int, Category]
    customers: dict[int, Customer]
    products: dict[int, Product]
    promotions: tuple[Promotion, ...]
    orders: dict[int, Order]


def _read(table: str) -> list[dict[str, str]]:
    path = DATA_DIR / f"desafio_tecnico_ai_eng - {table}.csv"
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _optional(value: str) -> str | None:
    return value or None


def _optional_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


@cache
def load_store() -> Store:
    items: dict[int, list[OrderItem]] = {}
    for row in _read("order_items"):
        items.setdefault(int(row["order_id"]), []).append(
            OrderItem(product_id=int(row["product_id"]), quantity=int(row["quantity"]))
        )

    return Store(
        categories={
            int(r["category_id"]): Category(int(r["category_id"]), r["name"], r["description"])
            for r in _read("categories")
        },
        customers={
            int(r["customer_id"]): Customer(int(r["customer_id"]), r["name"], r["phone"], r["email"], r["city"])
            for r in _read("customers")
        },
        products={
            int(r["product_id"]): Product(
                product_id=int(r["product_id"]),
                name=r["name"],
                category_id=int(r["category_id"]),
                description=r["description"],
                price_brl=float(r["price_brl"]),
                stock_quantity=int(r["stock_quantity"]),
                status=r["status"],
                specs=json.loads(r["specs"]),
                created_at=date.fromisoformat(r["created_at"]),
            )
            for r in _read("products")
        },
        promotions=tuple(
            Promotion(
                promotion_id=int(r["promotion_id"]),
                product_id=int(r["product_id"]),
                discount_percent=int(r["discount_percent"]),
                description=r["description"],
                is_active=r["is_active"] == "1",
            )
            for r in _read("promotions")
        ),
        orders={
            int(r["order_id"]): Order(
                order_id=int(r["order_id"]),
                customer_id=int(r["customer_id"]),
                order_date=date.fromisoformat(r["order_date"]),
                status=r["status"],
                total_brl=float(r["total_brl"]),
                payment_method=r["payment_method"],
                tracking_code=_optional(r["tracking_code"]),
                estimated_delivery=_optional_date(r["estimated_delivery"]),
                notes=_optional(r["notes"]),
                items=tuple(items[int(r["order_id"])]),
            )
            for r in _read("orders")
        },
    )
