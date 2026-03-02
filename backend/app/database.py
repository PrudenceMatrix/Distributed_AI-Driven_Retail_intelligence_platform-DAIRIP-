from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    from app.models.product import Product                        # noqa: F401
    from app.models.user import User                              # noqa: F401
    from app.models.event_store import EventStore                 # noqa: F401
    from app.models.inventory import InventoryProjection          # noqa: F401
    from app.models.forecast import DemandForecast, IdempotencyKey, PricingRule  # noqa: F401
    from app.models.order import Order, OrderItem  # noqa: F401
    Base.metadata.create_all(bind=engine)