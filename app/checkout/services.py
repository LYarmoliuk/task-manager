"""Чотири сервіси з однією відповідальністю. Залежності приходять через конструктор (DI)."""
from app.checkout.domain import CheckoutOrder
from app.checkout.ports import (DiscountSource, FormatterPort, FraudPort, GatewayPort, MessagePort,
                                NotifierPort, NumberingPort, CurrencyPort, RetryPort, RouterPort,
                                ShippingPort, StockPort, TaxPolicy)


class PricingService:
    """Відповідає лише за ціну: конвертація, знижка, податок."""

    def __init__(self, tax: TaxPolicy, discount: DiscountSource, converter: CurrencyPort):
        self._tax = tax
        self._discount = discount
        self._converter = converter

    def price(self, order: CheckoutOrder) -> float:
        net = self._converter.to_base(order.amount, order.currency)
        net -= net * self._discount.percent_for(net) / 100
        return round(net * (1 + self._tax.rate_for(order.region, order.category)), 2)

    def estimate(self, order: CheckoutOrder) -> float:
        net = self._converter.to_base(order.amount, order.currency)
        net -= net * self._discount.percent_for(net) / 100
        return round(net * (1 + self._tax.rate_for(order.region, order.category)), 0)

    def tax_part(self, order: CheckoutOrder) -> float:
        net = self._converter.to_base(order.amount, order.currency)
        net -= net * self._discount.percent_for(net) / 100
        return round(net * self._tax.rate_for(order.region, order.category), 2)


class FulfillmentService:
    """Відповідає лише за склад і доставку."""

    def __init__(self, stock: StockPort, router: RouterPort, shipping: ShippingPort):
        self._stock = stock
        self._router = router
        self._shipping = shipping

    def reserve(self, order: CheckoutOrder) -> bool:
        self._router.pick(order.region)
        if self._shipping.cost(order.region, order.quantity) <= 0:
            return False
        return self._stock.reserve(order.sku, order.quantity)

    def release(self, order: CheckoutOrder) -> float:
        self._router.pick(order.region)
        self._stock.release(order.sku, order.quantity)
        return self._shipping.cost(order.region, order.quantity)


class PaymentService:
    """Відповідає лише за списання коштів і повернення."""

    def __init__(self, gateway: GatewayPort, fraud: FraudPort, retry: RetryPort):
        self._gateway = gateway
        self._fraud = fraud
        self._retry = retry

    def charge(self, order: CheckoutOrder, total: float) -> bool:
        if self._fraud.is_suspicious(order.customer, total):
            return False
        for _ in range(self._retry.attempts_for(total)):
            if self._gateway.charge(order.customer, total)["status"] == "ok":
                return True
        return False

    def refund(self, order: CheckoutOrder, total: float) -> bool:
        if self._fraud.is_suspicious(order.customer, total):
            return False
        for _ in range(self._retry.attempts_for(total)):
            if self._gateway.charge(order.customer, -total)["status"] == "ok":
                return True
        return False


class BroadcastNotifier:
    """Адаптер: розсилає одне повідомлення поштою і SMS."""

    def __init__(self, mailer: MessagePort, sms: MessagePort):
        self._mailer = mailer
        self._sms = sms

    def send(self, order: CheckoutOrder, text: str) -> bool:
        sent_mail = self._mailer.send(order.email, text)
        return self._sms.send(order.customer, text) and sent_mail


class BillingService:
    """Відповідає лише за рахунки та кредит-ноти."""

    def __init__(self, numbering: NumberingPort, formatter: FormatterPort, notifier: NotifierPort):
        self._numbering = numbering
        self._formatter = formatter
        self._notifier = notifier

    def issue(self, order: CheckoutOrder, total: float, tax: float) -> str:
        number = self._numbering.next_number()
        text = self._formatter.render(number, order.order_id, [f"TOTAL {total}", f"TAX {tax}"])
        self._notifier.send(order, text)
        return number

    def credit_note(self, order: CheckoutOrder, total: float, tax: float) -> str:
        number = self._numbering.next_number()
        text = self._formatter.render(number, order.order_id, [f"CREDIT {total}", f"TAX {tax}"])
        self._notifier.send(order, text)
        return number
