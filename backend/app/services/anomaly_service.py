from datetime import datetime, timedelta
from app.models import ScanEvent


class AnomalyService:
    """Intelligent analysis of tracking data to detect anomalies and drift."""

    @staticmethod
    def analyze_scan(current_event: ScanEvent):
        """Perform real-time analysis of a new scan event."""
        anomalies = []

        # 1. Impossible Travel Detection
        prev_event = (
            ScanEvent.query.filter(
                ScanEvent.item_type == current_event.item_type,
                ScanEvent.item_id == current_event.item_id,
                ScanEvent.id != current_event.id,
                ScanEvent.timestamp < current_event.timestamp,
            )
            .order_by(ScanEvent.timestamp.desc())
            .first()
        )

        if prev_event:
            time_diff = (
                current_event.timestamp - prev_event.timestamp
            ).total_seconds() / 60
            # If changed warehouses within a ridiculously short time (e.g., < 10 mins)
            if (
                prev_event.warehouse_id != current_event.warehouse_id
                and time_diff < 10
            ):
                anomalies.append(
                    {
                        "type": "IMPOSSIBLE_TRAVEL",
                        "severity": "HIGH",
                        "message": f"Item moved between warehouses in {time_diff:.1f} minutes. Potential spoofing.",
                    }
                )

        # 2. Workflow State Violation
        # This would be integrated with item.status checks

        return anomalies

    @staticmethod
    def detect_duplicate_scans(org_id, window_minutes=5):
        """Detect if unique items are being scanned in multiple places simultaneously."""
        threshold = datetime.utcnow() - timedelta(minutes=window_minutes)

        # Find items with multiple scans from different devices in the last X minutes
        results = ScanEvent.query.filter(
            ScanEvent.organisation_id == org_id,
            ScanEvent.timestamp >= threshold,
        ).all()

        # Group by item and check device IDs
        item_scans = {}
        duplicates = []
        for event in results:
            key = (event.item_type, event.item_id)
            if key not in item_scans:
                item_scans[key] = set()
            item_scans[key].add(event.device_id)

            if len(item_scans[key]) > 1:
                duplicates.append(
                    {
                        "item_type": event.item_type,
                        "item_id": event.item_id,
                        "devices": list(item_scans[key]),
                    }
                )

        return duplicates

    @staticmethod
    def predict_misplaced_items(org_id):
        """Identify items whose current location doesn't match their assigned department/expected location."""
        # This is a bit more complex as it requires cross-referencing Asset.department_id
        # with the latest ScanEvent.warehouse_id/bin_id.
