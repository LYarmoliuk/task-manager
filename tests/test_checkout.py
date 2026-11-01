from app.checkout.domain import CheckoutOrder, CheckoutReceipt
from app.checkout.god_order_processor import OrderProcessor


def make_order(**changes):
    values = dict(order_id="o-1", customer="c-1", region="UA", category="tools", currency="USD",
                  amount=100.0, quantity=2, sku="SKU-1", email="buyer@example.com")
    values.update(changes)
    return CheckoutOrder(**values)


def test_price_order_applies_discount_and_tax():
    assert OrderProcessor().price_order(make_order()) == 4428.0


def test_estimate_total_includes_shipping():
    assert OrderProcessor().estimate_total(make_order()) == 4930.0


def test_invoice_contains_tax_line():
    processor = OrderProcessor()
    number = processor.issue_invoice(make_order(), 4428.0)
    assert number == "INV-0001"
    assert "TAX 738.0" in processor.audit.events[0]


def test_reserve_stock_reduces_ledger():
    processor = OrderProcessor()
    assert processor.reserve_stock(make_order()) is True
    assert processor.stock.stock["SKU-1"] == 8


def test_out_of_stock_is_rejected():
    assert OrderProcessor().reserve_stock(make_order(sku="SKU-2", quantity=5)) is False


def test_suspicious_payment_is_refused():
    assert OrderProcessor().charge(make_order(), 60000.0) is False


def test_notify_sends_mail_and_sms():
    processor = OrderProcessor()
    assert processor.notify(make_order(), "hello") is True
    assert processor.mailer.outbox == [("buyer@example.com", "hello")]


def test_full_flow_returns_paid_receipt():
    receipt = OrderProcessor().process(make_order())
    assert receipt == CheckoutReceipt("o-1", 4428.0, True, "INV-0001", True)
