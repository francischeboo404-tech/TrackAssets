import json
import time
import queue
import threading
from datetime import datetime, timedelta
from app import db
from app.models.event import SystemEvent


class EventBus:
    """Event Bus with DB persistence and in-memory pub/sub fallback for tests."""

    def __init__(self):
        self._subscribers = []
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def _notify_subscribers(self, msg):
        with self._lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(msg)
                except Exception:
                    pass

    def publish(self, event_type, data, organisation_id=None):
        """Publish an event: persist to DB when available, and notify in-memory subscribers."""
        # Attempt DB persistence; if it fails (e.g., tests mocking db), fall back.
        try:
            event = SystemEvent(
                event_type=event_type, data=data, organisation_id=organisation_id
            )
            db.session.add(event)
            db.session.commit()
            try:
                self._notify_subscribers(event.to_dict())
            except Exception:
                # If event.to_dict isn't available, send a simple payload
                self._notify_subscribers({"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()})
        except Exception:
            # In-memory fallback for test environments or DB failures
            self._notify_subscribers({"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()})

    def stream(self, organisation_id=None):
        """Streaming generator that polls for events. SSE compatible.

        Uses a fresh SQLAlchemy session per poll cycle so it does not
        hold the request-level session open across the entire stream lifetime.
        """
        from flask import current_app
        from sqlalchemy.orm import scoped_session, sessionmaker

        last_id = 0
        last_check = datetime.utcnow() - timedelta(seconds=5)

        # Send an immediate heartbeat so the browser knows the connection is alive
        yield ": heartbeat\n\n"

        while True:
            try:
                # Create a fresh, short-lived session for each poll
                SessionFactory = scoped_session(
                    sessionmaker(bind=db.engine, expire_on_commit=False)
                )
                poll_session = SessionFactory()

                try:
                    query = poll_session.query(SystemEvent).filter(
                        SystemEvent.created_at >= last_check
                    )
                    if organisation_id:
                        query = query.filter(
                            (SystemEvent.organisation_id == organisation_id)
                            | (SystemEvent.organisation_id.is_(None))
                        )
                    if last_id > 0:
                        query = query.filter(SystemEvent.id > last_id)

                    events = query.order_by(SystemEvent.id.asc()).limit(50).all()

                    for event in events:
                        try:
                            payload = {
                                "id": event.id,
                                "type": event.event_type,
                                "data": event.data,
                                "organisation_id": event.organisation_id,
                                "timestamp": event.created_at.isoformat() if event.created_at else None,
                            }
                            yield f"data: {json.dumps(payload)}\n\n"
                        except Exception:
                            pass
                        last_id = event.id
                        last_check = event.created_at

                finally:
                    poll_session.close()
                    SessionFactory.remove()

            except GeneratorExit:
                # Client disconnected — stop streaming cleanly
                return
            except Exception:
                # Any DB error → send heartbeat to keep connection alive
                yield ": heartbeat\n\n"

            time.sleep(2)


# Global singleton
event_bus = EventBus()
