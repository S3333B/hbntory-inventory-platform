# API and MCP Contracts

These contracts document the official Product API, the implemented Product MCP product/stock tools, and the planned public AI endpoint. The official catalog contract is defined by the [API repository](https://github.com/hbtn-edu/hbntory-products-api), its [README](https://github.com/hbtn-edu/hbntory-products-api/blob/main/README.md), and its [API contract](https://github.com/hbtn-edu/hbntory-products-api/blob/main/docs/api_contract.md).

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

The Product MCP Server `ProductApiClient` handles an empty product list, HTTP `404`, temporary unavailability, slow responses, explicit network timeouts, forced HTTP errors, and invalid or unexpected JSON. It uses `PRODUCT_API_TIMEOUT` and returns controlled HBntory errors (`PRODUCT_API_UNAVAILABLE`, `PRODUCT_API_TIMEOUT`, `INVALID_PRODUCT_RESPONSE`, `PRODUCT_NOT_FOUND`, `INVALID_PRODUCT_REFERENCE`). It never silently returns an empty list on connection failure.

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
- `503 DEPENDENCY_UNAVAILABLE` when MCP or its stock database cannot be reached;
- `500 INTERNAL_ERROR` for an unexpected failure, with no internal detail exposed.

An unknown product should normally produce a grounded successful answer such as “Product 999 was not found.” If the calling flow needs an error, it uses `404 PRODUCT_NOT_FOUND` consistently.

## Internal stock-query boundary

Stock is not exposed as a public REST or generic database API. The Product MCP Server imports the shared SQLAlchemy `Branch` and `Stock` mappings and executes a fixed set of parameterized `SELECT` queries. The future AI service sees only the MCP contracts below.

The boundary is intentionally limited:

- no caller-provided SQL, table, column, filter expression, or ordering;
- no create, add, remove, update, delete, branch-management, or user-management operation;
- no `User` query and no password, soft-delete, session, secret, or database URL in results;
- no locally stored product names, descriptions, prices, images, or metadata;
- database and malformed-response failures are converted to stable public errors.

These service tools do not apply the Backoffice `admin` and `common` roles. Those roles protect authenticated Backoffice operations. MCP is instead constrained to the three read-only stock capabilities documented below.

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

- **Status:** implemented by the Product MCP Server (Task 4).
- **Input:** optional official Product API search, filter, or pagination parameters: `q`, `category`, `supplier_id`, `include_discontinued`, `min_price`, `max_price`, `limit`, `offset`, `sort`.
- **Output:** structured success with the official paginated shape (`count`, `limit`, `offset`, `results`).
- **Errors:** `PRODUCT_API_UNAVAILABLE`, `PRODUCT_API_TIMEOUT`, `INVALID_PRODUCT_RESPONSE`, `INVALID_ARGUMENT`.

### `get_product_details`

- **Status:** implemented by the Product MCP Server (Task 4).
- **Input:** `{ "id_or_sku": "1" }` or `{ "id_or_sku": "HB-LAP-1001" }`.
- **Output:** structured success with the official product object (detail may include nested `supplier`).
- **Errors:** `PRODUCT_NOT_FOUND`, `PRODUCT_API_UNAVAILABLE`, `PRODUCT_API_TIMEOUT`, `INVALID_PRODUCT_RESPONSE`, `INVALID_PRODUCT_REFERENCE`.

### `get_product_stock`

- **Signature:** `get_product_stock(product_id: int)`.
- **Input:** `{ "product_id": 12 }`; booleans, null, strings, zero, and negative values are invalid.
- **Output:**

```json
{
  "status": "success",
  "data": {
    "external_product_id": 12,
    "total_quantity": 8,
    "branches": [
      {
        "branch_id": 1,
        "branch_name": "Lille",
        "quantity": 5
      },
      {
        "branch_id": 2,
        "branch_name": "Roubaix",
        "quantity": 3
      }
    ]
  }
}
```

Only positive quantities are listed. No positive stock returns `STOCK_NOT_FOUND`.

### `get_branch_stock`

- **Signature:** `get_branch_stock(branch: str | int)`.
- **Input:** `{ "branch": 2 }` or `{ "branch": "Lille" }`. Names use a trimmed, case-insensitive exact match.
- **Output:**

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

An existing empty branch returns a successful empty `stocks` list. An unknown branch returns `BRANCH_NOT_FOUND`. Product details are not joined into this stock result.

### `check_shopping_list`

- **Signature:** `check_shopping_list(items: list[ShoppingListItem])`, where `ShoppingListItem` contains `product_id: int` and `quantity: int`.
- **Input:** a non-empty list of strictly positive integer identifiers and quantities:

```json
{
  "items": [
    {
      "product_id": 12,
      "quantity": 3
    },
    {
      "product_id": 12,
      "quantity": 2
    }
  ]
}
```

Duplicate products are merged after validation; the request above becomes quantity `5` for product `12`.

- **Output:**

```json
{
  "status": "success",
  "data": {
    "requested_items": [
      {
        "product_id": 12,
        "quantity": 5
      }
    ],
    "single_branch_possible": false,
    "single_branch_candidates": [],
    "multi_branch_possible": true,
    "fulfillable": true,
    "fulfillment_plan": [
      {
        "branch_id": 1,
        "branch_name": "Lille",
        "items": [
          {
            "product_id": 12,
            "quantity": 3
          }
        ]
      },
      {
        "branch_id": 2,
        "branch_name": "Roubaix",
        "items": [
          {
            "product_id": 12,
            "quantity": 2
          }
        ]
      }
    ],
    "missing_items": []
  }
}
```

The deterministic algorithm first returns every complete single-branch candidate ordered by `branch_id`. If none exists, it processes products by ascending identifier and allocates from branches by quantity descending, then `branch_id` ascending. An impossible request returns `fulfillable: false`, preserves the safe partial plan, and reports `requested_quantity`, `available_quantity`, and `missing_quantity`.

### Stock tool errors

| Code | Meaning |
| --- | --- |
| `INVALID_ARGUMENT` | Invalid product, branch, list, item, or quantity shape. |
| `BRANCH_NOT_FOUND` | No branch matches the supplied id or exact name. |
| `STOCK_NOT_FOUND` | No positive stock exists for the requested product. |
| `DATABASE_UNAVAILABLE` | The configured stock database cannot be queried. |
| `INVALID_STOCK_RESPONSE` | Internal stock records failed safe validation. |
| `INTERNAL_ERROR` | An unexpected error occurred; no internal detail is returned. |

## Required failure behaviour

- **Unknown product:** return `PRODUCT_NOT_FOUND` or clearly state that the product was not found; never invent its name.
- **Product API unavailable:** return `PRODUCT_API_UNAVAILABLE`; do not use guessed or stale product details.
- **Insufficient information:** return `INSUFFICIENT_INFORMATION` and explain which input is missing or ambiguous.
- **Unknown quantity:** clearly state that availability cannot be confirmed; never invent stock.
- **Partial shopping-list failure:** identify the affected item and do not claim that the full list is available.
