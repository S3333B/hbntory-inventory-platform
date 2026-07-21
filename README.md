# HBntory — Inventory Management Platform

HBntory is a two-week inventory management project. It combines an internal stock-management Backoffice with a public, stateless AI question interface. Product details remain in a read-only external Product API, while local PostgreSQL data contains only users, branches, product identifiers, and stock quantities.

## Team members

- Sébastien Lamblin
- Ulysse Dewaleyne

## Current status

> Docker foundation for the official External Product API is available on this branch. Backoffice, database, MCP, and AI features are developed separately.

## Architecture summary

The monorepo contains three main application blocks:

- the **Backoffice Service**, built with Flask, Jinja, SQLAlchemy, PostgreSQL, and Flask-Login;
- the **Product MCP Server**, which exposes controlled product and read-only stock tools;
- the **AI Query Service**, built with FastAPI, which hosts one AI agent and the public web interface.

The external Product API is the source of truth for product information. The MCP server reads stock through controlled Backoffice endpoints and never connects directly to PostgreSQL. Docker Compose will eventually orchestrate all services.

## Target repository structure

This tree describes the project target. Files such as Dockerfiles, requirements files, Python modules, and `docker-compose.yml` are intentionally not created during Task 0.

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
- give MCP read-only stock access through controlled Backoffice endpoints.

## Documentation

- [Architecture](docs/architecture.md)
- [Technical decisions](docs/decisions.md)
- [MVP scope](docs/mvp.md)
- [Conceptual database schema](docs/database.md)
- [API and MCP contracts](docs/api-contracts.md)
- [Team organization](docs/team-organization.md)
- [Test plan](docs/test-plan.md)
- [External Product API Docker foundation](docs/external-product-api.md)

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

## Contributing

Development uses a GitHub Flow workflow:

- one branch per Issue;
- no direct push to `main`;
- one Pull Request per feature;
- review by the other team member;
- squash merge after validation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete workflow.
