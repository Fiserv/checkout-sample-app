# OpenAI Checkout Sample App

A full-stack e-commerce checkout application demonstrating the integration of OpenAI Apps SDK with Model Context Protocol (MCP) servers. This project consists of a Python backend MCP server and a Node.js/TypeScript frontend UI application.

## 📋 Project Overview

This application showcases how to build intelligent e-commerce experiences using:
- **Model Context Protocol (MCP)** – For LLM-server communication
- **OpenAI Apps SDK** – For rich UI components and widgets
- **Conversational checkout** – Natural language product search and purchase flow

## 📁 Project Structure

```
checkout-sample-app/
├── ch-openai-checkout-app/      # Backend MCP Server (Python)
└── ch-openai-checkout-ui/       # Frontend UI Application (Node.js/TypeScript)
```

### 1. ch-openai-checkout-app (Backend MCP Server)

**Language:** Python  
**Framework:** FastMCP + Uvicorn  
**Port:** 8080

**Description:**
A Python-based MCP server that implements e-commerce tools for:
- Product search and catalog browsing
- Shopping cart management (`add_to_cart`, update quantities)
- Checkout session creation
- Payment processing and order completion

The server maintains shopping cart state across conversation turns using `_meta["widgetSessionId"]` to keep the UI widget in sync with backend state.

**Key Features:**
- SSE (Server-Sent Events) endpoint for MCP protocol
- Structured JSON responses with embedded UI metadata
- Shopping cart state management
- Checkout session handling

**Files:**
- `shopping_cart_python/main.py` – Main application entry point
- `shopping_cart_python/models.py` – Data models for products, carts, and sessions
- `shopping_cart_python/requirements.txt` – Python dependencies
- `shopping_cart_python/Dockerfile` – Container configuration (Python 3.12)
- `product_data.json` – Sample product catalog
- `checkout_session_data.json` – Checkout session templates
- `checkout_completion_data.json` – Order completion data

### 2. ch-openai-checkout-ui (Frontend UI Application)

**Language:** TypeScript/React  
**Framework:** Vite + Tailwind CSS  
**Port:** 8088

**Description:**
A modern web-based UI application that renders the shopping cart widget and interfaces with the Python MCP server. Built with Vite for fast development and production builds.

**Key Features:**
- Shopping cart widget with real-time state sync
- Responsive design using Tailwind CSS
- Dynamic widget rendering from OpenAI Apps SDK
- Product display and checkout interface
- Health check actuator endpoint

**Files:**
- `src/shopping-cart/` – Shopping cart widget components
- `src/use-widget-state.ts` – State management hook for widgets
- `src/use-openai-global.ts` – OpenAI SDK integration
- `vite.config.mts` – Vite build configuration
- `package.json` – Node.js dependencies
- `pnpm-lock.yaml` – Dependency lock file
- `Dockerfile` – Container configuration (Node 20 Alpine)

---

## 🚀 Getting Started

### Prerequisites

- **For Python Backend:**
  - Python 3.12+
  - pip or poetry
  - Docker (optional, for containerized setup)

- **For Node.js Frontend:**
  - Node.js 20+
  - pnpm (recommended) or npm/yarn
  - Docker (optional, for containerized setup)

### Setup Instructions

#### Option 1: Run Services Locally

**Backend Setup (Python):**

```bash
cd ch-openai-checkout-app

# Create virtual environment (optional but recommended)
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r shopping_cart_python/requirements.txt

# Run the MCP server
python shopping_cart_python/main.py
# Server runs on http://localhost:8080
```

**Frontend Setup (Node.js):**

```bash
cd ch-openai-checkout-ui

# Install dependencies
pnpm install
# or: npm install

# Development server (hot reload)
pnpm run dev
# or: npm run dev
# Accessible at http://localhost:8088

# Build for production
pnpm run build
# or: npm run build

# Preview production build
pnpm serve
```

#### Option 3: Run with Docker

**Build Backend:**

```bash
cd ch-openai-checkout-app
docker build -f shopping_cart_python/Dockerfile -t checkout-app-backend .
docker run -p 8080:8080 checkout-app-backend
```

**Build Frontend:**

```bash
cd ch-openai-checkout-ui
docker build -f Dockerfile -t checkout-app-ui .
docker run -p 8088:8088 checkout-app-ui
```

---

## 🔄 How the Application Works

### Conversation Flow

1. **User Request** → "I'd like to find a gift card"
2. **MCP Tool Call** → `product_search` tool is triggered
3. **Product Results** → Search results returned with product catalog
4. **Add to Cart** → User clicks add button in the shopping cart widget
5. **State Sync** → Widget state updates via `_meta["widgetSessionId"]`
6. **Checkout** → User clicks checkout to create a checkout session
7. **Payment** → Card capture screen appears for tokenization
8. **Order Complete** → Order confirmation is displayed

### State Management

- **Backend State:** Cart maintained on the Python server
- **Widget State:** Synchronized via `window.openai.widgetState`
- **Session Tracking:** `widgetSessionId` keeps widget and server aligned across conversation turns
- **Persistence:** Checkout session ID enables multi-turn order tracking

---

## 📡 API Endpoints

### Backend MCP Server (Port 8080)

- `GET /mcp` – Server-Sent Events (SSE) connection for MCP protocol
- `POST /mcp/messages?sessionId={sessionId}` – Process MCP tool calls
- `GET /actuator/health` – Health check endpoint

### Frontend (Port 8088)

- `/` – Main shopping cart widget interface
- `/actuator/health` – Health check endpoint
- `/assets/*` – Static assets (CSS, JavaScript)

---

## 🛠️ Development

### Backend Development

```bash
cd ch-openai-checkout-app

# Run with auto-reload
uvicorn shopping_cart_python.main:app --reload --host 0.0.0.0 --port 8080
```

### Frontend Development

```bash
cd ch-openai-checkout-ui

# Start dev server with hot reload
pnpm run dev
```

When making changes to either service, follow conventions:
- **Python:** PEP 8 style guide, type hints recommended
- **TypeScript:** ESLint and Prettier configured, run `pnpm run lint`

---

## 📦 Key Dependencies

**Backend (Python):**
- FastMCP – MCP server framework
- Uvicorn – ASGI server
- Pydantic – Data validation
- Requests – HTTP client

**Frontend (Node.js):**
- React – UI framework
- TypeScript – Type safety
- Tailwind CSS – Utility-first CSS
- Vite – Build tool
- Pnpm – Package manager

---

## 📝 Environment Variables

### Backend (.env in ch-openai-checkout-app)

```env
APP_VERSION=1.0.0
HOST=0.0.0.0
PORT=8080
```

### Frontend (.env in ch-openai-checkout-ui)

```env
VITE_API_URL=http://localhost:8088
VITE_PORT=8088
```

---

## 🚢 Deployment

### Docker Setup

Both services include Dockerfiles optimized for production:

- **Backend:** `python:3.12-slim` – Lightweight Python image
- **Frontend:** `node:20-alpine` – Minimal Node.js image

### Kubernetes

For Kubernetes deployments, adapt the Docker images and expose services via Ingress.

---

## 📚 Additional Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk)
- [FastMCP Documentation](https://fastmcp.dev)
- [Vite Documentation](https://vitejs.dev)

---

## 📄 License

MIT License – See LICENSE file for details

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

For issues, questions, or suggestions, please open a GitHub issue or contact the maintainers.
