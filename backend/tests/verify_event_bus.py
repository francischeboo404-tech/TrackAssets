from unittest.mock import MagicMock
import sys


def test_event_bus():
    # Mock the 'app' module before importing EventBus
    sys.modules["app"] = MagicMock()
    db_mock = MagicMock()
    sys.modules["app"].db = db_mock

    from app.services.event_bus import EventBus

    bus = EventBus()
    q = bus.subscribe()

    event_type = "TEST_EVENT"
    data = {"key": "value"}

    bus.publish(event_type, data)

    msg = q.get_nowait()
    assert msg["type"] == event_type
    assert msg["data"] == data
    assert "timestamp" in msg
    print("EventBus test passed!")


if __name__ == "__main__":
    try:
        test_event_bus()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
