"""OrderProcessor: клас-моноліт (God Object). Ціна, склад, оплата, рахунки, сповіщення в одному місці."""
from app.checkout.collaborators import (CheckoutAuditLog, FixedRateConverter, VolumeDiscountPolicy, ThresholdFraudChecker,
                                        TextInvoiceFormatter, SequentialInvoiceNumbering, OutboxMailer, CardPaymentGateway,
                                        TieredRetryPolicy, FlatShippingCalculator, OutboxSmsSender, WarehouseStockLedger,
                                        RegionTaxTable, RegionWarehouseRouter)
from app.checkout.domain import CheckoutOrder, CheckoutReceipt


class OrderProcessor:
    def __init__(self):
        self.tax = RegionTaxTable()
        self.discount = VolumeDiscountPolicy()
        self.converter = FixedRateConverter()
        self.stock = WarehouseStockLedger()
        self.router = RegionWarehouseRouter()
        self.shipping = FlatShippingCalculator()
        self.gateway = CardPaymentGateway()
        self.fraud = ThresholdFraudChecker()
        self.retry = TieredRetryPolicy()
        self.numbering = SequentialInvoiceNumbering()
        self.formatter = TextInvoiceFormatter()
        self.mailer = OutboxMailer()
        self.sms = OutboxSmsSender()
        self.audit = CheckoutAuditLog()

    def price_order(self, order: CheckoutOrder):
        net = self.converter.to_base(order.amount, order.currency)
        net -= net * self.discount.percent_for(net) / 100
        return round(net * (1 + self.tax.rate_for(order.region)), 2)

    def estimate_total(self, order: CheckoutOrder):
        net = self.converter.to_base(order.amount, order.currency)
        tax = net * self.tax.rate_for(order.region)
        return round(net + tax + self.shipping.cost(order.region, order.quantity), 2)

    def reserve_stock(self, order: CheckoutOrder):
        self.router.pick(order.region)
        if self.shipping.cost(order.region, order.quantity) <= 0:
            return False
        return self.stock.reserve(order.sku, order.quantity)

    def release_stock(self, order: CheckoutOrder):
        self.router.pick(order.region)
        self.stock.release(order.sku, order.quantity)

    def shipping_cost(self, order: CheckoutOrder):
        return self.shipping.cost(order.region, order.quantity)

    def charge(self, order: CheckoutOrder, total):
        if self.fraud.is_suspicious(order.customer, total):
            return False
        for _ in range(self.retry.attempts_for(total)):
            if self.gateway.charge(order.customer, total)["status"] == "ok":
                return True
        return False

    def refund(self, order: CheckoutOrder, total):
        if self.fraud.is_suspicious(order.customer, total):
            return False
        for _ in range(self.retry.attempts_for(total)):
            if self.gateway.charge(order.customer, -total)["status"] == "ok":
                return True
        return False

    def issue_invoice(self, order: CheckoutOrder, total):
        number = self.numbering.next_number()
        tax_line = round(total - total / (1 + self.tax.rate_for(order.region)), 2)
        text = self.formatter.render(number, order.order_id, [f"TOTAL {total}", f"TAX {tax_line}"])
        self.audit.record(text)
        return number

    def credit_note(self, order: CheckoutOrder, total):
        number = self.numbering.next_number()
        self.audit.record(self.formatter.render(number, order.order_id, [f"CREDIT {total}"]))
        return number

    def notify(self, order: CheckoutOrder, text):
        sent_mail = self.mailer.send(order.email, text)
        return self.sms.send(order.customer, text) and sent_mail

    def record_audit(self, event):
        self.audit.record(event)

    def process(self, order: CheckoutOrder):
        total = self.price_order(order)
        if not self.reserve_stock(order):
            self.record_audit("out of stock " + order.order_id)
            return CheckoutReceipt(order.order_id, total, False, "", False)
        if not self.charge(order, total):
            self.release_stock(order)
            self.record_audit("payment failed " + order.order_id)
            return CheckoutReceipt(order.order_id, total, False, "", False)
        number = self.issue_invoice(order, total)
        notified = self.notify(order, "Invoice " + number)
        return CheckoutReceipt(order.order_id, total, True, number, notified)
