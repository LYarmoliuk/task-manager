"""Оплата замовлення через платіжний шлюз (базова версія з мутабельним станом)."""

BASE_CURRENCY = "UAH"


class PaymentError(Exception):
    """Шлюз відхилив платіж."""


def charge_order(gateway, order, customer_id, token, rates):
    base = order["amount"]
    if order["discount_pct"] > 0:
        base = base - base * order["discount_pct"] / 100
    if order["currency"] != BASE_CURRENCY:
        base = base * rates[order["currency"]]
    tax = base * order["tax_pct"] / 100
    order["amount"] = round(base + tax + order["shipping"], 2)
    response = gateway.charge(customer_id, token, order["amount"], BASE_CURRENCY)
    status = response["status"]
    if status != "ok":
        raise PaymentError(status)
    return response
