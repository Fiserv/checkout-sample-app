FROM fmk-prod.nexus-ci.onefiserv.net/fmk/python/python-3.12:FMK-25-06-10

# Build arguments
ARG APP_VERSION=1.0.0
ARG FISV_PROXY=http://proxy-na.fiserv.one:8080/
ENV APP_VERSION=${APP_VERSION}

# Default environment variables (can be overridden at runtime)
ENV MCP_WIDGET_TEMPLATE_URI=ui://widget/shopping-cart.html
ENV ASSET_BASE_URL=https://agentic-commerce.gift.solutions/assets
#ENV ASSET_BASE_URL=http://localhost:54612
ENV MCP_WIDGET_TITLE="Start shopping cart"
ENV MCP_WIDGET_INVOKING="Preparing shopping cart"
ENV MCP_WIDGET_INVOKED="Shopping cart ready"
ENV MCP_WIDGET_MIME_TYPE="text/html+skybridge"
ENV CHECKOUT_SESSION_API_URL=https://ch-agent-acp-service-dev-us-east-1.gbs-agentic-commerce-dev-nonprod.aws.fisv.cloud/agents/v1/acp/checkout_sessions
ENV PRODUCT_SEARCH_API_URL=https://dev-product-discovery-services.commercehub-development-nonprod.aws.fisv.cloud/products/search?channel=CHATGPT
ENV CHECKOUT_COMPLETION_API_URL=https://ch-agent-acp-service-dev-us-east-1.gbs-agentic-commerce-dev-nonprod.aws.fisv.cloud/agents/v1/acp/checkout_sessions/{checkout_session_id}/complete
ENV AUTH_HEADER_CHECKOUT_API="Basic YWRtaW46dGFjb2NhdA=="
ENV APIGEE_API_KEY="xcxh77ixvztKxJ0gRawFXor79TKeqQLJ"
ENV API_DEVELOPER_EMAIL="pavan.joshi@fiserv.com"
ENV API_X_ORIGINATOR="test-acp"
ENV USE_STATIC_DATA=true

WORKDIR /app

# Install deps first to maximize cache reuse
COPY shopping_cart_python/requirements.txt ./shopping_cart_python/requirements.txt
ENV VIRTUAL_ENV=/home/python/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
USER python
RUN python3.12 -m venv "$VIRTUAL_ENV" \
    && chmod -R a+rX "$VIRTUAL_ENV" \
    && pip3 install -vvv --no-cache-dir --proxy "$FISV_PROXY" \
    --index-url https://nexus.onefiserv.net/repository/pypi-proxy/simple -r shopping_cart_python/requirements.txt

# Copy application code and assets
COPY shopping_cart_python/ ./shopping_cart_python/
COPY assets/ ./assets/

# Health check for ECS Fargate
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/actuator/health', timeout=5)"

EXPOSE 8080

# Use venv's uvicorn directly or activate venv before running
CMD ["uvicorn", "shopping_cart_python.main:app", "--host", "0.0.0.0", "--port", "8080"]