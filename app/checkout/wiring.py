"""Корінь композиції: єдине місце, де створюються конкретні об'єкти й складаються разом."""
from app.checkout.collaborators import (CheckoutAuditLog, FixedRateConverter, VolumeDiscountPolicy, ThresholdFraudChecker,
                                        TextInvoiceFormatter, SequentialInvoiceNumbering, OutboxMailer, CardPaymentGateway,
                                        TieredRetryPolicy, FlatShippingCalculator, OutboxSmsSender, WarehouseStockLedger,
                                        RegionTaxTable, RegionWarehouseRouter)
from app.checkout.domain import CheckoutOrder, CheckoutReceipt
from app.checkout.ports import AuditPort, BillingPort, FulfillmentPort, PaymentPort, PricingPort
from app.checkout.services import (BillingService, BroadcastNotifier, FulfillmentService,
                                   PaymentService, PricingService)


def process_order(order: CheckoutOrder, pricing: PricingPort, fulfillment: FulfillmentPort,
                  payment: PaymentPort, billing: BillingPort, audit: AuditPort) -> CheckoutReceipt:
    total = pricing.price(order)
    if not fulfillment.reserve(order):
        audit.record("out of stock " + order.order_id)
        return CheckoutReceipt(order.order_id, total, False, "", False)
    if not payment.charge(order, total):
        fulfillment.release(order)
        audit.record("payment failed " + order.order_id)
        return CheckoutReceipt(order.order_id, total, False, "", False)
    number = billing.issue(order, total, pricing.tax_part(order))
    return CheckoutReceipt(order.order_id, total, True, number, True)


def build_services():
    mailer, sms = OutboxMailer(), OutboxSmsSender()
    notifier = BroadcastNotifier(mailer, sms)
    return {
        "pricing": PricingService(RegionTaxTable(), VolumeDiscountPolicy(), FixedRateConverter()),
        "fulfillment": FulfillmentService(WarehouseStockLedger(), RegionWarehouseRouter(), FlatShippingCalculator()),
        "payment": PaymentService(CardPaymentGateway(), ThresholdFraudChecker(), TieredRetryPolicy()),
        "billing": BillingService(SequentialInvoiceNumbering(), TextInvoiceFormatter(), notifier),
        "audit": CheckoutAuditLog(),
        "mailer": mailer,
        "sms": sms,
    }
