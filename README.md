# HBntory — Inventory Management Platform

HBntory is a two-week inventory management project. It combines an internal stock-management Backoffice with a public, stateless AI question interface. Product details remain in a read-only external Product API, while local PostgreSQL data contains only users, branches, product identifiers, and stock quantities.

## Team members

- Sébastien Lamblin
- Ulysse Dewaleyne

## Current status

> The External Product API, database foundation, Backoffice authentication and authorization, and Product MCP Server product/stock tools are available. Backoffice management pages and AI features are developed separately.

## Architecture summary

The monorepo contains three main application blocks:

- the **Backoffice Service**, built with Flask, Jinja, SQLAlchemy, PostgreSQL, and Flask-Login;
- the **Product MCP Server**, which exposes controlled product and read-only stock tools;
- the **AI Query Service**, built with FastAPI, which hosts one AI agent and the public web interface.

The external Product API is the source of truth for product information. The MCP server reads local stock through a narrow SQLAlchemy repository backed by PostgreSQL. It exposes fixed read-only contracts and never accepts arbitrary SQL. Docker Compose currently orchestrates the Product API, PostgreSQL, and Product MCP Server; later tasks add the Backoffice and AI service containers.

## Target repository structure

This tree describes the project target. The repository implements it incrementally as Issues are completed.

```text
hbntory-inventory-platform/
├── backoffice/
│   ├── app/
│   │   ├── templates/
│   │   └── static/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── product_mcp_server/
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── ai_service/
│   ├── app/
│   │   ├── templates/
│   │   └── static/
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── database.md
│   ├── api-contracts.md
│   ├── mvp.md
│   ├── team-organization.md
│   └── test-plan.md
├── .github/
│   └── pull_request_template.md
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── docker-compose.yml
└── README.md
```

## Main decisions

- use one monorepo for the three application blocks;
- use Flask and Jinja server-side rendering for the Backoffice;
- use session authentication with Flask-Login;
- use PostgreSQL through SQLAlchemy for local relational data;
- serve the public interface from the FastAPI AI service;
- use REST for independent public questions;
- connect the AI service to MCP with Streamable HTTP;
- extend the existing MCP server with controlled SQLAlchemy stock queries instead of exposing a generic database MCP.

## Documentation

- [Architecture](docs/architecture.md)
- [Technical decisions](docs/decisions.md)
- [MVP scope](docs/mvp.md)
- [Conceptual database schema](docs/database.md)
- [API and MCP contracts](docs/api-contracts.md)
- [Team organization](docs/team-organization.md)
- [Test plan](docs/test-plan.md)
- [External Product API Docker foundation](docs/external-product-api.md)
- [Product MCP Server](product_mcp_server/README.md)

## External dependency

HBntory consumes the official read-only External Product API:
[hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api).

The API must be available before running the complete Backoffice, MCP, and AI flow. Its base URL is configured with `PRODUCT_API_URL`. See [API and MCP contracts](docs/api-contracts.md) for the supported execution URLs and official endpoints.

Full Docker procedure and validation notes: [docs/external-product-api.md](docs/external-product-api.md).

## Setup — External Product API

### Prerequisites

- Docker Engine with Compose (`docker compose` or `docker-compose`)
- Network access to GitHub (the official API is built from its public repository)
- `curl` for manual checks

### Configuration

```bash
cp .env.example .env
```

Do not commit `.env`. Important variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PRODUCT_API_URL` | `http://localhost:5001` | Base URL for future HBntory clients |
| `PRODUCT_API_HOST_PORT` | `5001` | Host port published by Compose |
| `HBN_PRODUCTS_PORT` | `5000` | Listen port inside the API container |
| `HBN_PRODUCTS_LATENCY_MS` | `0` | Optional simulated base latency |

### Start

```bash
docker compose up --build -d external-products-api
```

### Check status

```bash
docker compose ps
docker compose logs external-products-api
curl -sS http://localhost:5001/health
```

### Manual API tests

```bash
# List products
curl -sS "http://localhost:5001/api/v1/products?limit=2"

# Existing product by id
curl -sS http://localhost:5001/api/v1/products/1

# Existing product by SKU
curl -sS http://localhost:5001/api/v1/products/HB-LAP-1001

# Unknown product → HTTP 404
curl -sS -i http://localhost:5001/api/v1/products/999999
```

### Stop

```bash
docker compose down
```

Official routes used by this foundation:

- `GET /health`
- `GET /api/v1/products`
- `GET /api/v1/products/{id_or_sku}`

The catalog is read-only. HBntory never stores product metadata from this API in PostgreSQL.

## Product MCP Server (product and stock tools)

Product tools (`list_products`, `get_product_details`) consume the official Product API through an internal httpx client. Stock tools (`get_product_stock`, `get_branch_stock`, `check_shopping_list`) use fixed, read-only SQLAlchemy queries against local branch and stock tables. Full setup, manual tests, and limits: [product_mcp_server/README.md](product_mcp_server/README.md).

```bash
# Install MCP server dependencies
pip install -r product_mcp_server/requirements.txt

# Start API + MCP via Compose
docker compose up --build -d external-products-api product-mcp-server
curl -sS http://localhost:8001/health

# Or run MCP on the host against the published API
export PRODUCT_API_URL=http://localhost:5001
export DATABASE_URL='postgresql+psycopg://hbntory:<local-password>@localhost:5432/hbntory'
export MCP_PORT=8001
python -m product_mcp_server.app.server

# Automated tests (no network)
python -m pytest product_mcp_server/tests -v
```

## Contributing

Development uses a GitHub Flow workflow:

- one branch per Issue;
- no direct push to `main`;
- one Pull Request per feature;
- review by the other team member;
- squash merge after validation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete workflow.
