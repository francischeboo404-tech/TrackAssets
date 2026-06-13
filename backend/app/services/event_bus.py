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
        """Streaming generator that polls for events. SSE compatible."""
        # Initial offset
        last_check = datetime.utcnow()
        last_id = 0

        while True:
            # Re-scoping session to get fresh data
            try:
                db.session.expire_all()
            except Exception:
                pass

            # Polling logic: fetch events newer than last check
            query = SystemEvent.query.filter(
                SystemEvent.created_at >= last_check - timedelta(seconds=5)
            )

            if organisation_id:
                query = query.filter(
                    (SystemEvent.organisation_id == organisation_id)
                    | (SystemEvent.organisation_id == None)
                )

            if last_id > 0:
                query = query.filter(SystemEvent.id > last_id)

            events = query.order_by(SystemEvent.id.asc()).limit(50).all()

            for event in events:
                yield f"data: {json.dumps(event.to_dict())}\n\n"
                last_id = event.id
                last_check = event.created_at

            # Sleep to prevent high DB load
            time.sleep(1)


# Global singleton
event_bus = EventBus()
