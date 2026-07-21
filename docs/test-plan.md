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
| Call `get_product_details` with a numeric ID. | MCP returns the matching external product details. |
| Call `get_product_details` with a SKU. | MCP resolves and returns the matching external product details. |
| Call `get_stock_by_product`. | MCP returns stock through the read-only Backoffice endpoint. |
| Call `get_branch_stock`. | MCP returns the branch stock without direct database access. |
| Call `check_shopping_list` with positive quantities. | MCP reports availability for every requested item. |
| Attempt to change stock through MCP. | No write tool or write endpoint is available. |

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
- verify that the Product MCP Server has no PostgreSQL credentials;
- verify that internal stock endpoints require service authentication;
- verify that internal stock endpoints expose read-only operations only;
- verify that API responses and logs do not expose passwords, session secrets, or internal tokens;
- verify the complete public flow: browser → FastAPI → MCP → Product API/Backoffice → grounded answer.

## MVP completion criteria

- all mandatory critical scenarios pass;
- no role can perform an operation forbidden by the architecture;
- stock cannot become negative;
- the AI does not invent products, product details, branches, or quantities;
- external service failures return clear, structured errors.
