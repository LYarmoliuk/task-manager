"""Предметна область оформлення замовлення: прості незмінні об'єкти."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckoutOrder:
    order_id: str
    customer: str
    region: str
    category: str
    currency: str
    amount: float
    quantity: int
    sku: str
    email: str


@dataclass(frozen=True)
class CheckoutReceipt:
    order_id: str
    total: float
    paid: bool
    invoice_number: str
    notified: bool
