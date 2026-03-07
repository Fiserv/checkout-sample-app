FROM python:3.12-slim

# Build arguments
ARG APP_VERSION=1.0.0
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app

# Install deps first to maximize cache reuse
COPY shopping_cart_python/requirements.txt ./shopping_cart_python/requirements.txt
RUN pip install --no-cache-dir -r shopping_cart_python/requirements.txt

# Copy application code and assets
COPY shopping_cart_python/ ./shopping_cart_python/
COPY assets/ ./assets/


EXPOSE 8080

# Use venv's uvicorn directly or activate venv before running
CMD ["uvicorn", "shopping_cart_python.main:app", "--host", "0.0.0.0", "--port", "8080"]