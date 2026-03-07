# Shopping Cart MCP Server

A Python-based Model Context Protocol (MCP) server that exposes e-commerce tools for shopping cart management and checkout operations. This server integrates with the OpenAI Apps SDK to provide conversational commerce capabilities.

## 📋 Overview

This MCP server implements the following tools:
- **product_search** – Search products by query
- **add_to_cart** – Add items to the shopping cart
- **update_cart_item** – Modify item quantities
- **checkout** – Create checkout sessions
- **place_order** – Process and complete orders

The server maintains cart state across conversation turns using session IDs and returns structured content with widgets for UI rendering.

## 🛠️ Prerequisites

- Python 3.12+
- pip or poetry
- Docker (optional, for containerized setup)

## 📦 Setup

### Local Development

1. **Clone and navigate to this directory:**
   ```bash
   cd ch-openai-checkout-app
   ```

2. **Create a virtual environment:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r shopping_cart_python/requirements.txt
   ```

## 🚀 Build and Run

### Local Execution

```bash
# Run the MCP server directly
python shopping_cart_python/main.py
```

The server starts on `http://localhost:8080` with:
- `GET /mcp` – Server-Sent Events (SSE) endpoint for MCP protocol
- `POST /mcp/messages?sessionId={sessionId}` – Tool execution endpoint
- `GET /actuator/health` – Health check endpoint

### Docker Build and Run

**Build the image:**
```bash
docker build -f shopping_cart_python/Dockerfile -t shopping-cart-python .
```

**Run the container:**
```bash
docker run -p 8080:8080 shopping-cart-python
```

The server will be accessible at `http://localhost:8080`.

## 📂 Project Structure

```
shopping_cart_python/
├── main.py                      # Server entry point and tool definitions
├── models.py                    # Data models (Product, Cart, Session)
├── requirements.txt             # Python dependencies
└── Dockerfile                   # Docker configuration (Python 3.12)

├── product_data.json            # Sample product catalog
├── checkout_session_data.json   # Checkout session templates
└── checkout_completion_data.json # Order completion data
```

## 🔧 Configuration

Environment variables (optional):
```
APP_VERSION=1.0.0
HOST=0.0.0.0
PORT=8080
```

## 🧪 Health Check

Verify the server is running:
```bash
curl http://localhost:8080/actuator/health
```

## 📚 MCP Protocol Details

The server exposes tools following the MCP specification:

- **Tool Definition** – Each tool includes JSON Schema contracts for input/output
- **Tool Execution** – Models issue `call_tool` requests with arguments
- **Structured Response** – Returns data with `_meta["widgetSessionId"]` for UI state synchronization
- **Session Management** – Cart state persisted per session ID across conversation turns

## 🚢 Production Deployment

For production, consider:
- Implement persistent datastore for cart state (database, cache layer)
- Add authentication and authorization
- Enable HTTPS/TLS
- Add request logging and monitoring
- Implement proper error handling
- Configure CORS appropriately

## 📖 API Example

**Search Products:**
```bash
curl -X POST http://localhost:8080/mcp/messages?sessionId=session-123 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call_tool",
    "params": {
      "name": "product_search",
      "arguments": {"query": "gift card"}
    }
  }'
```

## 📄 License

MIT License – See LICENSE file for details