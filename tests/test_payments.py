import pytest

from app.payments import BASE_CURRENCY, Order, PaymentError, charge_order

RATES = {"USD": 41.0, "EUR": 45.5}


class FakeGateway:
    def __init__(self, statuses=("ok",)):
        self.statuses = list(statuses)
        self.calls = []

    def charge(self, customer_id, token, amount, currency):
        self.calls.append((customer_id, token, amount, currency))
        return {"status": self.statuses.pop(0)}


def make_order(amount, currency="UAH", discount_pct=0, tax_pct=0, shipping=0):
    return Order(amount, currency, discount_pct, tax_pct, shipping)


@pytest.mark.parametrize(
    "amount, currency, discount, tax, shipping, expected",
    [
        (1000, "UAH", 0, 0, 0, 1000.0),
        (1000, "UAH", 10, 20, 50, 1130.0),
        (100, "USD", 10, 20, 50, 4478.0),
        (250, "EUR", 0, 7, 0.5, 12171.75),
        (99.99, "USD", 25, 20, 12.34, 3701.97),
        (0, "UAH", 0, 0, 0, 0.0),
    ],
)
def test_amount_to_charge(amount, currency, discount, tax, shipping, expected):
    gateway = FakeGateway()
    charge_order(gateway, make_order(amount, currency, discount, tax, shipping), "cust-1", "tkn-1", RATES)
    assert gateway.calls[0][2] == expected


def test_gateway_gets_customer_token_and_base_currency():
    gateway = FakeGateway()
    charge_order(gateway, make_order(10), "cust-7", "tkn-9", RATES)
    assert gateway.calls[0][0] == "cust-7"
    assert gateway.calls[0][1] == "tkn-9"
    assert gateway.calls[0][3] == BASE_CURRENCY


def test_declined_payment_raises():
    with pytest.raises(PaymentError, match="declined"):
        charge_order(FakeGateway(["declined"]), make_order(10), "cust-1", "tkn-1", RATES)


def test_unknown_currency_raises_key_error():
    with pytest.raises(KeyError):
        charge_order(FakeGateway(), make_order(10, "GBP"), "cust-1", "tkn-1", RATES)
