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

## Project Structure

```
app/
├── main.py              # FastAPI app + startup
├── config.py            # Settings
├── database.py          # SQLAlchemy engine + session
├── models/              # SQLAlchemy ORM models
│   ├── product.py
│   ├── user.py
│   ├── event_store.py   # ← Core: append-only event log
│   ├── inventory.py     # ← Read model (projection)
│   └── forecast.py      # Demand forecasts + pricing rules
├── events/
│   ├── types.py         # Domain event definitions
│   ├── store.py         # EventStoreService (append + query)
│   └── dispatcher.py    # Routes events to handlers + Redis
├── projections/
│   └── inventory_projection.py  # Projection handlers
├── services/
│   └── inventory_service.py     # Business logic
├── routers/             # FastAPI route handlers
├── auth/                # JWT + RBAC
└── core/
    └── exceptions.py    # Domain exceptions
```

## Next Steps (implement during hackathon)
- [ ] AI demand forecasting endpoint (`/api/v1/forecast/{product_id}`)
- [ ] Perishable optimization engine (`/api/v1/perishable/optimize`)
- [ ] Multi-branch inventory summary
- [ ] Order aggregate + OrderCreated/Completed events
