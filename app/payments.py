"""Оплата замовлення через платіжний шлюз: незмінні Value Objects."""
from dataclasses import dataclass
from typing import Any, Mapping

BASE_CURRENCY = "UAH"


class PaymentError(Exception):
    """Шлюз відхилив платіж."""


@dataclass(frozen=True)
class Quote:
    """Підсумкова сума до списання (значення, не змінюється)."""

    amount: float
    currency: str


@dataclass(frozen=True)
class Order:
    """Замовлення: сума, валюта, знижка, податок і доставка в одному незмінному об'єкті."""

    amount: float
    currency: str
    discount_pct: float = 0
    tax_pct: float = 0
    shipping: float = 0

    def quote(self, rates: Mapping[str, float]) -> Quote:
        discounted = self.amount - self.amount * self.discount_pct / 100
        converted = discounted if self.currency == BASE_CURRENCY else discounted * rates[self.currency]
        tax = converted * self.tax_pct / 100
        return Quote(round(converted + tax + self.shipping, 2), BASE_CURRENCY)


def require_ok(response: Mapping[str, Any]) -> Mapping[str, Any]:
    status = response["status"]
    if status != "ok":
        raise PaymentError(status)
    return response


def charge_order(gateway, order, customer_id, token, rates):
    quote = order.quote(rates)
    response = gateway.charge(customer_id, token, quote.amount, quote.currency)
    return require_ok(response)
