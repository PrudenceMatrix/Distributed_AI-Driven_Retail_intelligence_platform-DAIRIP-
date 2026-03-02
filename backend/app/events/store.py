import json
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.event_store import EventStore
from app.events.types import DomainEvent
from app.core.exceptions import ConcurrencyConflictError


class EventStoreService:
    """
    Handles appending domain events to the event store with optimistic concurrency control.
    This is the ONLY way state changes should enter the system.
    """

    def append(
        self,
        db: Session,
        event: DomainEvent,
        expected_version: int | None = None,
    ) -> EventStore:
        """
        Append a domain event to the store.

        Args:
            db: SQLAlchemy session
            event: The domain event to persist
            expected_version: If provided, raises ConcurrencyConflictError if the
                              current version doesn't match (optimistic locking).

        Returns:
            The persisted EventStore row.
        """
        current_version = self._get_current_version(db, event.aggregate_id)

        if expected_version is not None and current_version != expected_version:
            raise ConcurrencyConflictError(
                f"Concurrency conflict on aggregate {event.aggregate_id}. "
                f"Expected version {expected_version}, found {current_version}."
            )

        new_version = current_version + 1

        stored_event = EventStore(
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type.value,
            event_type=event.event_type.value,
            payload=json.dumps(event.payload),
            version=new_version,
            correlation_id=event.correlation_id,
            branch_id=event.branch_id,
            created_by=event.created_by,
            created_at=event.occurred_at,
        )

        db.add(stored_event)
        db.flush()  # get the ID without committing yet
        return stored_event

    def get_events_for_aggregate(
        self,
        db: Session,
        aggregate_id: str,
        from_version: int = 0,
    ) -> list[EventStore]:
        """Fetch all events for an aggregate, ordered by version."""
        stmt = (
            select(EventStore)
            .where(EventStore.aggregate_id == aggregate_id)
            .where(EventStore.version > from_version)
            .order_by(EventStore.version.asc())
        )
        return list(db.scalars(stmt).all())

    def get_all_events_ordered(
        self,
        db: Session,
        from_id: str | None = None,
    ) -> list[EventStore]:
        """
        Returns ALL events in chronological order.
        Used for full system replay.
        """
        stmt = select(EventStore).order_by(
            EventStore.created_at.asc(), EventStore.version.asc()
        )
        return list(db.scalars(stmt).all())

    def _get_current_version(self, db: Session, aggregate_id: str) -> int:
        """Returns the latest version number for an aggregate, or 0 if none exist."""
        stmt = select(func.max(EventStore.version)).where(
            EventStore.aggregate_id == aggregate_id
        )
        result = db.scalar(stmt)
        return result or 0


# Singleton instance
event_store_service = EventStoreService()