from typing import Literal

from pydantic import BaseModel, Field


Provider = Literal["google", "github"]


class SocialLoginRequest(BaseModel):
    provider: Provider
    return_to: str
    redirect_uri: str


class CheckoutItem(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    available_quantity: int = Field(ge=0)


class CheckoutRequest(BaseModel):
    customer_id: str
    email: str
    captcha_token: str
    items: list[CheckoutItem] = Field(min_length=1)


class Receipt(BaseModel):
    receipt_id: str
    order_id: str
    total_cents: int
    email: str


class CustomerUpdate(BaseModel):
    customer_id: str
    order_id: str
    message: str


class CheckoutResult(BaseModel):
    order_id: str
    status: Literal["ready_for_fulfillment", "inventory_review"]
    fulfillment_requested: bool
    receipt: Receipt | None
    customer_update: CustomerUpdate
