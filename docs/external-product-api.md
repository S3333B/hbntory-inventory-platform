# External Product API — Docker foundation and validation

This document describes how to start the official read-only External Product API from the HBntory monorepo, how to test it, and what was validated on the foundation branch.

Responsible: Ulysse (Docker / Product API integration).
Out of scope: database models, migrations, Backoffice features, MCP implementation, AI service.

## Official dependency

| Item | Official value |
| --- | --- |
| Repository | [hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api) |
| Distribution mode | Docker Compose build from the official repository (no published registry image) |
| Compose service name | `external-products-api` |
| Container name | `hbntory-external-products-api` |
| Container port | `5000` (`HBN_PRODUCTS_PORT`) |
| Host port (default) | `5001` (`PRODUCT_API_HOST_PORT`) |
| Host base URL | `http://localhost:5001` |
| In-network base URL | `http://external-products-api:5000` |
| Access mode | Read-only (`GET` and `OPTIONS` only) |

HBntory must not modify this API, must not fork its catalog into the monorepo, and must not store product metadata in PostgreSQL. Only the numeric product `id` may later be stored as `external_product_id` in local stock records.

Official documentation:

- [README](https://github.com/hbtn-edu/hbntory-products-api/blob/main/README.md)
- [API contract](https://github.com/hbtn-edu/hbntory-products-api/blob/main/docs/api_contract.md)

## Prerequisites

- Docker Engine with the Compose plugin (`docker compose`) or the `docker-compose` CLI
- Network access to clone/build from GitHub (`https://github.com/hbtn-edu/hbntory-products-api.git`)
- `curl` for manual HTTP checks
- Optional: a local `.env` copied from `.env.example` (never commit `.env`)

## Configuration

1. From the monorepo root, copy the example environment file if needed:

```bash
cp .env.example .env
```

2. Relevant variables for this foundation:

| Variable | Purpose | Example |
| --- | --- | --- |
| `PRODUCT_API_URL` | Base URL used later by HBntory HTTP clients | `http://localhost:5001` |
| `PRODUCT_API_HOST_PORT` | Host port published by Compose | `5001` |
| `HBN_PRODUCTS_PORT` | Listen port inside the API container | `5000` |
| `HBN_PRODUCTS_LATENCY_MS` | Optional base latency simulation | `0` |

Docker Compose reads these values from the environment or from a local `.env` file. Defaults match the official asset pack when no override is provided.

## Start the API

From the monorepo root:

```bash
docker compose up --build -d external-products-api
```

Equivalent with the standalone CLI:

```bash
docker-compose up --build -d external-products-api
```

The first build clones the official repository and builds image `hbntory-external-products-api:local`. Later starts reuse the built image unless the remote context changes.

## Check container status

```bash
docker compose ps
docker compose logs external-products-api
```

Expected status: container `hbntory-external-products-api` is running (and healthy once the healthcheck succeeds).

Healthcheck uses the official endpoint `GET /health` with Python already present in the official image.

## Manual test commands

Replace `5001` if you changed `PRODUCT_API_HOST_PORT`.

### Health

```bash
curl -sS -i http://localhost:5001/health
```

Expected: HTTP `200` and JSON similar to:

```json
{
  "status": "ok",
  "products": <number>,
  "suppliers": <number>
}
```

### List products

```bash
curl -sS -i "http://localhost:5001/api/v1/products?limit=2"
```

Expected: HTTP `200` and JSON with `count`, `limit`, `offset`, and `results` (array of product objects).

### Product detail by numeric id

```bash
curl -sS -i http://localhost:5001/api/v1/products/1
```

Expected: HTTP `200` and one product object (includes nested `supplier` on detail).

### Product detail by SKU

```bash
curl -sS -i http://localhost:5001/api/v1/products/HB-LAP-1001
```

Expected: HTTP `200` for the matching catalog item.

### Unknown product

```bash
curl -sS -i http://localhost:5001/api/v1/products/999999
```

Expected: HTTP `404` and:

```json
{
  "error": "not_found",
  "message": "Product not found."
}
```

### Optional robustness probes (official)

```bash
curl -sS -i "http://localhost:5001/api/v1/products?simulate_delay_ms=750"
curl -sS -i "http://localhost:5001/api/v1/products?force_error=true"
```

### Confirm read-only behaviour

Only `GET` (and CORS `OPTIONS`) are accepted by the official API. Write methods are not part of the contract. Example negative check:

```bash
curl -sS -i -X POST http://localhost:5001/api/v1/products
```

Expected: not a successful catalog mutation (the official service does not implement product writes).

## Stop the environment

```bash
docker compose down
```

This stops and removes the API container. The built image may remain locally (`hbntory-external-products-api:local`).

To also remove the built image later:

```bash
docker image rm hbntory-external-products-api:local
```

## Official routes validated for the MVP

| Method and path | Purpose | Result expected |
| --- | --- | --- |
| `GET /health` | Health check | `200` + `status: ok` |
| `GET /api/v1/products` | List / filter products | `200` + paginated `results` |
| `GET /api/v1/products/{id}` | Detail by numeric id | `200` product or `404` |
| `GET /api/v1/products/{sku}` | Detail by SKU | `200` product or `404` |

Optional official routes (not required to start the foundation):

- `GET /api/v1/products/search?q=...`
- `GET /api/v1/categories`
- `GET /api/v1/suppliers`

## Connection URLs for future HBntory services

| Caller location | `PRODUCT_API_URL` |
| --- | --- |
| Process on the host | `http://localhost:5001` |
| Container calling the host-published port | `http://host.docker.internal:5001` |
| Container on the same Compose network | `http://external-products-api:5000` |

## Data ownership reminder

- Product catalog and metadata: official External Product API only.
- Stock quantities, branches, users: HBntory PostgreSQL (Sébastien / Backoffice), not this API.
- No product name, SKU, description, price, image, or tag is copied into HBntory storage by this foundation task.

## Validation log

Fill or update this section whenever the foundation is re-validated on a machine.

| Check | Command area | Status |
| --- | --- | --- |
| Compose config valid | `docker compose config` | See latest run notes below |
| Container starts | `docker compose up --build -d` | See latest run notes below |
| Container status | `docker compose ps` | See latest run notes below |
| Logs readable | `docker compose logs` | See latest run notes below |
| `GET /health` | curl | See latest run notes below |
| `GET /api/v1/products` | curl | See latest run notes below |
| `GET /api/v1/products/1` | curl | See latest run notes below |
| `GET /api/v1/products/999999` | curl | See latest run notes below |
| Clean stop | `docker compose down` | See latest run notes below |

### Latest run notes

Validated on branch `feat/docker-product-api-foundation` (2026-07-21) with Docker Engine 29.1.3 and Compose v5.1.4.

| Check | Result |
| --- | --- |
| `docker compose config` | Valid — service `external-products-api`, host port `5001` → container `5000` |
| `docker compose up --build -d` | Image `hbntory-external-products-api:local` built from official GitHub `main` and started |
| `docker compose ps` | Container `hbntory-external-products-api` **Up (healthy)** |
| `docker compose logs` | `HBntory External Product API running on http://0.0.0.0:5000` |
| `GET /health` | **200** — `{"status":"ok","products":40,"suppliers":5}` |
| `GET /api/v1/products?limit=2` | **200** — paginated list (`count`, `limit`, `offset`, `results`) |
| `GET /api/v1/products/1` | **200** — Holberton Student Laptop 14 (`HB-LAP-1001`) |
| `GET /api/v1/products/HB-LAP-1001` | **200** — same product resolved by SKU |
| `GET /api/v1/products/999999` | **404** — `{"error":"not_found","message":"Product not found."}` |
| `POST /api/v1/products` | **501 Unsupported method** — write not supported (read-only) |
| `Access-Control-Allow-Methods` | `GET, OPTIONS` only |
| `docker compose down` | Clean stop — container and network removed |

## Limitations

- No Docker Hub image is published by Holberton for this API; every environment builds from the official Git repository.
- The first start requires outbound network access to GitHub.
- This foundation intentionally starts only the External Product API. PostgreSQL, Backoffice, MCP, and AI services are out of scope for this task.
- Changing `HBN_PRODUCTS_PORT` requires keeping `PRODUCT_API_URL` / published ports consistent for callers.
