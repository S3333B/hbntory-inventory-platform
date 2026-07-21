# Architecture

## Overview

HBntory is a monorepo with three main application blocks: the Backoffice Service, the Product MCP Server, and the AI Query Service. PostgreSQL stores local business data. The official read-only [hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api) service remains the source of truth for the product catalog.

The public web interface is part of the AI Query Service. It is not a separate Docker service. Docker Compose will eventually run PostgreSQL, the external Product API, the Backoffice, the MCP server, and the AI service.

## Target repository structure

This is the target structure. The project implements it incrementally without creating empty application files in advance.

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
├── docker-compose.yml
└── README.md
```

## Components and responsibilities

### Backoffice Service

Planned technologies: Python, Flask, Jinja, SQLAlchemy, PostgreSQL, Flask-Login, and Werkzeug PBKDF2 password hashing.

Responsibilities:

- authenticate internal users and manage sessions;
- enforce administrator and common-user roles;
- manage branches, users, and stock according to role permissions;
- retrieve product display data from the external Product API;
- render the internal interface on the server with Jinja;
- expose controlled, read-only internal stock endpoints for MCP.

Authorization and business rules:

- a common user belongs to exactly one branch and manages only that branch's stock;
- a common user cannot manage users;
- an administrator can manage users but cannot perform stock operations;
- deleted users use soft delete and cannot sign in;
- stock quantity can never be negative;
- stock additions and removals accept positive integers only.

### Relational Database

PostgreSQL stores only users, branches, stock quantities, and the canonical numeric external product identifier in `external_product_id`. Product names, SKU values, descriptions, prices, images, and external metadata are never copied into the local database.

### External Product API

The official [External Product API repository](https://github.com/hbtn-edu/hbntory-products-api) is an independent, already-developed dependency. It is read-only, belongs to the product catalog domain, and must not be modified or copied into HBntory. It can be started separately with the Docker Compose configuration provided in its own repository.

The API supplies product identifiers, SKU values, names, descriptions, categories, brands, suppliers, prices, currencies, tags, discontinued status, and product metadata. It does not supply stock quantities, reserved units, available quantities, reorder thresholds, storage locations, or branch stock. HBntory owns all stock data in PostgreSQL.

Both the Backoffice and Product MCP Server consume this API. They must read its base URL from `PRODUCT_API_URL` because the correct value depends on the execution mode:

| Execution mode | `PRODUCT_API_URL` |
| --- | --- |
| API started from its own repository and accessed from the host | `http://localhost:5001` |
| HBntory containers access an API exposed separately on the host | `http://host.docker.internal:5001` |
| All services directly share the API's Docker network | `http://external-products-api:5000` |

The future HTTP client must use an explicit timeout and convert slow responses, network timeouts, unavailable services, forced HTTP errors, and invalid JSON into controlled errors. This client is not implemented during Task 0.

### Product MCP Server

Planned technologies: Python, the MCP Python SDK, FastMCP, and MCP Streamable HTTP between containers.

The server exposes only these required tools:

- `list_products`;
- `get_product_details`;
- `get_stock_by_product`;
- `get_branch_stock`;
- `check_shopping_list`.

It reads products from the official external Product API and reads stock from controlled Backoffice endpoints. It returns structured errors, never modifies the Product API or stock, persists no catalog data, and has no direct SQL access to PostgreSQL.

### AI Query Service and public interface

Planned technologies: Python, FastAPI, one AI agent, and an MCP Streamable HTTP client.

FastAPI serves `GET /` for the public page and `POST /api/questions` for questions. The page assets live under `ai_service/app/templates/` and `ai_service/app/static/`. The browser uses REST; no WebSocket is required.

Each request is independent and has no conversation history. The agent calls only the MCP tools it needs, grounds its answer in tool results, never invents product data or quantities, and clearly reports unavailable or insufficient information.

The public page contains only a question field, a submit button, a loading indicator, a response area, and a clear error message.

### Docker Compose

Docker Compose currently defines PostgreSQL and the official Product API without modifying the external source. Backoffice, MCP, and AI services will be added in later tasks. The Product API may either share a Docker network or run separately with its own provided Docker Compose configuration.

## Data ownership

| Data | Source of truth | Consumers |
| --- | --- | --- |
| Users and roles | PostgreSQL through the Backoffice | Backoffice only |
| Branches | PostgreSQL through the Backoffice | Backoffice and MCP through internal endpoints |
| Stock quantities | PostgreSQL through the Backoffice | Backoffice and MCP through internal endpoints |
| Canonical numeric `external_product_id` | PostgreSQL stock records | Backoffice and MCP |
| Product catalog and metadata | Official External Product API | Backoffice and MCP |

## Backoffice data flow

1. An internal user opens the Backoffice.
2. Flask authenticates the user with a session.
3. The backend checks the user's role and branch authorization.
4. SQLAlchemy reads or changes local data in PostgreSQL.
5. The Backoffice retrieves product details from the external Product API when needed for display.
6. The backend validates every operation before saving it.

## Public interface data flow

1. An anonymous user opens the page served by FastAPI.
2. The browser sends one question with `POST /api/questions`.
3. The AI agent analyses the independent question.
4. The agent calls the required Product MCP Server tools over Streamable HTTP.
5. MCP retrieves product data from the external Product API.
6. MCP retrieves stock through read-only internal Backoffice endpoints.
7. The agent creates an answer based only on the returned data.
8. FastAPI returns the response to the browser.

## Architecture diagram

```mermaid
flowchart LR
    BackofficeBrowser[Backoffice Browser] -->|HTTP + session| Backoffice[Backoffice Service<br/>Flask + Jinja + SQLAlchemy]
    Backoffice -->|SQL read/write| PostgreSQL[(PostgreSQL<br/>local users, branches,<br/>external IDs and stock only)]
    Backoffice -->|REST read-only products| ProductAPI[External Product API]

    PublicBrowser[Public Browser] -->|GET / and POST /api/questions<br/>REST| AI[AI Query Service<br/>FastAPI + public interface]
    AI -->|MCP Streamable HTTP| MCP[Product MCP Server<br/>FastMCP]
    MCP -->|REST read-only products| ProductAPI
    MCP -->|Internal REST<br/>read-only stock| Backoffice
```
