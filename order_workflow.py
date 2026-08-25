import hashlib

from commerce_models import CheckoutRequest, CheckoutResult, CustomerUpdate, Receipt


def decide_checkout(request: CheckoutRequest) -> CheckoutResult:
    """Turn a validated checkout into one visible order transition."""
    fingerprint = "|".join(
        [request.customer_id, request.email]
        + [f"{item.sku}:{item.quantity}:{item.unit_price_cents}" for item in request.items]
    )
    order_id = f"ord_{hashlib.sha256(fingerprint.encode()).hexdigest()[:12]}"
    in_stock = all(item.quantity <= item.available_quantity for item in request.items)

    if not in_stock:
        return CheckoutResult(
            order_id=order_id,
            status="inventory_review",
            fulfillment_requested=False,
            receipt=None,
            customer_update=CustomerUpdate(
                customer_id=request.customer_id,
                order_id=order_id,
                message="We received your order and are confirming inventory.",
            ),
        )

    total_cents = sum(item.quantity * item.unit_price_cents for item in request.items)
    receipt = Receipt(
        receipt_id=f"rcpt_{order_id.removeprefix('ord_')}",
        order_id=order_id,
        total_cents=total_cents,
        email=request.email,
    )
    return CheckoutResult(
        order_id=order_id,
        status="ready_for_fulfillment",
        fulfillment_requested=True,
        receipt=receipt,
        customer_update=CustomerUpdate(
            customer_id=request.customer_id,
            order_id=order_id,
            message=f"Order {order_id} is confirmed and ready for fulfillment.",
        ),
    )
