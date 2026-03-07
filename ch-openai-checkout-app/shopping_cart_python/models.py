"""Pydantic models for the ecommerce MCP server."""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

# Merchant name to ID mappings
MERCHANT_MAPPING = {
    "HomeDepot": "100015000300423",
    "Panera": "panerabread",
    "Dell": "dell",
    "NewEgg": "NewEgg",
}

__all__ = [
    "AddToCartInput",
    "Address",
    "Allowance",
    "BillingAddress",
    "Buyer",
    "CartItem",
    "CheckoutInput",
    "CompleteCheckoutInput",
    "DelegatePaymentRequest",
    "GetCheckoutSessionInput",
    "Item",
    "MERCHANT_MAPPING",
    "Order",
    "PaymentData",
    "PaymentMethod",
    "ProductSearchRequest",
    "RiskSignal",
]


class CartItem(BaseModel):
    """Represents an item being added to a cart."""

    name: str = Field(..., description="Name of the item to show in the cart.")
    quantity: int = Field(
        default=1,
        ge=1,
        description="How many units to add to the cart (must be positive).",
    )

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class AddToCartInput(BaseModel):
    """Payload for the add_to_cart tool."""

    items: List[CartItem] = Field(
        ...,
        description="List of items to add to the active cart.",
    )
    cart_id: str | None = Field(
        default=None,
        alias="cartId",
        description="Existing cart identifier. Leave blank to start a new cart.",
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Address(BaseModel):
    """Represents a physical address."""

    name: str = Field(
        ..., description="Name of the person to whom the items are shipped.", max_length=256
    )
    line_one: str = Field(..., description="First line of address.", max_length=60)
    line_two: str | None = Field(
        default=None, description="Optional second line of address.", max_length=60
    )
    city: str = Field(
        ..., description="Address city/district/suburb/town/village.", max_length=60
    )
    state: str = Field(
        ..., description="Address state/county/province/region. Should follow the ISO 3166-1 standard"
    )
    country: str = Field(
        ..., description="Address country. Should follow the ISO 3166-1 standard"
    )
    postal_code: str = Field(
        ..., description="Address postal code or zip code.", max_length=20
    )
    phone_number: str | None = Field(
        default=None, description="Optional phone number. Follows the E.164 standard."
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Item(BaseModel):
    """Represents an item used in checkout operations."""

    id: str = Field(..., description="Unique identifier for the item.")
    quantity: int = Field(..., description="Quantity of the item.")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class GetCheckoutSessionInput(BaseModel):
    """Payload for the get_checkout_session tool."""

    items: List[Item] = Field(
        ..., description="List of items to include in the checkout session."
    )
    fulfillment_address: Address | None = Field(
        default=None, description="Shipping address for order fulfillment."
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Buyer(BaseModel):
    """Represents a buyer's information."""

    name: str = Field(..., description="Name of the buyer.")
    email: str = Field(..., description="Email address of the buyer.")
    phone_number: str | None = Field(default=None, description="Phone number of the buyer.")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class PaymentData(BaseModel):
    """Represents payment information."""

    token: str = Field(..., description="Credit card number.")
    provider: str = Field(..., description="Expiry date of the credit card.")
    billing_address: Address = Field(
        ..., description="Billing address associated with the payment method."
    )
    managed_by: str | None = Field(
        default=None, description="Optional field indicating who manages the payment method."
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CompleteCheckoutInput(BaseModel):
    """Payload for the complete_checkout tool."""

    checkout_session_id: str = Field(
        ..., alias="checkoutSessionId", description="Identifier for the checkout session to complete."
    )
    buyer: Buyer = Field(..., description="Information about the buyer completing the checkout.")
    payment_data: PaymentData = Field(
        ..., alias="paymentData", description="Payment information for completing the checkout."
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Order(BaseModel):
    """Represents an order."""

    id: str = Field(..., description="Order identifier.")
    checkout_session_id: str = Field(
        ..., alias="checkoutSessionId", description="Checkout session identifier."
    )
    permalink_url: str = Field(
        ..., alias="permalinkUrl", description="Permanent URL for the order."
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class CompleteCheckoutResponse(BaseModel):
    """Payload for the complete_checkout tool."""

    id: str = Field(
        ..., alias="id", description="Identifier for the checkout session to complete."
    )
    status: str = Field(
        ..., alias="status", description="Status of the checkout session."
    )
    currency: str = Field(
        ..., alias="currency", description="Currency of the checkout session."
    )
    order: Order = Field(..., description="Information about the order.")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")



class ProductSearchRequest(BaseModel):
    """Payload for the product search tool."""

    query: str = Field(
        ..., description="Search query for finding products in the catalog."
    )
    merchant: str | None = Field(
        default=None,
        description=(
            "Merchant name to filter products. Default to the_home_depot if not provided. "
            f"Available merchants: {', '.join(f'{k}: {v}' for k, v in MERCHANT_MAPPING.items())}"
        ),
    )
    price_operator: str | None = Field(
        default=None,
        description="Optional comparison operator for prices (<, <=, =, >=, >).",
    )
    price_value: float | int | None = Field(
        default=0,
        description="Optional price value to filter results by when price_operator is set.",
    )

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class PaymentMethod(BaseModel):
    """Payment method details."""

    type: str = Field(..., description="Payment method type (e.g., 'card')")
    card_number_type: str | None = Field(default=None, description="Card number type")
    virtual: bool | None = Field(default=None, description="Whether card is virtual")
    number: str | None = Field(default=None, description="Card number")
    exp_month: str | None = Field(default=None, description="Expiration month")
    exp_year: str | None = Field(default=None, description="Expiration year")
    name: str | None = Field(default=None, description="Cardholder name")
    cvc: str | None = Field(default=None, description="Card verification code")
    checks_performed: List[str] | None = Field(default=None, description="Checks performed")
    iin: str | None = Field(default=None, description="Issuer identification number")
    display_card_funding_type: str | None = Field(default=None, description="Card funding type")
    display_wallet_type: str | None = Field(default=None, description="Wallet type")
    display_brand: str | None = Field(default=None, description="Card brand")
    display_last4: str | None = Field(default=None, description="Last 4 digits")
    metadata: Dict[str, Any] | None = Field(default=None, description="Additional metadata")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Allowance(BaseModel):
    """Payment allowance details."""

    reason: str = Field(..., description="Reason for the allowance")
    max_amount: int | float = Field(..., description="Maximum amount allowed")
    currency: str = Field(..., description="Currency code")
    checkout_session_id: str | None = Field(default=None, description="Checkout session ID")
    merchant_id: str | None = Field(default=None, description="Merchant ID")
    expires_at: str | None = Field(default=None, description="Expiration timestamp")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class BillingAddress(BaseModel):
    """Billing address details."""

    name: str | None = Field(default=None, description="Full name")
    line_one: str | None = Field(default=None, description="Address line 1")
    line_two: str | None = Field(default=None, description="Address line 2")
    city: str | None = Field(default=None, description="City")
    state: str | None = Field(default=None, description="State/Province")
    country: str | None = Field(default=None, description="Country code")
    postal_code: str | None = Field(default=None, description="Postal code")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class RiskSignal(BaseModel):
    """Risk signal information."""

    type: str = Field(..., description="Risk signal type")
    score: int | float | None = Field(default=None, description="Risk score")
    action: str | None = Field(default=None, description="Recommended action")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class DelegatePaymentRequest(BaseModel):
    """Delegate payment request payload."""

    payment_method: PaymentMethod = Field(..., description="Payment method details")
    allowance: Allowance = Field(..., description="Payment allowance details")
    billing_address: BillingAddress | None = Field(default=None, description="Billing address")
    risk_signals: List[RiskSignal] | None = Field(default=None, description="Risk signals")
    metadata: Dict[str, Any] | None = Field(default=None, description="Additional metadata")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class CheckoutInput(BaseModel):
    """Payload for the checkout tool."""

    delegate_payment_request: DelegatePaymentRequest = Field(
        ..., description="Payment delegation request"
    )

    model_config = ConfigDict(populate_by_name=True, extra="allow")
