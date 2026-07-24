# Architecture Decision Records

## ADR 1 — Monorepo

- **Decision:** one repository contains the Backoffice Service, Product MCP Server, and AI Query Service.
- **Main advantage:** collaboration, documentation, and integration are simpler.
- **Main limitation:** the team must avoid simultaneous changes to shared root files.

## ADR 2 — Server-side rendering for the Backoffice

- **Decision:** use Flask and Jinja to render the Backoffice on the server.
- **Main advantage:** the interface is simple to develop and directly connected to backend authorization.
- **Main limitation:** it is less dynamic than a separate frontend application.

## ADR 3 — REST for the public interface

- **Decision:** expose `GET /` and `POST /api/questions` from FastAPI.
- **Main advantage:** every question is independent, so REST is sufficient and easy to test.
- **Main limitation:** responses are not streamed in real time.

## ADR 4 — Public interface inside the AI service

- **Decision:** FastAPI serves the public templates and static files.
- **Main advantage:** the architecture needs one fewer service and container.
- **Main limitation:** the public frontend is tied to the AI service deployment.

## ADR 5 — MCP with Streamable HTTP

- **Decision:** the AI service communicates with the Product MCP Server through MCP Streamable HTTP.
- **Main advantage:** both components can run in separate containers.
- **Main limitation:** an additional internal network connection must be configured and tested.

## ADR 6 — Controlled stock access

- **Decision:** extend the existing internal Product MCP Server with a narrow SQLAlchemy repository that exposes only fixed branch and stock reads. Do not expose PostgreSQL through a generic database MCP or accept caller-provided SQL.
- **Main advantage:** the agent receives stable, validated contracts over a limited access surface with no arbitrary SQL, while deterministic repository and allocation tests remain independent from Flask.
- **Main limitation:** the MCP container needs read access to PostgreSQL and the team must maintain the explicit query contracts when the schema evolves.

## ADR 7 — Session authentication

- **Decision:** use Flask-Login and session cookies for the Backoffice.
- **Main advantage:** session authentication fits a server-rendered Backoffice.
- **Main limitation:** the Backoffice must protect the session configuration and secret key correctly.

## ADR 8 — PostgreSQL

- **Decision:** use PostgreSQL through SQLAlchemy for local data.
- **Main advantage:** a reliable relational database supports the constraints required for stock management.
- **Main limitation:** PostgreSQL adds another Docker service to operate.

## ADR 9 — External Product API remains an independent read-only dependency

- **Choice:** HBntory consumes the official [hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api) service without modifying or copying it.
- **Benefits:** this creates a clear ownership boundary, avoids catalog-data duplication, and complies with the project requirements.
- **Trade-offs:** HBntory depends on a network service, needs explicit timeouts and controlled error handling, and may temporarily have no product information when the API is unavailable.

## ADR 10 — Store the canonical numeric external product identifier

- **Choice:** each local stock record stores only the integer `external_product_id` returned by the official API. A SKU selected by a user is resolved through the API before the numeric identifier is saved.
- **Benefits:** stock keeps a stable catalog reference without duplicating SKU values or product metadata.
- **Trade-offs:** displaying or resolving a product requires the external API, and `external_product_id` cannot be enforced as a SQL foreign key because there is no local `Product` table.

## ADR 11 — Stock tools resolve exact branch references

- **Choice:** `get_branch_stock` resolves either a positive numeric identifier or a case-insensitive exact branch name through the controlled stock repository.
- **Benefits:** users can refer to branches naturally, identifiers and names still come from authoritative HBntory rows, and no additional public tool or arbitrary lookup is required.
- **Trade-offs:** only exact normalized names are accepted; an unknown or ambiguous user phrase must be clarified by the future AI service.

## ADR 12 — Initial schema creation uses SQLAlchemy metadata

- **Choice:** Task 1 uses SQLAlchemy 2.x directly and `Base.metadata.create_all()` to bootstrap new databases. No Alembic dependency is introduced yet.
- **Benefits:** the first schema is reproducible with the minimum dependency set and remains independent from Flask routes or application startup.
- **Trade-offs:** `create_all()` is not a migration system and cannot safely evolve an existing schema. A versioned migration tool must be selected before later schema changes.

## ADR 13 — Product MCP Server uses official MCP SDK + Streamable HTTP + httpx

- **Choice:** implement the Product MCP Server with the official Python MCP SDK (`mcp` / FastMCP), transport **Streamable HTTP** on path `/mcp`, and an internal **httpx** `ProductApiClient` for the External Product API. Default process port is `8001`.
- **Benefits:** matches ADR 5 for container-to-container AI → MCP communication; avoids a hand-rolled MCP protocol; httpx provides explicit timeouts and a mockable transport for network-free tests; tool handlers accept an injectable client.
- **Trade-offs:** Streamable HTTP requires a reachable HTTP port and Compose networking; stdio remains available via `MCP_TRANSPORT=stdio` for local experiments but is not the production path between containers.
- **Scope reminder:** product tools remain unchanged; the stock-query task adds three read-only tools to the same server. AI integration remains separate.

## ADR 14 — Product MCP Compose service uses in-network Product API URL

- **Choice:** the `product-mcp-server` Compose service derives `PRODUCT_API_URL` from `HBN_PRODUCTS_PORT` and the `external-products-api` service name unless `PRODUCT_API_URL_DOCKER` explicitly overrides it. It never reuses a host-oriented `PRODUCT_API_URL=http://localhost:5001`.
- **Benefits:** containers reach the official API by Compose DNS without depending on published host ports; local host clients keep using `localhost:5001`.
- **Trade-offs:** two related variables must stay documented so developers do not point the MCP container at `localhost` by mistake.

## ADR 15 — Deterministic shopping-list allocation

- **Choice:** merge duplicate requested products, test every branch for complete fulfillment, then allocate each remaining product greedily by available quantity descending with `branch_id` ascending as the tie-breaker.
- **Benefits:** results are stable, explainable, and easy to test; the algorithm always detects cumulative per-product sufficiency because products have no shared capacity constraint.
- **Trade-offs:** the plan is deterministic rather than globally optimized for the fewest branches or travel distance.
