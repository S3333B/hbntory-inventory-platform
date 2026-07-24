# Product MCP Server

Read-only MCP boundary between the future HBntory AI Query Service, the
official External Product API, and local branch stock.

Responsible: Ulysse.

## Role and security boundary

The server exposes five tools over MCP Streamable HTTP:

- `list_products`;
- `get_product_details`;
- `get_product_stock`;
- `get_branch_stock`;
- `check_shopping_list`.

Product tools call the official read-only catalog with `httpx`. Stock tools
execute fixed SQLAlchemy `SELECT` queries against the existing `Branch` and
`Stock` models. The server never stores product catalog metadata.

The stock tools are intended for the AI Query Service, not Backoffice users.
They do not apply the Backoffice `admin`/`common` roles. This is safe because
their public surface is strictly read-only: no stock, branch, or user write
operation exists, and no caller can provide SQL, table names, columns, or query
fragments. Authenticated Backoffice operations remain a separate boundary.

Extending this internal server is preferred to a generic database MCP because
it provides:

- a limited access surface;
- no arbitrary SQL;
- stable contracts for the agent;
- centralized input and response validation;
- deterministic, network-free tests;
- a clear split between public read tools and authenticated Backoffice writes.

Tool results never expose database URLs, SQL/driver messages, tracebacks,
password hashes, deleted users, session data, tokens, or secrets.

## Architecture

```text
AI Query Service / MCP Inspector
              |
              | MCP Streamable HTTP (/mcp)
              v
       Product MCP Server
          /           \
         /             \
 ProductApiClient    Stock repository
   httpx GET only    SQLAlchemy SELECT only
       |                  |
 External Product API  PostgreSQL
```

| Module | Responsibility |
| --- | --- |
| `app/config.py` | Environment settings |
| `app/exceptions.py` | Product API errors |
| `app/product_api_client.py` | Read-only External Product API client |
| `app/db.py` | Shared engine/session construction |
| `app/stock_exceptions.py` | Stable stock-query errors |
| `app/stock_repository.py` | Fixed, parameterized SQLAlchemy reads |
| `app/stock_query.py` | Validation and deterministic allocation |
| `app/stock_tools.py` | MCP adapters for stock queries |
| `app/tools.py` | MCP adapters for product queries |
| `app/server.py` | FastMCP registration, health route, and startup |

The repository imports the existing Backoffice declarative models without
calling the Flask app factory or depending on a Flask request/session.

## Technology

- Python 3.10+
- official MCP Python SDK (`mcp`) with FastMCP
- MCP Streamable HTTP at `/mcp`
- optional local `stdio` transport
- SQLAlchemy 2.x and Psycopg 3
- httpx
- pytest with fakes, `httpx.MockTransport`, and isolated SQLite

## Tool contracts

Every successful tool result uses:

```json
{
  "status": "success",
  "data": {}
}
```

Every controlled error uses:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "A safe, stable message."
  }
}
```

### `list_products`

Signature:

```text
list_products(
  q=None, category=None, supplier_id=None,
  include_discontinued=None, min_price=None, max_price=None,
  limit=None, offset=None, sort=None
)
```

Calls `GET /api/v1/products`. It preserves the official paginated product
shape. An empty result is a valid success.

### `get_product_details`

Signature:

```text
get_product_details(id_or_sku: str | int)
```

Calls `GET /api/v1/products/{id_or_sku}` and returns only official catalog data.

### `get_product_stock`

Signature:

```text
get_product_stock(product_id: int)
```

Example success:

```json
{
  "status": "success",
  "data": {
    "external_product_id": 1,
    "total_quantity": 8,
    "branches": [
      {"branch_id": 1, "branch_name": "Lille", "quantity": 5},
      {"branch_id": 2, "branch_name": "Roubaix", "quantity": 3}
    ]
  }
}
```

`product_id` must be a strictly positive integer; booleans are rejected.
Branches are ordered by id. Zero quantities are omitted. A product with no
positive local stock returns `STOCK_NOT_FOUND`.

### `get_branch_stock`

Signature:

```text
get_branch_stock(branch: str | int)
```

`branch` is either a positive branch id or a non-empty branch name. Name
matching trims whitespace and uses a case-insensitive exact comparison.

```json
{
  "status": "success",
  "data": {
    "branch_id": 1,
    "branch_name": "Lille",
    "stocks": [
      {"external_product_id": 1, "quantity": 5}
    ]
  }
}
```

An existing branch without positive stock returns an empty `stocks` list.
An unknown branch returns `BRANCH_NOT_FOUND`. No product name, price,
description, image, or other catalog metadata is read from PostgreSQL.

### `check_shopping_list`

Signature:

```text
check_shopping_list(items: list[ShoppingListItem])
ShoppingListItem = {"product_id": int, "quantity": int}
```

The list must be non-empty. Both fields must be strictly positive integers;
booleans, nulls, strings, zero, negatives, missing fields, and malformed
elements are rejected. Duplicate product ids are validated and summed.

Output fields:

- `requested_items`: normalized, merged items ordered by product id;
- `single_branch_possible`: whether one branch can satisfy the whole list;
- `single_branch_candidates`: every matching branch ordered by id;
- `multi_branch_possible`: whether cumulative stock is sufficient when no
  single branch qualifies;
- `fulfillable`: whether the complete list can be supplied;
- `fulfillment_plan`: allocations grouped by branch and product;
- `missing_items`: exact requested, available, and missing quantities.

Allocation is deterministic:

1. merge duplicate product ids;
2. find all complete single-branch candidates in ascending branch-id order;
3. if none exists, process products in ascending product-id order;
4. for each product, use branches by quantity descending, then branch id
   ascending as a stable tie-breaker;
5. retain a safe partial plan when cumulative stock is insufficient and mark
   the result `fulfillable: false`.

This algorithm is stable and always detects cumulative per-product
sufficiency. It does not optimize travel distance or the globally smallest
number of branches.

## Error codes

| Code | Meaning |
| --- | --- |
| `PRODUCT_NOT_FOUND` | Official API returned 404 |
| `INVALID_PRODUCT_REFERENCE` | Invalid product id/SKU for catalog detail |
| `PRODUCT_API_UNAVAILABLE` | Catalog connection or HTTP 5xx failure |
| `PRODUCT_API_TIMEOUT` | Catalog request exceeded the configured timeout |
| `INVALID_PRODUCT_RESPONSE` | Unexpected catalog status or body |
| `INVALID_ARGUMENT` | Invalid product, branch, list, item, or quantity |
| `BRANCH_NOT_FOUND` | No branch matches the id or exact name |
| `STOCK_NOT_FOUND` | No positive local stock exists for the product |
| `DATABASE_UNAVAILABLE` | The stock database cannot be queried |
| `INVALID_STOCK_RESPONSE` | Internal stock records failed safe validation |
| `INTERNAL_ERROR` | Unexpected failure without internal details |

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `PRODUCT_API_URL` | `http://localhost:5001` | Official Product API base URL |
| `PRODUCT_API_TIMEOUT` | `5.0` | Product API timeout in seconds |
| `DATABASE_URL` | none | Required at process startup for stock tools |
| `MCP_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` in Docker) |
| `MCP_PORT` | `8001` | Listen port |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio` |
| `MCP_LOG_LEVEL` | `INFO` | Logging level |

In Compose, `PRODUCT_API_URL_DOCKER` overrides the catalog URL. Otherwise it is
derived from `HBN_PRODUCTS_PORT`. `DATABASE_URL_DOCKER` similarly overrides
the in-network PostgreSQL URL; otherwise Compose derives it from `POSTGRES_*`
and the `postgres:5432` service address. Host ports are not container ports.

## Installation and demo data

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backoffice/requirements.txt \
  -r product_mcp_server/requirements.txt
```

Start PostgreSQL, create the schema, and initialize demo rows:

```bash
export POSTGRES_PASSWORD='<local-password>'
docker compose up -d --wait postgres
export DATABASE_URL='postgresql+psycopg://hbntory:<local-password>@localhost:5432/hbntory'
read -rsp 'Initial admin password: ' INITIAL_ADMIN_PASSWORD
echo
export INITIAL_ADMIN_PASSWORD
python -m backoffice.scripts.create_schema
python -m backoffice.scripts.init_db
unset INITIAL_ADMIN_PASSWORD
```

Replace `<local-password>` with the same local value configured as
`POSTGRES_PASSWORD`. The password is entered without terminal echo and is not
printed by the initializer.

## Start and health check

Host process:

```bash
export PRODUCT_API_URL=http://localhost:5001
export DATABASE_URL='postgresql+psycopg://hbntory:<local-password>@localhost:5432/hbntory'
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_TRANSPORT=streamable-http
python -m product_mcp_server.app.server
```

Compose:

```bash
docker compose up --build -d --wait \
  postgres external-products-api product-mcp-server
docker compose ps
curl -sS http://localhost:8001/health
```

The health route is a liveness check and reports whether stock tools were
registered. Individual stock calls report database availability.

## Manual MCP Inspector checks

MCP Inspector is optional and is not a project dependency. The real service
uses Streamable HTTP:

```bash
npx -y @modelcontextprotocol/inspector
```

In the UI, select **Streamable HTTP**, connect to
`http://localhost:8001/mcp`, inspect `tools/list`, and call the five tools.

Equivalent CLI commands:

```bash
# List the five tools.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/list

# Product stock across branches.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_stock \
  --tool-arg product_id=1

# Branch by id, then by exact name.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_branch_stock \
  --tool-arg branch=1
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_branch_stock \
  --tool-arg branch=Lille

# Shopping list (duplicate product ids are summed).
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name check_shopping_list \
  --tool-arg 'items=[{"product_id":1,"quantity":1},{"product_id":1,"quantity":2}]'

# Unknown branch and product without stock.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_branch_stock \
  --tool-arg branch=Unknown
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_stock \
  --tool-arg product_id=999999

# Impossible list.
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name check_shopping_list \
  --tool-arg 'items=[{"product_id":1,"quantity":999999}]'
```

Database failure:

```bash
docker compose stop postgres
npx -y @modelcontextprotocol/inspector --cli http://localhost:8001/mcp \
  --transport http --method tools/call --tool-name get_product_stock \
  --tool-arg product_id=1
# Expected structured code: DATABASE_UNAVAILABLE
docker compose start postgres
```

## Automated tests

```bash
python -m pytest product_mcp_server/tests -v
python -m pytest backoffice/tests -v
python -m compileall -q backoffice product_mcp_server
python -m pip check
docker compose config --quiet
```

Product client tests use `httpx.MockTransport`; stock logic uses an injected
fake repository; repository tests use isolated SQLite. Tests do not require a
real Product API or PostgreSQL service.

## Current limits

- the AI Query Service and agent are not implemented here;
- no Backoffice stock-management page or write operation is added;
- no Product table or product catalog persistence exists;
- the shopping plan is deterministic, not route- or distance-optimized;
- MCP service authentication/network isolation must be finalized with the AI
  deployment;
- schema evolution still needs a future migration solution beyond
  `Base.metadata.create_all()`.
