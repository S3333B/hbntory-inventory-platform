# Product MCP Server — read-only product tools for HBntory.
# Does not include PostgreSQL credentials and never stores catalog data.
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

COPY product_mcp_server /app/product_mcp_server

EXPOSE 8001

# Streamable HTTP endpoint path is /mcp (see MCP_SERVER_URL in .env.example).
CMD ["python", "-m", "product_mcp_server.app.server"]
