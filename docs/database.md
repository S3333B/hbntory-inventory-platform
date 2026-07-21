# Conceptual Database Schema

This document describes the planned data model only. No SQLAlchemy model is implemented during Task 0.

## User

| Field | Purpose |
| --- | --- |
| `id` | Unique user identifier. |
| `username` | Unique sign-in name. |
| `password_hash` | PBKDF2 password hash; never a plain-text password. |
| `role` | Either `admin` or `common`. |
| `branch_id` | Assigned branch; nullable only for the administrator. |
| `is_deleted` | Soft-delete flag. A deleted user cannot sign in. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last update timestamp. |

## Branch

| Field | Purpose |
| --- | --- |
| `id` | Unique branch identifier. |
| `name` | Branch name. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last update timestamp. |

## Stock

| Field | Purpose |
| --- | --- |
| `id` | Unique stock-record identifier. |
| `branch_id` | Branch that owns the quantity. |
| `external_product_id` | Canonical numeric product identifier supplied by the external Product API. |
| `quantity` | Current non-negative quantity. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last update timestamp. |

## Relationships

- one `Branch` can have many common `User` records;
- every common `User` belongs to exactly one `Branch`;
- the administrator has no branch stock responsibility;
- one `Branch` can have many `Stock` records;
- every `Stock` record belongs to exactly one `Branch`;
- `external_product_id` is an integer obtained from the external Product API;
- `external_product_id` is not a SQL foreign key because no external `Product` table exists in HBntory PostgreSQL.

## Constraints

- `User.username` is unique;
- `User.role` is limited to `admin` or `common`;
- a common user must have a non-null `branch_id`;
- the administrator does not manage stock and does not require a branch assignment;
- `Stock.quantity` is greater than or equal to zero;
- the pair `Stock.branch_id + Stock.external_product_id` is unique;
- stock additions and removals must use positive integer amounts;
- soft-deleted users cannot authenticate;
- there is no local `Product` table.

## Product data boundary

PostgreSQL must not store product names, SKU values, descriptions, prices, images, or other Product API metadata. When a user selects a product by SKU, HBntory resolves it through the official API and stores only its canonical numeric `external_product_id`.

Allowed local stock representation:

```json
{
  "branch_id": 2,
  "external_product_id": 1,
  "quantity": 12
}
```

```mermaid
erDiagram
    BRANCH ||--o{ USER : assigns
    BRANCH ||--o{ STOCK : contains

    USER {
        int id PK
        string username UK
        string password_hash
        string role
        int branch_id FK
        boolean is_deleted
        datetime created_at
        datetime updated_at
    }

    BRANCH {
        int id PK
        string name
        datetime created_at
        datetime updated_at
    }

    STOCK {
        int id PK
        int branch_id FK
        int external_product_id
        int quantity
        datetime created_at
        datetime updated_at
    }
```
