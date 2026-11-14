import pytest

from app.checkout.domain import CheckoutOrder, CheckoutReceipt
from app.checkout.wiring import build_services, process_order


def make_order(**changes):
    values = dict(order_id="o-1", customer="c-1", region="UA", category="tools", currency="USD",
                  amount=100.0, quantity=2, sku="SKU-1", email="buyer@example.com")
    values.update(changes)
    return CheckoutOrder(**values)


@pytest.fixture
def parts():
    return build_services()


def test_price_applies_discount_and_tax(parts):
    assert parts["pricing"].price(make_order()) == 4428.0


def test_books_have_reduced_tax(parts):
    assert parts["pricing"].price(make_order(category="books")) == 4059.0


def test_estimate_matches_price(parts):
    assert parts["pricing"].estimate(make_order()) == 4428.0


def test_tax_part_is_tax_only(parts):
    assert parts["pricing"].tax_part(make_order()) == 738.0


def test_reserve_reduces_stock_and_rejects_shortage(parts):
    assert parts["fulfillment"].reserve(make_order()) is True
    assert parts["fulfillment"].reserve(make_order(sku="SKU-2", quantity=5)) is False


def test_suspicious_payment_is_refused(parts):
    assert parts["payment"].charge(make_order(), 60000.0) is False


def test_billing_numbers_invoices_and_notifies(parts):
    number = parts["billing"].issue(make_order(), 4428.0, 738.0)
    assert number == "INV-0001"
    assert parts["mailer"].outbox[0][0] == "buyer@example.com"
    assert parts["sms"].sent[0][0] == "c-1"


def test_full_flow_returns_paid_receipt(parts):
    receipt = process_order(make_order(), parts["pricing"], parts["fulfillment"], parts["payment"],
                            parts["billing"], parts["audit"])
    assert receipt == CheckoutReceipt("o-1", 4428.0, True, "INV-0001", True)


def test_failed_payment_releases_stock_and_audits(parts):
    order = make_order(amount=1000000.0, currency="UAH")
    receipt = process_order(order, parts["pricing"], parts["fulfillment"], parts["payment"],
                            parts["billing"], parts["audit"])
    assert receipt.paid is False
    assert parts["audit"].events == ["payment failed o-1"]
