import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.event_store import EventStore
from app.models.user import User
from app.schemas import EventResponse
from app.auth import require_manager_or_above
from app.events.store import event_store_service

router = APIRouter(prefix="/events", tags=["Event Store"])


@router.get("/aggregate/{aggregate_id}", response_model=list[EventResponse])
def get_aggregate_events(
    aggregate_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
    from_version: int = 0,
):
    """Returns the full event history for a given aggregate (product/order)."""
    events = event_store_service.get_events_for_aggregate(db, aggregate_id, from_version)
    if not events:
        raise HTTPException(status_code=404, detail="No events found for this aggregate")

    return [
        EventResponse(
            id=e.id,
            aggregate_id=e.aggregate_id,
            aggregate_type=e.aggregate_type,
            event_type=e.event_type,
            payload=json.loads(e.payload),
            version=e.version,
            branch_id=e.branch_id,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get("/recent", response_model=list[EventResponse])
def get_recent_events(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_manager_or_above)],
    limit: int = 50,
    branch_id: str | None = None,
):
    """Returns the most recent events across the system."""
    stmt = select(EventStore).order_by(EventStore.created_at.desc()).limit(limit)
    if branch_id:
        stmt = stmt.where(EventStore.branch_id == branch_id)
    events = list(db.scalars(stmt).all())

    return [
        EventResponse(
            id=e.id,
            aggregate_id=e.aggregate_id,
            aggregate_type=e.aggregate_type,
            event_type=e.event_type,
            payload=json.loads(e.payload),
            version=e.version,
            branch_id=e.branch_id,
            created_at=e.created_at,
        )
        for e in events
    ]