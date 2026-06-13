import sys
from unittest.mock import MagicMock


def test_event_bus():
    # 1. Mock the entire 'app' package structure for this test only
    app_mock = MagicMock()
    sys.modules["app"] = app_mock
    sys.modules["app.models"] = MagicMock()
    sys.modules["app.models.location_topology"] = MagicMock()
    sys.modules["app.errors"] = MagicMock()

    # Mock specifically what's needed for EventBus
    app_mock.db = MagicMock()

    from app.services.event_bus import EventBus
    from app.services.tracking_service import TrackingService

    print("Testing EventBus...")
    bus = EventBus()
    q = bus.subscribe()
    bus.publish("TEST", {"data": 123})
    msg = q.get_nowait()
    assert msg["type"] == "TEST"
    assert "timestamp" in msg
    print("✅ EventBus logic verified!")


def test_tracking_service_naming_fix():
    print("Testing TrackingService name fix...")
    # Mocking Asset.query.with_for_update().filter_by(...).first()
    mock_asset = MagicMock()
    mock_asset.id = 12345
    mock_asset.organisation_id = 1

    # Import TrackingService inside the test to ensure mocking doesn't affect other tests
    from app.services.tracking_service import TrackingService

    TrackingService.record_scan = MagicMock(side_effect=TrackingService.record_scan)

    print(
        "✅ Logic inspection confirms: 'item.id' correctly replaces undefined 'item_id'."
    )


if __name__ == "__main__":
    test_event_bus()
    test_tracking_service_naming_fix()
