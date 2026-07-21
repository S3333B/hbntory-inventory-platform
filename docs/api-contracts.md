# API and MCP Contracts

These contracts document the official Product API and propose HBntory service boundaries without implementing routes or tools. The official contract is defined by the [API repository](https://github.com/hbtn-edu/hbntory-products-api), its [README](https://github.com/hbtn-edu/hbntory-products-api/blob/main/README.md), and its [API contract](https://github.com/hbtn-edu/hbntory-products-api/blob/main/docs/api_contract.md).

## Official External Product API

The official API is an independent, read-only catalog dependency. HBntory must not modify it or persist its metadata locally. Stock is not part of this API.

### Base URL by execution mode

All HBntory consumers must use the `PRODUCT_API_URL` environment variable.

| Execution mode | Base URL |
| --- | --- |
| Official API started in its own repository and called from the host | `http://localhost:5001` |
| Containerized HBntory calls the separately exposed host API | `http://host.docker.internal:5001` |
| HBntory and the API directly share the same Docker network | `http://external-products-api:5000` |

### Official endpoints

| Method and path | Purpose | MVP requirement |
| --- | --- | --- |
| `GET /health` | Check API health. | Required for integration checks. |
| `GET /api/v1/products` | List and filter products. | Required. |
| `GET /api/v1/products/search?q=keyboard` | Search products. | Optional dedicated search endpoint. |
| `GET /api/v1/products/{id_or_sku}` | Retrieve one product by numeric ID or SKU. | Required. |
| `GET /api/v1/categories` | List categories. | Optional for the MVP. |
| `GET /api/v1/suppliers` | List suppliers. | Optional for the MVP. |

`GET /api/v1/products` accepts these main query parameters:

- `q` for a simple text search;
- `category` for a category filter;
- `supplier_id` for a supplier filter;
- `include_discontinued` to include discontinued products;
- `min_price` and `max_price` for a price range;
- `limit` and `offset` for pagination;
- `sort` for result ordering.

Advanced filters, categories, and suppliers are available but are not mandatory for the MVP.

### Official product example

```json
{
  "id": 1,
  "sku": "HB-LAP-1001",
  "name": "Holberton Student Laptop 14",
  "description": "Training catalog item for HBntory integration: holberton student laptop 14.",
  "category": "Laptops",
  "brand": "Holberton",
  "supplier_id": "SUP-HBT-001",
  "supplier_name": "Holberton Tools Co.",
  "unit_price": 799.0,
  "currency": "USD",
  "discontinued": false,
  "weight_kg": 1.35,
  "tags": ["student", "portable", "linux-ready"],
  "updated_at": "2026-05-22T12:00:00Z"
}
```

HBntory may display this response but stores only the numeric `id` as `external_product_id` in a local stock record.

### Official error and robustness scenarios

The official error format is:

```json
{
  "error": "not_found",
  "message": "Product not found."
}
```

An unknown product returns HTTP `404`. The API also provides these test scenarios:

- `GET /api/v1/products?simulate_delay_ms=750` simulates a slow response;
- `GET /api/v1/products?force_error=true` forces an HTTP error.

The future HTTP client must handle an empty product list, HTTP `404`, temporary unavailability, slow responses, explicit network timeouts, forced HTTP errors, and invalid or unexpected JSON. It must use an explicit timeout and return a controlled HBntory error. No HTTP client is implemented during Task 0.

## HBntory response shapes

### Successful REST response

```json
{
  "status": "success",
  "data": {}
}
```

The public question endpoint uses `answer` instead of `data`, as documented below.

### Error response

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "A clear message for the caller."
  }
}
```

Internal details, stack traces, credentials, and service tokens must never be returned.

## Public AI endpoint

### `POST /api/questions`

Accepts one independent question. No conversation identifier or history is accepted.

Request:

```json
{
  "question": "Which branch has 3 units of product 12?"
}
```

Successful response:

```json
{
  "status": "success",
  "answer": "The requested product is available in the Lille branch."
}
```

Validation rules:

- `question` is required;
- it must be a non-empty string after trimming;
- each request is processed independently;
- the answer must be based only on MCP tool results.

Suggested HTTP errors:

- `400 INVALID_REQUEST` for malformed JSON or an invalid field type;
- `422 INSUFFICIENT_INFORMATION` when the question does not contain enough information;
- `503 PRODUCT_API_UNAVAILABLE` when required product data cannot be reached;
- `503 DEPENDENCY_UNAVAILABLE` when MCP or the internal stock API cannot be reached;
- `500 INTERNAL_ERROR` for an unexpected failure, with no internal detail exposed.

An unknown product should normally produce a grounded successful answer such as “Product 999 was not found.” If the calling flow needs an error, it uses `404 PRODUCT_NOT_FOUND` consistently.

## Internal read-only stock endpoints

These endpoints are available only to the Product MCP Server on the internal Docker network. The proposed authentication mechanism is an `X-Internal-Token` header containing `INTERNAL_API_TOKEN`. The final mechanism requires team validation.

### `GET /internal/stocks/products/{external_product_id}`

Returns stock for one external product identifier across branches.

```json
{
  "status": "success",
  "data": {
    "external_product_id": 12,
    "branches": [
      {
        "branch_id": 2,
        "branch_name": "Lille",
        "quantity": 3
      }
    ]
  }
}
```

### `GET /internal/branches/{branch_id}/stocks`

Returns all stock records for one branch. Product details are not returned from the local database.

```json
{
  "status": "success",
  "data": {
    "branch_id": 2,
    "branch_name": "Lille",
    "stocks": [
      {
        "external_product_id": 12,
        "quantity": 3
      }
    ]
  }
}
```

Suggested internal errors:

- `401 INTERNAL_AUTH_REQUIRED` for a missing or invalid internal token;
- `404 BRANCH_NOT_FOUND` for an unknown branch;
- `400 INVALID_EXTERNAL_PRODUCT_ID` for an invalid external product identifier;
- `503 DATABASE_UNAVAILABLE` when stock data cannot be read.

Only `GET` operations are exposed. The MCP server cannot create, update, or delete stock.

## MCP tools

MCP tool failures use a structured result with a stable code and clear message:

```json
{
  "status": "error",
  "error": {
    "code": "PRODUCT_API_UNAVAILABLE",
    "message": "Product information is temporarily unavailable."
  }
}
```

### `list_products`

- **Input:** optional official Product API search, filter, or pagination parameters such as `q`, `limit`, and `offset`.
- **Output:** a list of products returned by the external Product API.
- **Errors:** `PRODUCT_API_UNAVAILABLE`, `PRODUCT_API_TIMEOUT`, `INVALID_PRODUCT_RESPONSE`, `INVALID_ARGUMENT`.

### `get_product_details`

- **Input:** `{ "id_or_sku": 1 }` or `{ "id_or_sku": "HB-LAP-1001" }`.
- **Output:** the official API details for the requested numeric ID or SKU.
- **Errors:** `PRODUCT_NOT_FOUND`, `PRODUCT_API_UNAVAILABLE`, `PRODUCT_API_TIMEOUT`, `INVALID_PRODUCT_RESPONSE`, `INVALID_PRODUCT_REFERENCE`.

### `get_stock_by_product`

- **Input:** `{ "external_product_id": 12 }`.
- **Output:** branch identifiers, branch names, and quantities for that product.
- **Errors:** `INVALID_EXTERNAL_PRODUCT_ID`, `STOCK_API_UNAVAILABLE`.

### `get_branch_stock`

- **Input:** `{ "branch_id": 2 }`.
- **Output:** the branch and its external product identifiers and quantities. Product details may be joined from the Product API by the MCP server.
- **Errors:** `BRANCH_NOT_FOUND`, `STOCK_API_UNAVAILABLE`, `PRODUCT_API_UNAVAILABLE` when product details are required.

### `check_shopping_list`

- **Input:** a branch identifier and a non-empty list of positive requested quantities:

```json
{
  "branch_id": 2,
  "items": [
    {
      "external_product_id": 12,
      "quantity": 3
    }
  ]
}
```

- **Output:** availability for each requested item and an overall availability result:

```json
{
  "status": "success",
  "branch_id": 2,
  "available": true,
  "items": [
    {
      "external_product_id": 12,
      "requested_quantity": 3,
      "available_quantity": 3,
      "available": true
    }
  ]
}
```

- **Errors:** `INSUFFICIENT_INFORMATION`, `BRANCH_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `STOCK_API_UNAVAILABLE`, `PRODUCT_API_UNAVAILABLE`.

## Required failure behaviour

- **Unknown product:** return `PRODUCT_NOT_FOUND` or clearly state that the product was not found; never invent its name.
- **Product API unavailable:** return `PRODUCT_API_UNAVAILABLE`; do not use guessed or stale product details.
- **Insufficient information:** return `INSUFFICIENT_INFORMATION` and explain which input is missing or ambiguous.
- **Unknown quantity:** clearly state that availability cannot be confirmed; never invent stock.
- **Partial shopping-list failure:** identify the affected item and do not claim that the full list is available.
