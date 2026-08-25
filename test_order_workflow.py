from commerce_models import CheckoutItem, CheckoutRequest
from order_workflow import decide_checkout


def checkout(available_quantity: int) -> CheckoutRequest:
    return CheckoutRequest(
        customer_id="cus_42",
        email="ada@example.com",
        captcha_token="verified-by-request-boundary",
        items=[
            CheckoutItem(
                sku="agent-field-guide",
                quantity=2,
                unit_price_cents=2400,
                available_quantity=available_quantity,
            )
        ],
    )


def test_in_stock_checkout_requests_fulfillment_and_issues_receipt() -> None:
    result = decide_checkout(checkout(available_quantity=5))

    assert result.status == "ready_for_fulfillment"
    assert result.fulfillment_requested is True
    assert result.receipt is not None
    assert result.receipt.total_cents == 4800
    assert result.customer_update.order_id == result.order_id


def test_short_inventory_holds_fulfillment_and_receipt() -> None:
    result = decide_checkout(checkout(available_quantity=1))

    assert result.status == "inventory_review"
    assert result.fulfillment_requested is False
    assert result.receipt is None
