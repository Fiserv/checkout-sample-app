"""Simple ecommerce MCP server exposing the shopping cart widget.

This module implements a Model Context Protocol (MCP) server that provides
an interactive shopping cart widget with the following capabilities:

- Add items to cart
- Create checkout sessions
- Complete checkout with payment
- Search product catalog

The server exposes these operations as MCP tools and provides an HTML widget
for visual interaction through compatible clients.

Environment Variables:
    MCP_WIDGET_TEMPLATE_URI: Widget template URI (default: ui://widget/shopping-cart.html)
    ASSET_BASE_URL: Base URL for static assets (default: http://localhost:4444)
    CHECKOUT_SESSION_API_URL: External API endpoint for creating checkout sessions
    CHECKOUT_COMPLETION_API_URL: External API endpoint for completing checkouts
    PRODUCT_SEARCH_API_URL: External API endpoint for product search
    MCP_ALLOWED_HOSTS: Comma-separated list of allowed hosts for DNS rebinding protection
    MCP_ALLOWED_ORIGINS: Comma-separated list of allowed origins for CORS

Example:
    Run the server directly:
        $ python main.py
    
    Or with uvicorn:
        $ uvicorn main:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from time import time
from typing import Any, Dict, List
from uuid import uuid4

import mcp.types as types
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import ValidationError
import requests

try:
    from .models import (
        AddToCartInput,
        Address,
        Buyer,
        CartItem,
        CompleteCheckoutInput,
        GetCheckoutSessionInput,
        Item,
        MERCHANT_MAPPING,
        PaymentData,
        ProductSearchRequest,
    )
except ImportError:  # pragma: no cover - fallback when running as script
    from models import (
        AddToCartInput,
        Address,
        Buyer,
        CartItem,
        CompleteCheckoutInput,
        GetCheckoutSessionInput,
        Item,
        MERCHANT_MAPPING,
        PaymentData,
        ProductSearchRequest,
    )

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

# ============================================================================
# MCP Tool Names
# ============================================================================
TOOL_NAME_ADD_TO_CART = "add_to_cart"
TOOL_NAME_GET_CHECKOUT_SESSION = "get_checkout_session"
TOOL_NAME_COMPLETE_CHECKOUT = "complete_checkout"
TOOL_NAME_PRODUCT_SEARCH = "product_search"

# ============================================================================
# Widget Configuration
# ============================================================================
WIDGET_TEMPLATE_URI = os.getenv("MCP_WIDGET_TEMPLATE_URI", "ui://widget/shopping-cart.html")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://localhost:4444")
WIDGET_TITLE = os.getenv("MCP_WIDGET_TITLE", "Start shopping cart")
WIDGET_INVOKING = os.getenv("MCP_WIDGET_INVOKING", "Preparing shopping cart")
WIDGET_INVOKED = os.getenv("MCP_WIDGET_INVOKED", "Shopping cart ready")
MIME_TYPE = os.getenv("MCP_WIDGET_MIME_TYPE", "text/html+skybridge")

# ============================================================================
# External API Configuration
# ============================================================================
CHECKOUT_SESSION_API_URL = os.getenv("CHECKOUT_SESSION_API_URL")
PRODUCT_SEARCH_API_URL = os.getenv("PRODUCT_SEARCH_API_URL")
CHECKOUT_COMPLETION_API_URL = os.getenv("CHECKOUT_COMPLETION_API_URL")

# API Configuration
API_TIMEOUT = 10  # seconds
API_AUTHORIZATION = os.getenv("AUTH_HEADER_CHECKOUT_API") # bearer token or other auth value for API requests
API_KEY = os.getenv("APIGEE_API_KEY") # Your API key
API_ORIGINATOR = os.getenv("API_X_ORIGINATOR", "test-originator")
DEVELOPER_EMAIL = os.getenv("API_DEVELOPER_EMAIL", "test@fiserv.com")
CENTS_TO_DOLLARS_MULTIPLIER = 100

# Feature Flags
USE_STATIC_DATA = os.getenv("USE_STATIC_DATA", "false").lower() in ("true", "1", "yes")

# ============================================================================
# File System Paths
# ============================================================================
ASSETS_DIR = BASE_DIR.parent / "assets"
PRODUCT_DATA_FILE = BASE_DIR / "product_data.json"
CHECKOUT_SESSION_DATA_FILE = BASE_DIR / "checkout_session_data.json"
CHECKOUT_COMPLETION_DATA_FILE = BASE_DIR / "checkout_completion_data.json"


# ============================================================================
# Widget HTML Loading
# ============================================================================
def _load_widget_html() -> str:
    """Load the shopping cart widget HTML template.
    
    Attempts to load shopping-cart.html and replaces the ASSETS_BASE_URL placeholder.
    Falls back to versioned HTML files if the main file doesn't exist.
    
    Returns:
        str: The HTML content of the widget template.
        
    Raises:
        FileNotFoundError: If no widget HTML file is found in the assets directory.
    """
    html_path = ASSETS_DIR / "shopping-cart.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf8")
        return html.replace("ASSETS_BASE_URL", ASSET_BASE_URL)

    fallback = sorted(ASSETS_DIR.glob("shopping-cart-*.html"))
    if fallback:
        return fallback[-1].read_text(encoding="utf8")

    raise FileNotFoundError(
        f'Widget HTML for "shopping-cart" not found in {ASSETS_DIR}. '
        "Run `pnpm run build` to generate the assets before starting the server."
    )


SHOPPING_CART_HTML = _load_widget_html()


def _load_static_data(file_path: Path) -> Dict[str, Any]:
    """Load static data from JSON file.
    
    Returns:
        Dictionary containing results data.
        
    Raises:
        FileNotFoundError: If the data file is not found.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {file_path}. "
            "Please create the file in the shopping_cart_python directory."
        )
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================================
# Utility Functions
# ============================================================================
def _split_env_list(value: str | None) -> List[str]:
    """Split a comma-separated environment variable into a list of strings.
    
    Args:
        value: Comma-separated string or None.
        
    Returns:
        List of trimmed non-empty strings.
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _transport_security_settings() -> TransportSecuritySettings:
    """Configure transport security settings for the MCP server.
    
    Returns:
        TransportSecuritySettings with DNS rebinding protection configured
        based on environment variables MCP_ALLOWED_HOSTS and MCP_ALLOWED_ORIGINS.
    """
    allowed_hosts = _split_env_list(os.getenv("MCP_ALLOWED_HOSTS"))
    allowed_origins = _split_env_list(os.getenv("MCP_ALLOWED_ORIGINS"))
    if not allowed_hosts and not allowed_origins:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )

# ============================================================================
# JSON Schemas
# ============================================================================
TOOL_INPUT_SCHEMA_ADD_TO_CART = AddToCartInput.model_json_schema(by_alias=True)
TOOL_INPUT_SCHEMA_GET_CHECKOUT_SESSION = GetCheckoutSessionInput.model_json_schema(by_alias=True)
TOOL_INPUT_SCHEMA_COMPLETE_CHECKOUT = CompleteCheckoutInput.model_json_schema(by_alias=True)
TOOL_INPUT_SCHEMA_PRODUCT_SEARCH = ProductSearchRequest.model_json_schema(by_alias=True)

# ============================================================================
# State Management
# ============================================================================
carts: Dict[str, List[Dict[str, Any]]] = {}

# ============================================================================
# MCP Server Initialization
# ============================================================================
mcp = FastMCP(
    name="ecommerce-python",
    stateless_http=True,
    transport_security=_transport_security_settings(),
)


from starlette.requests import Request
from starlette.responses import JSONResponse


# ============================================================================
# Health Check
# ============================================================================
async def health(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring.
    
    Args:
        request: Starlette request object.
        
    Returns:
        JSONResponse indicating the service health status.
    """
    return JSONResponse({"status": "UP"})


# ============================================================================
# Helper Functions
# ============================================================================
def _serialize_item(item: CartItem) -> Dict[str, Any]:
    """Return a JSON serializable dict including any custom fields."""
    return item.model_dump(by_alias=True)


def _get_or_create_cart(cart_id: str | None) -> str:
    """Get an existing cart or create a new one.
    
    Args:
        cart_id: Optional existing cart ID.
        
    Returns:
        Cart ID (existing or newly created).
    """
    if cart_id and cart_id in carts:
        return cart_id

    new_id = cart_id or uuid4().hex
    carts.setdefault(new_id, [])
    return new_id


def _widget_meta() -> Dict[str, Any]:
    """Generate widget metadata for OpenAI tool invocations.
    
    Returns:
        Dictionary containing widget configuration metadata.
    """
    return {
        "openai/outputTemplate": WIDGET_TEMPLATE_URI,
        "openai/toolInvocation/invoking": WIDGET_INVOKING,
        "openai/toolInvocation/invoked": WIDGET_INVOKED,
        "openai/widgetAccessible": True,
    }


def _build_api_headers() -> Dict[str, str]:
    """Build standard API headers for checkout and search requests.
    
    Returns:
        Dictionary of HTTP headers with authentication and tracking values.
    """
    return {
        "Content-Type": "application/json",
        "Request-Id": str(uuid4()),
        "Idempotency-Key": str(uuid4()),
        "Authorization": API_AUTHORIZATION,
        "Accept-Language": "en-US",
        "Timestamp": str(int(time())),
        "Api-Key": API_KEY,
        "X-B3-SpanId": str(uuid4()),
        "X-B3-TraceId": str(uuid4()),
        "Client-Request-Id": str(uuid4()),
        "X-Developer-Email": DEVELOPER_EMAIL,
        "X-Originator": API_ORIGINATOR,
        "X-System-Entry-Time": str(int(time())),
    }


def _convert_prices_to_cents(api_response: Dict[str, Any]) -> None:
    """Convert price fields from dollars to cents in the API response.
    
    Modifies the response in-place, converting base_amount, subtotal, total,
    discount, and tax fields in line_items, and amount in totals.
    
    Args:
        api_response: API response dictionary to modify.
    """
    # Convert line item prices
    if "line_items" in api_response and isinstance(api_response["line_items"], list):
        for item in api_response["line_items"]:
            for field in ["base_amount", "subtotal", "total", "discount", "tax"]:
                if field in item and item[field] not in (None, 0):
                    item[field] = int(item[field] * CENTS_TO_DOLLARS_MULTIPLIER)
    
    # Convert totals
    if "totals" in api_response and isinstance(api_response["totals"], list):
        for item in api_response["totals"]:
            if "amount" in item and item["amount"] is not None:
                item["amount"] = int(item["amount"] * CENTS_TO_DOLLARS_MULTIPLIER)


def _normalize_checkout_response(api_response: Dict[str, Any]) -> None:
    """Normalize checkout API response with standard fields.
    
    Converts prices, sets currency, and configures payment provider.
    
    Args:
        api_response: API response dictionary to normalize in-place.
    """

    # Set the test mode and status for the checkout session (for demo purposes)
    api_response["payment_mode"] = "test"
            
    # # Transform links structure: change "value" to "url" and ensure non-null URLs
    # if "links" in api_response and isinstance(api_response["links"], list):
    #     for link in api_response["links"]:
    #         if "value" in link:
    #             # Change "value" to "url" and provide default if empty/null
    #             url_value = link.pop("value")
    #             link["url"] = url_value if url_value else "https://test.com/products"
    #         elif "url" in link and not link["url"]:
    #             # Ensure existing "url" field is not empty/null
    #             link["url"] = "https://test.com/products"
    
    # Transform fulfillment options: convert amounts to cents and set ID
    if "fulfillment_options" in api_response and isinstance(api_response["fulfillment_options"], list):
        fulfillment_option_id = api_response.get("fulfillment_option_id")
        
        for option in api_response["fulfillment_options"]:
            # Set ID from fulfillment_option_id if available
            if fulfillment_option_id:
                option["id"] = fulfillment_option_id
                option["type"] = "shipping"
                option["carrier"] = "UPS"
                option["earliest_delivery_time"] = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat() + "Z"
                option["latest_delivery_time"] = (datetime.now() + timedelta(days=5)).replace(microsecond=0).isoformat() + "Z" 
                option["subtitle"] = "Estimated delivery in 3-5 business days"
            


# ============================================================================
# MCP Tool Handlers
# ============================================================================
@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    """List all available MCP tools.
    
    Returns:
        List of Tool objects representing available ecommerce operations.
    """
    return [
        types.Tool(
            name=TOOL_NAME_ADD_TO_CART,
            title="Add items to cart",
            description="Adds the provided items to the active cart and returns its state.",
            inputSchema=TOOL_INPUT_SCHEMA_ADD_TO_CART,
            _meta=_widget_meta()
        ),
        types.Tool(
            name=TOOL_NAME_GET_CHECKOUT_SESSION,
            title="Get checkout session",
            description="Creates a checkout session for the provided items and returns the session details.",
            inputSchema=TOOL_INPUT_SCHEMA_GET_CHECKOUT_SESSION,
            _meta=_widget_meta()
        ),
        types.Tool(
            name=TOOL_NAME_COMPLETE_CHECKOUT,
            title="Complete checkout",
            description="Completes the checkout process for the active cart.",
            inputSchema=TOOL_INPUT_SCHEMA_COMPLETE_CHECKOUT,
            _meta=_widget_meta()
        ),
        types.Tool(
            name=TOOL_NAME_PRODUCT_SEARCH,
            title="Product search",
            description=f"Searches for products in the catalog. Available merchants: {', '.join(f'{k}: {v}' for k, v in MERCHANT_MAPPING.items())}",
            inputSchema=TOOL_INPUT_SCHEMA_PRODUCT_SEARCH,
            _meta=_widget_meta()
        ),
    ]



@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    """List all available MCP resources.
    
    Returns:
        List of Resource objects (widget templates).
    """
    return [
        types.Resource(
            name=WIDGET_TITLE,
            title=WIDGET_TITLE,
            uri=WIDGET_TEMPLATE_URI,
            description="Markup for the shopping cart widget.",
            mimeType=MIME_TYPE,
            _meta=_widget_meta(),
        )
    ]


async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    """Handle resource read requests for widget templates.
    
    Args:
        req: ReadResourceRequest containing the URI to read.
        
    Returns:
        ServerResult with the resource contents or error.
    """
    if str(req.params.uri) != WIDGET_TEMPLATE_URI:
        return types.ServerResult(
            types.ReadResourceResult(
                contents=[],
                _meta={"error": f"Unknown resource: {req.params.uri}"},
            )
        )

    contents = [
        types.TextResourceContents(
            uri=WIDGET_TEMPLATE_URI,
            mimeType=MIME_TYPE,
            text=SHOPPING_CART_HTML,
            _meta=_widget_meta(),
        )
    ]
    return types.ServerResult(types.ReadResourceResult(contents=contents))


# ============================================================================
# Tool Call Dispatcher and Handlers
# ============================================================================
async def _handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
    """Handle MCP tool invocation requests.
    
    Dispatches to the appropriate handler based on tool name and validates input.
    Supports add_to_cart, get_checkout_session, complete_checkout, and product_search tools.
    
    Args:
        req: CallToolRequest containing tool name and arguments.
        
    Returns:
        ServerResult with tool execution results or error information.
    """
    print(f"Handling tool call: {req.params.name} with args: {req.params.arguments}")
    
    # Validate tool name
    valid_tools = {
        TOOL_NAME_ADD_TO_CART,
        TOOL_NAME_COMPLETE_CHECKOUT,
        TOOL_NAME_GET_CHECKOUT_SESSION,
        TOOL_NAME_PRODUCT_SEARCH,
    }
    
    if req.params.name not in valid_tools:
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Unknown tool: {req.params.name}",
                    )
                ],
                isError=True,
            )
        )

    # Validate input schema based on tool name
    validation_mapping = {
        TOOL_NAME_ADD_TO_CART: AddToCartInput,
        TOOL_NAME_GET_CHECKOUT_SESSION: GetCheckoutSessionInput,
        TOOL_NAME_COMPLETE_CHECKOUT: CompleteCheckoutInput,
        TOOL_NAME_PRODUCT_SEARCH: ProductSearchRequest,
    }
    
    try:
        validator = validation_mapping[req.params.name]
        validator.model_validate(req.params.arguments or {})
    except ValidationError as exc:
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text", text=f"Invalid input: {exc.errors()}"
                    )
                ],
                isError=True,
            )
        )

    # Dispatch to appropriate handler
    if req.params.name == TOOL_NAME_ADD_TO_CART:
        return await _handle_add_to_cart(req)
    elif req.params.name == TOOL_NAME_GET_CHECKOUT_SESSION:
        return await _handle_get_checkout_session(req)
    elif req.params.name == TOOL_NAME_COMPLETE_CHECKOUT:
        return await _handle_complete_checkout(req)
    elif req.params.name == TOOL_NAME_PRODUCT_SEARCH:
        return await _handle_product_search(req)


async def _handle_add_to_cart(req: types.CallToolRequest) -> types.ServerResult:
    """Handle add_to_cart tool invocation.
    
    Args:
        req: CallToolRequest with cart_id and items.
        
    Returns:
        ServerResult with updated cart state.
    """
    payload = AddToCartInput.model_validate(req.params.arguments or {})
    cart_id = _get_or_create_cart(payload.cart_id)
    
    cart_items = [_serialize_item(item) for item in payload.items]

    structured_content = {
        "cartId": cart_id,
        "items": [dict(item) for item in cart_items],
    }
    meta = _widget_meta()
    meta["openai/widgetSessionId"] = cart_id

    message = f"Cart {cart_id} now has {len(cart_items)} item(s)."
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=message)],
            structuredContent=structured_content,
            _meta=meta,
        )
    )


async def _handle_get_checkout_session(req: types.CallToolRequest) -> types.ServerResult:
    """Handle get_checkout_session tool invocation.
    
    Creates a checkout session via external API and returns normalized response.
    
    Args:
        req: CallToolRequest with items and optional fulfillment_address.
        
    Returns:
        ServerResult with checkout session details.
    """
    payload = GetCheckoutSessionInput.model_validate(req.params.arguments or {})
    
    # Extract request headers from MCP request metadata (for debugging)
    request_headers = {}
    if hasattr(req, '_meta') and req._meta:
        request_headers = req._meta.get('headers', {})
        
    # Build API payload
    api_payload = {
        "items": [item.model_dump(by_alias=True) for item in payload.items],
        "fulfillment_address": (
            payload.fulfillment_address.model_dump(by_alias=True)
            if payload.fulfillment_address
            else None
        ),
    }
    
    # Load static data or call API based on configuration
    if USE_STATIC_DATA:
        # Load static checkout session data from JSON file
        try:
            print(f"Using static data for checkout session. Request headers: {request_headers}")
            api_response = _load_static_data(CHECKOUT_SESSION_DATA_FILE)
            api_response["id"] = str(uuid4())  # Generate unique session ID for each request
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return types.ServerResult(
                types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text",
                            text=f"Failed to load checkout session data: {str(e)}"
                        )
                    ],
                    isError=True,
                )
            )
    else:
        # Call checkout session API
        response = requests.post(
            CHECKOUT_SESSION_API_URL,
            headers=_build_api_headers(),
            json=api_payload,
            timeout=API_TIMEOUT
        )
        api_response = response.json()
        
        # Normalize response
        _normalize_checkout_response(api_response)

    return types.ServerResult(
        types.CallToolResult(
            content=[],
            structuredContent=api_response,
            isError=False,
        )
    )


async def _handle_complete_checkout(req: types.CallToolRequest) -> types.ServerResult:
    """Handle complete_checkout tool invocation.
    
    Completes the checkout process by sending buyer and payment data to the API.
    
    Args:
        req: CallToolRequest with checkout_session_id, buyer, and payment_data.
        
    Returns:
        ServerResult with order completion details.
    """
    payload = CompleteCheckoutInput.model_validate(req.params.arguments or {})
    
    # Load static data or call API based on configuration
    if USE_STATIC_DATA:
        # Load static completion data from JSON file
        try:
            print(f"Using static data for checkout session completion. Checkout Session ID: {payload.checkout_session_id}")
            response_data = _load_static_data(CHECKOUT_COMPLETION_DATA_FILE)
            response_data["id"] = payload.checkout_session_id
            response_data["order"]["checkout_session_id"] = payload.checkout_session_id
            response_data["order"]["id"] = str(uuid4())  # Generate unique order ID
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return types.ServerResult(
                types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text",
                            text=f"Failed to load checkout completion data: {str(e)}"
                        )
                    ],
                    isError=True,
                )
            )
    else:
        # Build API payload
        api_payload = {
            "buyer": payload.buyer.model_dump(by_alias=True) if payload.buyer else None,
            "payment_data": (
                payload.payment_data.model_dump(by_alias=True)
                if payload.payment_data
                else None
            ),
        }
        
        # Call checkout completion API
        response = requests.post(
            CHECKOUT_COMPLETION_API_URL.format(checkout_session_id=payload.checkout_session_id),
            headers=_build_api_headers(),
            json=api_payload,
            timeout=API_TIMEOUT
        )
        response_data = response.json()
        
    return types.ServerResult(
        types.CallToolResult(
            content=[],
            structuredContent=response_data,
            isError=False,
        )
    )


async def _handle_product_search(req: types.CallToolRequest) -> types.ServerResult:
    """Handle product_search tool invocation.
    
    Search product data by calling external API.
    
    Args:
        req: CallToolRequest with query and optional merchant.
        
    Returns:
        ServerResult with search results and line items.
    """
    payload = ProductSearchRequest.model_validate(req.params.arguments or {})

    # Load static data or call API based on configuration
    if USE_STATIC_DATA:
        # Load static product data from JSON file
        try:
            print(f"Using static data for product search. Query: {payload.query}, Merchant: {payload.merchant}")
            api_response = _load_static_data(PRODUCT_DATA_FILE)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return types.ServerResult(
                types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text",
                            text=f"Failed to load product data: {str(e)}"
                        )
                    ],
                    isError=True,
                )
            )
        # Note: In a real implementation, you would filter the results based on
        # payload.query and payload.merchant here
    else:
        # Build API payload
        api_payload = {"search": payload.query}
        if payload.merchant is not None:
            api_payload["merchant"] = payload.merchant

        # Call product search API
        response = requests.post(
            PRODUCT_SEARCH_API_URL,
            headers={
                "Content-Type": "application/json",
                "Request-Id": str(uuid4()),
                "Client-Request-Id": str(uuid4()),
            },
            json=api_payload,
            timeout=API_TIMEOUT
        )
        api_response = response.json()
            
    # Create new cart for widget session
    cart_id = _get_or_create_cart(None)
    meta = _widget_meta()
    meta["openai/widgetSessionId"] = cart_id

    return types.ServerResult(
        types.CallToolResult(
            content=[],
            structuredContent=api_response,
            _meta=meta,
            isError=False,
        )
    )


# ============================================================================
# Application Setup
# ============================================================================
# Register request handlers
mcp._mcp_server.request_handlers[types.CallToolRequest] = _handle_call_tool
mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource

# Create Starlette app
app = mcp.streamable_http_app()
app.add_route("/actuator/health", health, methods=["GET"])

# Configure CORS middleware
try:
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
except Exception:
    # CORS middleware is optional
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
