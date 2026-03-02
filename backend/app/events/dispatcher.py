import json
import logging
from typing import Callable
from sqlalchemy.orm import Session

from app.models.event_store import EventStore
from app.events.types import EventType

logger = logging.getLogger(__name__)

# Registry: event_type -> list of handler functions
_handlers: dict[str, list[Callable]] = {}


def register_handler(event_type: EventType):
    """
    Decorator to register a projection handler for an event type.

    Usage:
        @register_handler(EventType.ITEM_SOLD)
        def handle_item_sold(event: EventStore, db: Session):
            ...
    """
    def decorator(fn: Callable):
        key = event_type.value
        if key not in _handlers:
            _handlers[key] = []
        _handlers[key].append(fn)
        logger.debug(f"Registered handler {fn.__name__} for {key}")
        return fn
    return decorator


class EventDispatcher:
    """
    Dispatches persisted events to:
    1. In-process projection handlers (synchronous, same transaction)
    2. Redis pub/sub channel (async, for future consumers)
    """

    def __init__(self):
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis
                from app.config import get_settings
                settings = get_settings()
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis not available, skipping pub/sub: {e}")
        return self._redis

    def dispatch(self, stored_event: EventStore, db: Session) -> None:
        """
        Dispatch a stored event to all registered handlers and Redis.
        Call this AFTER the event has been persisted and before commit.
        """
        event_type = stored_event.event_type
        handlers = _handlers.get(event_type, [])

        for handler in handlers:
            try:
                handler(stored_event, db)
            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} failed for event "
                    f"{stored_event.id} ({event_type}): {e}"
                )
                raise  # re-raise to trigger rollback

        self._publish_to_redis(stored_event)

    def _publish_to_redis(self, stored_event: EventStore) -> None:
        """Non-blocking Redis publish. Failure here does NOT roll back the transaction."""
        r = self._get_redis()
        if r is None:
            return
        try:
            message = json.dumps({
                "event_id": stored_event.id,
                "event_type": stored_event.event_type,
                "aggregate_id": stored_event.aggregate_id,
                "aggregate_type": stored_event.aggregate_type,
                "branch_id": stored_event.branch_id,
                "version": stored_event.version,
                "payload": json.loads(stored_event.payload),
                "created_at": stored_event.created_at.isoformat(),
            })
            r.publish("dairip:events", message)
        except Exception as e:
            logger.warning(f"Redis publish failed (non-critical): {e}")


# Singleton instance
event_dispatcher = EventDispatcher()