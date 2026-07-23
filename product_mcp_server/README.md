# Product MCP Server

Read-only MCP tool layer between future HBntory AI agents and the official
External Product API
([hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api)).

Responsible: Ulysse (Task 4 — Product MCP Server).

## Role

- expose controlled product tools to an AI agent over MCP;
- call the official External Product API through an internal HTTP client;
- return structured successes and errors the agent can ground answers on;
- never store product catalog data in PostgreSQL;
- never write to the Product API;
- never connect to PostgreSQL;
- never expose stock tools in this task (stock tools come later).

## Architecture flow

```text
AI agent / MCP Inspector
        |  MCP Streamable HTTP  (/mcp)
        v
Product MCP Server (FastMCP)
        |  ProductApiClient (httpx, explicit timeout)
        v
External Product API  GET /api/v1/products[...]
```

Separation of concerns:

| Module | Responsibility |
| --- | --- |
| `app/config.py` | Environment settings |
| `app/exceptions.py` | Explicit client errors |
| `app/models.py` | Stable product / list shapes |
| `app/product_api_client.py` | Reusable read-only HTTP client |
| `app/tools.py` | MCP tool registration and handlers |
| `app/server.py` | FastMCP entry point |
| `tests/` | Network-free automated tests |

## Technology

- Python 3.10+
- Official MCP Python SDK (`mcp`) with FastMCP
- Transport: **MCP Streamable HTTP** (ADR 5), path `/mcp`
- Optional local transport: `stdio` via `MCP_TRANSPORT=stdio`
- HTTP client: **httpx** with an explicit timeout
- Tests: **pytest** with `httpx.MockTransport` and injectable fakes

## MCP tools (read-only)

### `list_products`

List products from `GET /api/v1/products`.

**Inputs** (all optional, official API parameters only):

| Parameter | Type | Notes |
| --- | --- | --- |
| `q` | string | Text search |
| `category` | string | Exact category |
| `supplier_id` | string | Exact supplier id |
| `include_discontinued` | boolean | Default false on the API side |
| `min_price` | number | Finite non-negative minimum unit price |
| `max_price` | number | Finite non-negative maximum; must be >= `min_price` |
| `limit` | integer | Page size from 1 to 100 |
| `offset` | integer | Pagination offset |
| `sort` | string | Official field, e.g. `name`, `-unit_price` |

**Successful output:**

```json
{
  "status": "success",
  "data": {
    "count": 1,
    "limit": 20,
    "offset": 0,
    "results": [ { "id": 1, "sku": "HB-LAP-1001", "name": "..." } ]
  }
}
```

An empty `results` array is a valid success (no products matched), not a failure.

### `get_product_details`

Retrieve one product from `GET /api/v1/products/{id_or_sku}`.

**Input:**

| Parameter | Type | Notes |
| --- | --- | --- |
| `id_or_sku` | string or integer | Numeric id (`1` or `"1"`) or SKU (`"HB-LAP-1001"`) |

**Successful output:**

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "sku": "HB-LAP-1001",
    "name": "Holberton Student Laptop 14",
    "supplier": { "id": "SUP-HBT-001", "name": "Holberton Tools Co." }
  }
}
```

The tool never invents a product and never fills missing catalog fields.

## Structured errors

```json
{
  "status": "error",
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product not found."
  }
}
```

| Code | When |
| --- | --- |
| `PRODUCT_NOT_FOUND` | Official API returns HTTP 404 |
| `INVALID_PRODUCT_REFERENCE` | Empty, whitespace-only, non-positive, or unsafe id/SKU |
| `PRODUCT_API_UNAVAILABLE` | Connection failure or HTTP 5xx |
| `PRODUCT_API_TIMEOUT` | Client timeout exceeded |
| `INVALID_PRODUCT_RESPONSE` | Unexpected HTTP status or invalid/malformed JSON |
| `INVALID_ARGUMENT` | Invalid list argument (e.g. non-positive limit) |
| `INTERNAL_ERROR` | Unexpected handler failure (no stack trace returned) |

Server-side logs may include exception types for operators. Tool results never
include secrets, stack traces, or credentials.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `PRODUCT_API_URL` | `http://localhost:5001` | Base URL of the official Product API |
| `PRODUCT_API_TIMEOUT` | `5.0` | HTTP timeout in seconds |
| `MCP_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` in Docker) |
| `MCP_PORT` | `8001` | Listen port |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio` |
| `MCP_LOG_LEVEL` | `INFO` | Logging level |

URL examples for `PRODUCT_API_URL`:

| Caller location | Value |
| --- | --- |
| Process on the host | `http://localhost:5001` |
| Container → host-published API | `http://host.docker.internal:5001` |
| Container on the Compose network | `http://external-products-api:${HBN_PRODUCTS_PORT:-5000}` |

The Product MCP Server container uses `PRODUCT_API_URL_DOCKER` when it is
explicitly set. Otherwise, Compose derives its internal URL as
`http://external-products-api:${HBN_PRODUCTS_PORT:-5000}`. This keeps the MCP
upstream URL aligned with the Product API container port without confusing it
with `PRODUCT_API_HOST_PORT`, which is the separately published host port.

## Installation

From the monorepo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r product_mcp_server/requirements.txt
```

## Start the External Product API

```bash
docker compose up --build -d external-products-api
curl -sS http://localhost:5001/health
```

## Start the Product MCP Server (local process)

```bash
export PRODUCT_API_URL=http://localhost:5001
export PRODUCT_API_TIMEOUT=5.0
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_TRANSPORT=streamable-http
python -m product_mcp_server.app.server
```

Health check:

```bash
curl -sS http://localhost:8001/health
```

## Start with Docker Compose

```bash
docker compose up --build -d external-products-api product-mcp-server
docker compose ps
curl -sS http://localhost:8001/health
```

Service dependencies:

- `product-mcp-server` waits until `external-products-api` is healthy;
- `product-mcp-server` has **no** PostgreSQL environment variables;
- existing `external-products-api` and `postgres` services remain unchanged in behaviour.

## Manual tests

### 1. External Product API health

```bash
curl -sS -i http://localhost:5001/health
```

### 2. Product MCP Server health

```bash
curl -sS -i http://localhost:8001/health
```

### 3. Inspect tools with MCP Inspector (optional, npx)

MCP Inspector is optional and is **not** a project dependency. Requires Node.js
with `npx` available:

```bash
npx -y @modelcontextprotocol/inspector
```

In the Inspector UI:

1. Select `Streamable HTTP` and connect to `http://localhost:8001/mcp`.
2. List tools — expect only `list_products` and `get_product_details`.
3. Call `list_products` with `{ "limit": 2 }`.
4. Call `get_product_details` with `{ "id_or_sku": "1" }`.
5. Call `get_product_details` with `{ "id_or_sku": "HB-LAP-1001" }`.
6. Call `get_product_details` with `{ "id_or_sku": "999999" }` → `PRODUCT_NOT_FOUND`.
7. Call `get_product_details` with `{ "id_or_sku": "" }` → `INVALID_PRODUCT_REFERENCE`.

The same checks can be run directly with the Inspector CLI:

```bash
# Inspect the read-only tool surface.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/list

# List two products.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name list_products \
  --tool-arg limit=2

# Retrieve a product by numeric id or SKU.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_details \
  --tool-arg id_or_sku=1
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_details \
  --tool-arg id_or_sku=HB-LAP-1001

# Controlled errors: unknown product, then empty identifier.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_details \
  --tool-arg id_or_sku=999999
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_details \
  --tool-arg 'id_or_sku='
```

### 4. Product API intentionally unavailable

Stop the API and call a tool:

```bash
docker compose stop external-products-api
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name list_products
# Expected tool error code: PRODUCT_API_UNAVAILABLE.
docker compose start external-products-api
```

### 5. Confirm read-only surface

```bash
# No write tools are registered. Official Product API rejects writes:
curl -sS -i -X POST http://localhost:5001/api/v1/products
```

## Automated tests

```bash
# from monorepo root, with dependencies installed
python -m pytest product_mcp_server/tests -v
```

Tests use:

- `httpx.MockTransport` for the real `ProductApiClient`;
- `FakeProductApiClient` for tool handlers and FastMCP `call_tool`;
- no real network access.

Covered scenarios include successful list/detail, empty list, SKU lookup,
validated filters and response shapes, not found, invalid identifiers,
connection errors, timeouts, unexpected HTTP status, invalid JSON, MCP tool
registration, controlled error propagation, and absence of write tools.

## Limits of this task

- stock MCP tools are not implemented;
- AI Query Service / agent is not implemented;
- Backoffice authentication and routes are out of scope;
- no local `Product` table and no catalog persistence;
- MCP protocol-level transport integration with a live AI client is left to a
  later task; unit tests cover tool logic and FastMCP registration/call paths.

## Confirmations

- **Read-only:** only `list_products` and `get_product_details` are exposed.
- **No local product storage:** the server never writes to PostgreSQL and has
  no database configuration.
- **Official routes only:** `GET /api/v1/products` and
  `GET /api/v1/products/{id_or_sku}`.
