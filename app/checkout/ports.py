"""Контракти (Protocol): сервіси залежать від них, а не від конкретних класів."""
from typing import Protocol

from app.checkout.domain import CheckoutOrder


class TaxPolicy(Protocol):
    def rate_for(self, region: str, category: str) -> float: ...


class DiscountSource(Protocol):
    def percent_for(self, amount: float) -> float: ...


class CurrencyPort(Protocol):
    def to_base(self, amount: float, currency: str) -> float: ...


class StockPort(Protocol):
    def reserve(self, sku: str, quantity: int) -> bool: ...

    def release(self, sku: str, quantity: int) -> None: ...


class RouterPort(Protocol):
    def pick(self, region: str) -> str: ...


class ShippingPort(Protocol):
    def cost(self, region: str, quantity: int) -> float: ...


class GatewayPort(Protocol):
    def charge(self, customer: str, amount: float) -> dict: ...


class FraudPort(Protocol):
    def is_suspicious(self, customer: str, amount: float) -> bool: ...


class RetryPort(Protocol):
    def attempts_for(self, amount: float) -> int: ...


class NumberingPort(Protocol):
    def next_number(self) -> str: ...


class FormatterPort(Protocol):
    def render(self, number: str, order_id: str, lines: list) -> str: ...


class MessagePort(Protocol):
    def send(self, address: str, text: str) -> bool: ...


class NotifierPort(Protocol):
    def send(self, order: CheckoutOrder, text: str) -> bool: ...


class AuditPort(Protocol):
    def record(self, event: str) -> None: ...


class PricingPort(Protocol):
    def price(self, order: CheckoutOrder) -> float: ...

    def tax_part(self, order: CheckoutOrder) -> float: ...


class FulfillmentPort(Protocol):
    def reserve(self, order: CheckoutOrder) -> bool: ...

    def release(self, order: CheckoutOrder) -> float: ...


class PaymentPort(Protocol):
    def charge(self, order: CheckoutOrder, total: float) -> bool: ...

    def refund(self, order: CheckoutOrder, total: float) -> bool: ...


class BillingPort(Protocol):
    def issue(self, order: CheckoutOrder, total: float, tax: float) -> str: ...

    def credit_note(self, order: CheckoutOrder, total: float, tax: float) -> str: ...
