# Test Plan

This plan identifies the critical MVP scenarios. Exact test files and tools will be selected during implementation.

## Backoffice and database scenarios

| Scenario | Expected result |
| --- | --- |
| Add a positive integer quantity to stock. | The correct branch/product stock increases by that amount. |
| Remove a valid positive integer quantity. | The correct stock decreases without becoming negative. |
| Remove more units than are available. | The operation is rejected and the stored quantity is unchanged. |
| Try to create any negative stock state. | Validation or a database constraint prevents it. |
| Submit zero, a negative number, or a non-integer as an adjustment. | The operation is rejected with a clear validation error. |
| A common user accesses stock from another branch. | Access is denied and no data is changed. |
| An administrator creates a common user assigned to a branch. | The user is created with the correct role and branch. |
| A common user attempts to manage users. | Access is denied. |
| Soft-delete a user. | The record remains stored with `is_deleted` set. |
| A soft-deleted user attempts to sign in. | Authentication is refused. |
| An administrator attempts a stock operation. | The operation is denied. |
| The Backoffice displays a product. | Product details come from the external Product API and are not stored locally. |

## Official Product API integration scenarios

| Scenario | Expected result |
| --- | --- |
| Call `GET /health`. | The official API health endpoint is available before the full flow starts. |
| Retrieve `GET /api/v1/products`. | The product list is returned and can be consumed by HBntory. |
| Retrieve a product by numeric ID. | `GET /api/v1/products/1` returns the matching product. |
| Retrieve a product by SKU. | `GET /api/v1/products/HB-LAP-1001` returns the matching product. |
| Retrieve an unknown product. | HTTP `404` and the official structured `not_found` error are handled. |
| Receive an empty product list. | HBntory reports an empty result without failing or inventing products. |
| Use `simulate_delay_ms=750`. | The future client handles the slow response within its explicit timeout policy. |
| Use `force_error=true`. | The forced API error becomes a controlled HBntory error. |
| Stop or disconnect the API. | Connection failure becomes a controlled unavailable-service error. |
| Exceed the explicit client timeout. | A controlled timeout error is returned. |
| Receive invalid or unexpected JSON. | The response is rejected safely with a controlled format error. |
| Complete a product-backed stock operation. | Only the canonical numeric `external_product_id` is persisted locally. |
| Change external product metadata. | Local stock remains unchanged and independent from catalog metadata. |
| Inspect PostgreSQL after product use. | No product name, SKU, price, image, or other metadata was persisted. |

## MCP scenarios

| Scenario | Expected result |
| --- | --- |
| Call `list_products`. | MCP returns products supplied by `GET /api/v1/products`. |
| Call `list_products` with no matches. | Structured success with an empty `results` list (not an error). |
| Call `get_product_details` with a numeric ID. | MCP returns the matching external product details. |
| Call `get_product_details` with a SKU. | MCP resolves and returns the matching external product details. |
| Call `get_product_details` for an unknown product. | Structured `PRODUCT_NOT_FOUND` error; no invented product. |
| Call `get_product_details` with an empty or invalid id. | Structured `INVALID_PRODUCT_REFERENCE` error without calling the API when possible. |
| Product API connection failure or timeout. | Structured `PRODUCT_API_UNAVAILABLE` or `PRODUCT_API_TIMEOUT`; never a silent empty list. |
| Invalid JSON or unexpected HTTP from Product API. | Structured `INVALID_PRODUCT_RESPONSE`. |
| Call `get_product_stock` for stock in several branches. | MCP returns positive quantities, branch identities, and the correct total. |
| Call `get_product_stock` with no positive stock. | Structured `STOCK_NOT_FOUND`; zero quantities are never presented as available. |
| Call `get_branch_stock` by id or exact case-insensitive name. | MCP returns only external product identifiers and positive quantities. |
| Call `get_branch_stock` for an existing empty branch. | Structured success with an empty `stocks` list. |
| Call `get_branch_stock` for an unknown branch. | Structured `BRANCH_NOT_FOUND`. |
| Call `check_shopping_list` with duplicate products. | Validated duplicate quantities are merged before calculation. |
| Check a list satisfied by one or several single branches. | Every candidate is stable and ordered by branch id. |
| Check a list that needs several branches. | MCP returns the deterministic per-branch/per-product plan. |
| Check an impossible or partially missing list. | `fulfillable` is false; the partial plan and exact missing quantities are returned. |
| Pass booleans, nulls, strings, zero, negatives, malformed items, or an empty list. | Structured `INVALID_ARGUMENT`; no query uses caller-provided SQL. |
| Stop PostgreSQL and call a stock tool. | Structured `DATABASE_UNAVAILABLE` without SQL, credentials, or traceback. |
| Return malformed data from an injected repository. | Structured `INVALID_STOCK_RESPONSE`. |
| Inspect MCP `tools/list`. | Product tools and the three stock tools are present; no write or SQL tool exists. |
| Call stock tools through Streamable HTTP. | `tools/call` returns the same stable success/error contracts. |
| Attempt to change stock or products through MCP. | No write tool or write endpoint is available. |
| Automated Product MCP tests. | Pass with fakes/SQLite and without a real Product API or PostgreSQL service. |

## AI and public interface scenarios

| Scenario | Expected result |
| --- | --- |
| Ask where a known product is available. | The AI identifies branches using MCP product and stock results. |
| Ask for products available in one branch. | The AI lists only products grounded in MCP results. |
| Submit a simple shopping list for one branch. | The AI reports whether each requested quantity is available. |
| Ask about an unknown product. | The response clearly states that the product was not found. |
| Make the Product API unavailable. | The response clearly states that product information is unavailable. |
| Submit an incomplete or ambiguous question. | The response states that information is insufficient and does not guess. |
| Submit two consecutive questions. | Each question is processed independently without conversation history. |
| Submit a question from the public page. | A loading state is shown, followed by an answer or a clear error. |

## Integration and security checks

- verify the full Docker Compose flow when implementation exists;
- verify that the Product MCP Server receives its PostgreSQL URL only through environment configuration;
- verify that the stock repository contains only fixed SQLAlchemy `SELECT` queries;
- verify that no generic SQL, write-stock, branch-management, or user-management MCP tool is exposed;
- verify that API responses and logs do not expose passwords, session secrets, or internal tokens;
- verify the complete public flow: browser → FastAPI → MCP → Product API/PostgreSQL → grounded answer.

## MVP completion criteria

- all mandatory critical scenarios pass;
- no role can perform an operation forbidden by the architecture;
- stock cannot become negative;
- the AI does not invent products, product details, branches, or quantities;
- external service failures return clear, structured errors.
