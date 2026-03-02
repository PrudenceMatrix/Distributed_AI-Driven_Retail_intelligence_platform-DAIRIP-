import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_all_tables
from app.core.exceptions import (
    ConcurrencyConflictError,
    InsufficientStockError,
    ProductNotFoundError,
)

# Import projection handlers so they register via @register_handler decorator
import app.projections.inventory_projection  # noqa: F401

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}...")
    create_all_tables()
    logger.info("Database tables verified/created.")
    yield
    logger.info(f"{settings.APP_NAME} shutting down.")


app = FastAPI(
    title="DAIRIP — Distributed AI-Driven Retail Intelligence Platform",
    description=(
        "Event-sourced retail backend with CQRS, demand forecasting, "
        "and automated perishable pricing optimization."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(ConcurrencyConflictError)
async def concurrency_conflict_handler(request: Request, exc: ConcurrencyConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InsufficientStockError)
async def insufficient_stock_handler(request: Request, exc: InsufficientStockError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ProductNotFoundError)
async def product_not_found_handler(request: Request, exc: ProductNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# ── Routers ───────────────────────────────────────────────────────────────────

from app.routers import auth, products, inventory, events  # noqa: E402

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}