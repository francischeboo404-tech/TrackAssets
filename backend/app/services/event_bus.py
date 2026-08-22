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
        """Publish an event: persist to DB when available, and notify in-memory subscribers.

        The row is written through a short-lived session of the bus's own, bound
        to the same engine, and only that session is committed. It must never use
        ``db.session``: committing that would commit whatever business
        transaction the caller happens to have open, which both breaks atomicity
        and makes a ``@transaction_retry`` replay above the caller unsafe.

        Because this commits independently, an event becomes visible to SSE
        pollers the moment publish() returns. Callers that are mid-transaction
        should buffer their events and drain them after their own commit (see
        ``TrackingService.record_scan``).
        """
        # Attempt DB persistence; if it fails (e.g., tests mocking db), fall back.
        try:
           from sqlalchemy.orm import Session

            with Session(bind=db.engine, expire_on_commit=False) as pub_session:
                event = SystemEvent(
                    event_type=event_type, data=data, organisation_id=organisation_id
                )
                pub_session.add(event)
                pub_session.commit()
                try:
                    payload = event.to_dict()
                except Exception:
                    # If event.to_dict isn't available, send a simple payload
                    payload = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
        except Exception:
            # In-memory fallback for test environments or DB failures
            payload = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}

        self._notify_subscribers(payload)

    # Seconds between polls of the system_events table.
    POLL_INTERVAL_SECONDS = 2

    # Emit a comment line when nothing else has been written for this long.
    # Two jobs: it keeps intermediaries from cutting an idle connection (nginx
    # and Render both sit around 55-60s), and it gives the generator a write
    # that fails once the client is gone, so a closed tab terminates the
    # generator instead of polling the database forever.
    HEARTBEAT_SECONDS = 15

    def stream(self, organisation_id=None, last_event_id=None):
        """Streaming generator that polls for events. SSE compatible.

        ``last_event_id`` resumes delivery immediately after that event id, so a
        client reconnecting after an outage neither misses events nor replays
        ones it has already handled. With no cursor, a cold connect replays the
        last five seconds.


        Uses a fresh SQLAlchemy session per poll cycle so it does not
        hold the request-level session open across the entire stream lifetime.
        """
        from flask import current_app
       from sqlalchemy.orm import sessionmaker

        # Cursor tradeoff, deliberately accepted: an id-based cursor can skip a
        # row. If one transaction takes id 100 and another takes 101 but commits
        # first, a poll that observes 101 will never come back for 100. After
        # publish() moved to its own connection it is a single insert-and-commit,
        # so that window is sub-millisecond. If it ever bites in practice, hold
        # the cursor roughly one second behind the newest row — do not revert to
        # a time window, which loses events over any outage longer than it.
        last_id = last_event_id if last_event_id and last_event_id > 0 else 0
        last_check = datetime.utcnow() - timedelta(seconds=5)

        # Built once, not per poll. This used to be a scoped_session plus a
        # sessionmaker constructed and torn down every two seconds for every
        # connected client — pure overhead, plus the matching pool churn.
        SessionFactory = sessionmaker(bind=db.engine, expire_on_commit=False)

        # Send an immediate heartbeat so the browser knows the connection is alive
        yield ": heartbeat\n\n"

        last_write = time.monotonic()

        while True:
            try:
                # Short-lived session per poll, as before.
                poll_session = SessionFactory()

                try:
                    query = poll_session.query(SystemEvent)
                    if last_id > 0:
                        # A cursor is authoritative once we have one. The time
                        # window is only a cold-start heuristic: it re-delivers
                        # across a short reconnect and silently drops events
                        # across a long one.
                        query = query.filter(SystemEvent.id > last_id)
                    else:
                        query = query.filter(SystemEvent.created_at >= last_check)
                        
                    if organisation_id:
                        query = query.filter(
                            (SystemEvent.organisation_id == organisation_id)
                            | (SystemEvent.organisation_id.is_(None))
                        )
                        
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
                            # The id: field is what lets a client resume; the
                            # browser echoes it back as Last-Event-ID.
                            yield f"id: {event.id}\ndata: {json.dumps(payload)}\n\n"
                            last_write = time.monotonic()
                        except GeneratorExit:
                            raise
                            
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
                # Any DB error → fall through to the heartbeat below, which keeps
                # the connection alive without spinning out a write every cycle.
                pass

            # Unconditional: an idle stream must still write, or nothing ever
            # detects the client going away.
            if time.monotonic() - last_write >= self.HEARTBEAT_SECONDS:
                yield ": heartbeat\n\n"
                last_write = time.monotonic()
                
            time.sleep(self.POLL_INTERVAL_SECONDS)


# Global singleton
event_bus = EventBus()
