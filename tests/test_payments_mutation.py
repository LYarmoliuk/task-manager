"""Краш-тест: мутабельне замовлення ламається при повторній спробі оплати (FAIL-стан)."""
import pytest

from app.payments import PaymentError, charge_order

RATES = {"USD": 41.0}


class FakeGateway:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = []

    def charge(self, customer_id, token, amount, currency):
        self.calls.append((customer_id, token, amount, currency))
        return {"status": self.statuses.pop(0)}


def make_order():
    return {"amount": 100, "currency": "USD", "discount_pct": 10, "tax_pct": 20, "shipping": 50}


def test_retry_after_decline_charges_same_amount():
    gateway = FakeGateway(["declined", "ok"])
    order = make_order()
    with pytest.raises(PaymentError):
        charge_order(gateway, order, "cust-1", "tkn-1", RATES)
    charge_order(gateway, order, "cust-1", "tkn-1", RATES)
    first, second = gateway.calls[0][2], gateway.calls[1][2]
    assert second == first, f"повторна спроба змінила суму списання: {first} -> {second}"


def test_charge_does_not_modify_callers_order():
    order = make_order()
    before = dict(order)
    charge_order(FakeGateway(["ok"]), order, "cust-1", "tkn-1", RATES)
    assert order == before, f"метод перезаписав вхідне замовлення: {before} -> {order}"
