# Product MCP Server — read-only product + stock tools for HBntory.
# Stock tools use controlled SQLAlchemy reads against PostgreSQL.
# No arbitrary SQL tools. Catalog data is never persisted.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8001 \
    MCP_TRANSPORT=streamable-http \
    PRODUCT_API_URL=http://external-products-api:5000 \
    PRODUCT_API_TIMEOUT=5.0

COPY product_mcp_server/requirements.txt /app/product_mcp_server/requirements.txt
RUN pip install --no-cache-dir -r /app/product_mcp_server/requirements.txt

# Stock tools reuse Backoffice SQLAlchemy models/database helpers without
# starting the Flask application or copying catalog data.
COPY backoffice /app/backoffice
COPY product_mcp_server /app/product_mcp_server

EXPOSE 8001

# Streamable HTTP endpoint path is /mcp (see MCP_SERVER_URL in .env.example).
CMD ["python", "-m", "product_mcp_server.app.server"]
