# Product MCP Server

The future Python MCP server provides a controlled tool layer between the AI agent and HBntory data sources. It consumes the official read-only [hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api) service.

## Planned technology

- Python;
- MCP Python SDK;
- FastMCP;
- MCP Streamable HTTP between containers.

## Product API connection

The server reads the official API base URL only from `PRODUCT_API_URL`. Depending on the execution mode, it may be `http://localhost:5001`, `http://host.docker.internal:5001`, or `http://external-products-api:5000`.

The future HTTP client will use an explicit timeout. It will handle empty lists, unknown products, API unavailability, slow responses, network timeouts, forced HTTP errors, and invalid JSON with structured errors.

## Minimum product tools

- `list_products`;
- `get_product_details`.

These tools use the official product-list and product-detail endpoints. Categories, suppliers, and advanced filters are optional for the MVP.

## Planned stock tools

- `get_stock_by_product`;
- `get_branch_stock`;
- `check_shopping_list`.

## Data access rules

- product tools read from the official external Product API;
- stock tools read through authenticated internal Backoffice endpoints;
- tool failures return clear, structured errors;
- MCP never changes stock;
- MCP never modifies or copies the external API;
- MCP persists no product data locally;
- MCP never connects directly to PostgreSQL.

No MCP tool or server implementation is created during Task 0.
