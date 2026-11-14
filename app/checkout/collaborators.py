"""Дрібні допоміжні класи: податки, склад, оплата, рахунки, сповіщення."""


class RegionTaxTable:
    RATES = {"UA": 0.2, "DE": 0.19, "US": 0.07}

    def rate_for(self, region, category):
        rate = self.RATES.get(region, 0.0)
        return rate / 2 if category == "books" else rate


class VolumeDiscountPolicy:
    def percent_for(self, amount):
        return 10 if amount >= 1000 else 0


class FixedRateConverter:
    RATES = {"UAH": 1.0, "USD": 41.0, "EUR": 45.0}

    def to_base(self, amount, currency):
        return amount * self.RATES[currency]


class WarehouseStockLedger:
    def __init__(self):
        self.stock = {"SKU-1": 10, "SKU-2": 1}

    def reserve(self, sku, quantity):
        if self.stock.get(sku, 0) < quantity:
            return False
        self.stock[sku] -= quantity
        return True

    def release(self, sku, quantity):
        self.stock[sku] = self.stock.get(sku, 0) + quantity


class RegionWarehouseRouter:
    def pick(self, region):
        return "WH-" + region


class FlatShippingCalculator:
    def cost(self, region, quantity):
        return 5 * quantity + (0 if region == "UA" else 20)


class CardPaymentGateway:
    def charge(self, customer, amount):
        return {"status": "declined" if amount > 100000 else "ok"}


class ThresholdFraudChecker:
    def is_suspicious(self, customer, amount):
        return amount > 50000


class TieredRetryPolicy:
    def attempts_for(self, amount):
        return 3 if amount < 10000 else 1


class SequentialInvoiceNumbering:
    def __init__(self):
        self.counter = 0

    def next_number(self):
        self.counter += 1
        return f"INV-{self.counter:04d}"


class TextInvoiceFormatter:
    def render(self, number, order_id, lines):
        return number + " / " + order_id + "\n" + "\n".join(lines)


class OutboxMailer:
    def __init__(self):
        self.outbox = []

    def send(self, address, text):
        self.outbox.append((address, text))
        return True


class OutboxSmsSender:
    def __init__(self):
        self.sent = []

    def send(self, address, text):
        self.sent.append((address, text))
        return True


class CheckoutAuditLog:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)
