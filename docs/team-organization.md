# Team Organization

## Team members

- Sébastien Lamblin
- Ulysse Dewaleyne

## Responsibilities

### Sébastien — Backoffice and interfaces

Sébastien is responsible for:

- the relational database schema;
- SQLAlchemy models;
- initial database data;
- authentication and secure password storage;
- role and branch authorization;
- stock management;
- administrator user management;
- Backoffice templates and static files;
- the public interface inside the AI service;
- Backoffice tests.

Main ownership:

- `backoffice/`;
- `ai_service/app/templates/`;
- `ai_service/app/static/`.

### Ulysse — Infrastructure, Product API, MCP, and AI

Ulysse is responsible for:

- Docker Compose;
- inspecting and testing the official external Product API;
- implementing the HBntory HTTP client later in the development phase;
- handling Product API timeouts, connection failures, HTTP errors, and invalid responses;
- the Product MCP Server;
- connecting product MCP tools to the official API;
- product and stock MCP tools;
- the AI Query Service;
- the AI agent and MCP connection;
- product, stock, branch, and shopping-list questions;
- MCP and AI tests.

The official Product API is an external dependency. Ulysse integrates it with HBntory but is not responsible for developing or modifying it.

Main ownership:

- `product_mcp_server/`;
- the AI backend in `ai_service/`;
- `docker-compose.yml`.

## Shared responsibilities

Both team members participate in:

- architecture decisions;
- MVP definition;
- contracts between services;
- Pull Request reviews;
- service integration;
- end-to-end tests;
- README maintenance;
- the final presentation and demonstration.

## Git workflow

- Never push directly to `main`.
- Use one branch per Issue.
- Open a Pull Request for every feature.
- The other team member reviews the Pull Request.
- An Issue is Done only after its Pull Request is merged into `main`.
- Never commit secrets or local `.env` files.
