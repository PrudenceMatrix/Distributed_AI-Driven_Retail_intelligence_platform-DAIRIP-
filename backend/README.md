# DAIRIP — Distributed AI-Driven Retail Intelligence Platform

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Spin up the full stack
docker compose up --build

# 3. Seed the database (new terminal)
docker compose exec backend python seed.py

# 4. Open API docs
open http://localhost:8000/docs
```

## Default Credentials (after seeding)

| Role    | Email                  | Password       |
|---------|------------------------|----------------|
| Admin   | admin@dairip.com       | Admin1234!     |
| Manager | manager@dairip.com     | Manager1234!   |

## Core API Flow

### 1. Login
```
POST /api/v1/auth/login
form: username=admin@dairip.com&password=Admin1234!
→ returns JWT token
```

### 2. Receive Stock
```
POST /api/v1/inventory/receive
Authorization: Bearer <token>
{
  "product_id": "<uuid>",
  "branch_id": "branch-001",
  "quantity": 50
}
```

### 3. Sell Item
```
POST /api/v1/inventory/sell
X-Idempotency-Key: <unique-uuid-per-transaction>
{
  "product_id": "<uuid>",
  "branch_id": "branch-001",
  "quantity": 2,
  "unit_price": 1.50,
  "order_id": "<order-uuid>"
}
```

### 4. View Event History
```
GET /api/v1/events/aggregate/{product_id}
```

### 5. Replay Projections
```
POST /api/v1/inventory/replay
```

## Architecture

```
POS/Client
    ↓
FastAPI (REST)
    ↓
Service Layer (business rules + stock validation)
    ↓
Event Store (MySQL append-only)
    ↓
Event Dispatcher
    ├── Projection Handlers (updates inventory read model)
    └── Redis Pub/Sub (async consumers)
```
