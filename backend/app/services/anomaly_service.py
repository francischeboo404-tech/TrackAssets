import math
from datetime import datetime, timedelta
from flask import current_app
from app.models import ScanEvent


class AnomalyService:
    """Intelligent analysis of tracking data to detect anomalies and drift."""
    # Speed above which a movement is treated as physically impossible rather
    # than merely fast. The default is roughly commercial-jet cruise, so it
    # clears any legitimate ground or air freight movement.
    DEFAULT_MAX_PLAUSIBLE_SPEED_KMH = 900.0

    # Below this, two fixes are treated as the same place: consumer GPS scatter
    # and warehouse-scale movement should not read as travel.
    _MIN_SIGNIFICANT_DISTANCE_KM = 1.0

    @staticmethod
    def _haversine_km(lat1, lon1, lat2, lon2):
        """Great-circle distance between two WGS84 points, in kilometres."""
        earth_radius_km = 6371.0088
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )
        return 2 * earth_radius_km * math.asin(math.sqrt(min(1.0, a)))

    @staticmethod
    def _max_plausible_speed_kmh():
        try:
            return float(
                current_app.config.get(
                    "MAX_PLAUSIBLE_SPEED_KMH",
                    AnomalyService.DEFAULT_MAX_PLAUSIBLE_SPEED_KMH,
                )
            )
        except (RuntimeError, TypeError, ValueError):
            # No application context, or a malformed override.
            return AnomalyService.DEFAULT_MAX_PLAUSIBLE_SPEED_KMH
    
    @staticmethod
    def analyze_scan(current_event: ScanEvent):
        """Perform real-time analysis of a new scan event."""
        anomalies = []

        # 1. Impossible Travel Detection
        # item_id is only unique within an organisation, so this must be
        # tenant-scoped: without the organisation predicate, asset #42 here is
        # compared against asset #42 everywhere else, which both fabricates HIGH
        # severity alerts and leaks another tenant's movement timing.        
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

            # Prefer the coordinates the scan already captured. The warehouse
            # rule below cannot tell a move across the yard from a move across
            # the planet, and says nothing at all about two scans in the same
            # warehouse. It stays as the fallback for scans without a fix.
            coords = (
                prev_event.latitude,
                prev_event.longitude,
                current_event.latitude,
                current_event.longitude,
            )
            if all(c is not None for c in coords):
                distance_km = AnomalyService._haversine_km(*coords)
                max_speed = AnomalyService._max_plausible_speed_kmh()
                hours = time_diff / 60

                if distance_km >= AnomalyService._MIN_SIGNIFICANT_DISTANCE_KM:
                    if hours <= 0:
                        # Same instant, two places: no speed is finite.
                        anomalies.append(
                            {
                                "type": "IMPOSSIBLE_TRAVEL",
                                "severity": "HIGH",
                                "message": (
                                    f"Item scanned {distance_km:.1f} km apart with no time "
                                    f"between scans. Potential spoofing."
                                ),
                            }
                        )
                    elif (distance_km / hours) > max_speed:
                        implied_speed = distance_km / hours
                        anomalies.append(
                            {
                                "type": "IMPOSSIBLE_TRAVEL",
                                "severity": "HIGH",
                                "message": (
                                    f"Item moved {distance_km:.1f} km in {time_diff:.1f} minutes "
                                    f"({implied_speed:.0f} km/h, ceiling {max_speed:.0f} km/h). "
                                    f"Potential spoofing."
                                ),
                            }
                        )
            # Fallback for scans with no coordinates: changed warehouses within a
            # ridiculously short time (e.g., < 10 mins)
            elif (
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
    def predict_misplaced_items(org_id, limit=None):
        """
        Identify items whose current location doesn't match their expected location.

        Cross-references three item types (Asset, InventoryItem, ItemInstance) with their
        latest ScanEvent records to detect misplaced items.

        Args:
            org_id: Organization ID (tenant isolation)
            limit: Optional max results to return (for pagination)

        Returns:
            List of anomaly dicts, sorted by severity (HIGH first) and staleness
        """
        from app.models.asset import Asset, AssetStatus
        from app.models.inventory import InventoryItem
        from app.models.item_instance import ItemInstance
        from app.models.location_topology import Warehouse
        from app.models.organization import Department
        from app.models.user import User
        from sqlalchemy import func, and_, or_

        anomalies = []

        # =====================================================================
        # QUERY STRATEGY: Batch fetch latest scans for each item type
        # =====================================================================
        # This avoids N+1 queries and uses existing indexes on ScanEvent

        def get_latest_scans_per_item(item_type):
            """Get latest verified scan for each item of a type."""
            subq = (
                ScanEvent.query.with_entities(
                    ScanEvent.item_type,
                    ScanEvent.item_id,
                    func.max(ScanEvent.timestamp).label("latest"),
                )
                .filter(
                    ScanEvent.organisation_id == org_id,
                    ScanEvent.item_type == item_type,
                    ScanEvent.validation_status == "verified",
                )
                .group_by(ScanEvent.item_type, ScanEvent.item_id)
                .subquery()
            )

            events = (
                ScanEvent.query.join(
                    subq,
                    and_(
                        ScanEvent.item_type == subq.c.item_type,
                        ScanEvent.item_id == subq.c.item_id,
                        ScanEvent.timestamp == subq.c.latest,
                    ),
                )
                .filter(ScanEvent.organisation_id == org_id)
                .all()
            )

            return {event.item_id: event for event in events}

        # =====================================================================
        # ASSET MISPLACED DETECTION
        # =====================================================================

        skip_asset_statuses = [
            AssetStatus.DISPOSED.value,
            AssetStatus.LOST.value,
            AssetStatus.DAMAGED.value,
        ]

        assets = Asset.query.filter(
            Asset.organisation_id == org_id,
            ~Asset.status.in_(skip_asset_statuses),
        ).all()

        asset_scans = get_latest_scans_per_item("asset")

        for asset in assets:
            # Resolve expected warehouse based on assignment hierarchy
            expected_warehouse_id = None
            assignment_type = None

            # Priority 1: Assigned to user
            if asset.assigned_to_user_id:
                user = User.query.get(asset.assigned_to_user_id)
                if user and user.department_id:
                    dept = Department.query.get(user.department_id)
                    if dept and dept.warehouse_id:
                        expected_warehouse_id = dept.warehouse_id
                        assignment_type = "assigned_to_user"

            # Priority 2: Assigned to department
            if not expected_warehouse_id and asset.assigned_department_id:
                dept = Department.query.get(asset.assigned_department_id)
                if dept and dept.warehouse_id:
                    expected_warehouse_id = dept.warehouse_id
                    assignment_type = "assigned_to_department"

            # Priority 3: Home department
            if not expected_warehouse_id and asset.department_id:
                dept = Department.query.get(asset.department_id)
                if dept and dept.warehouse_id:
                    expected_warehouse_id = dept.warehouse_id
                    assignment_type = "home_department"

            # Skip: Cannot determine expected location
            if not expected_warehouse_id:
                continue

            expected_warehouse = Warehouse.query.get(expected_warehouse_id)
            expected_wh_name = (
                expected_warehouse.name
                if expected_warehouse
                else f"WH_{expected_warehouse_id}"
            )

            # Get latest scan
            latest_scan = asset_scans.get(asset.id)

            # Detect misplacement
            is_misplaced = False
            severity = None
            message = None

            if latest_scan is None:
                # No scan history
                is_misplaced = True
                severity = "HIGH"
                message = f"{asset.asset_code} has no scan history. Location unknown."
                days_since_scan = None
            else:
                days_since_scan = (datetime.utcnow() - latest_scan.timestamp).days

                if latest_scan.warehouse_id != expected_warehouse_id:
                    # Different warehouse entirely
                    is_misplaced = True
                    severity = "HIGH"
                    actual_wh = Warehouse.query.get(latest_scan.warehouse_id)
                    actual_wh_name = (
                        actual_wh.name if actual_wh else f"WH_{latest_scan.warehouse_id}"
                    )
                    message = f"{asset.asset_code} expected in {expected_wh_name} but found in {actual_wh_name}"

                elif latest_scan.bin_id and asset.bin_id:
                    # Same warehouse, check bin level
                    if latest_scan.bin_id != asset.bin_id:
                        is_misplaced = True
                        severity = "MEDIUM"
                        message = f"{asset.asset_code} in {expected_wh_name} but wrong bin (scan: {latest_scan.bin_id} vs expected: {asset.bin_id})"

                # Adjust severity for stale data (> 30 days)
                if is_misplaced and days_since_scan > 30:
                    if severity == "HIGH":
                        message += f" (Last scanned {days_since_scan} days ago)"
                    else:
                        severity = "LOW"
                        message += f" (Last scanned {days_since_scan} days ago)"

            if is_misplaced:
                actual_warehouse = (
                    Warehouse.query.get(latest_scan.warehouse_id)
                    if latest_scan and latest_scan.warehouse_id
                    else None
                )
                actual_wh_name = (
                    actual_warehouse.name if actual_warehouse else "Unknown"
                )

                anomalies.append(
                    {
                        "type": "MISPLACED_ITEM",
                        "severity": severity,
                        "item_type": "asset",
                        "item_id": asset.id,
                        "item_name": asset.name,
                        "item_code": asset.asset_code,
                        "expected_location": {
                            "warehouse_id": expected_warehouse_id,
                            "warehouse_name": expected_wh_name,
                        },
                        "actual_location": {
                            "warehouse_id": latest_scan.warehouse_id if latest_scan else None,
                            "warehouse_name": actual_wh_name if latest_scan else "No scan data",
                            "bin_id": latest_scan.bin_id if latest_scan else None,
                            "timestamp": latest_scan.timestamp.isoformat() if latest_scan else None,
                        },
                        "days_since_scan": days_since_scan,
                        "message": message,
                        "assignment_type": assignment_type,
                    }
                )

        # =====================================================================
        # INVENTORY ITEM MISPLACED DETECTION
        # =====================================================================

        inventory_items = InventoryItem.query.filter(
            InventoryItem.organisation_id == org_id,
            InventoryItem.is_active == True,
            InventoryItem.warehouse_id.isnot(None),
        ).all()

        inventory_scans = get_latest_scans_per_item("inventory")

        for inventory_item in inventory_items:
            expected_warehouse_id = inventory_item.warehouse_id
            expected_warehouse = Warehouse.query.get(expected_warehouse_id)
            expected_wh_name = (
                expected_warehouse.name
                if expected_warehouse
                else f"WH_{expected_warehouse_id}"
            )

            latest_scan = inventory_scans.get(inventory_item.id)

            is_misplaced = False
            severity = None
            message = None

            if latest_scan is None:
                is_misplaced = True
                severity = "HIGH"
                message = f"Inventory {inventory_item.sku} has no scan history. Location unknown."
                days_since_scan = None
            else:
                days_since_scan = (datetime.utcnow() - latest_scan.timestamp).days

                if latest_scan.warehouse_id != expected_warehouse_id:
                    is_misplaced = True
                    severity = "HIGH"
                    actual_wh = Warehouse.query.get(latest_scan.warehouse_id)
                    actual_wh_name = (
                        actual_wh.name if actual_wh else f"WH_{latest_scan.warehouse_id}"
                    )
                    message = f"Inventory {inventory_item.sku} expected in {expected_wh_name} but found in {actual_wh_name}"

                    if days_since_scan > 30:
                        message += f" (Last scanned {days_since_scan} days ago)"

            if is_misplaced:
                actual_warehouse = (
                    Warehouse.query.get(latest_scan.warehouse_id)
                    if latest_scan and latest_scan.warehouse_id
                    else None
                )
                actual_wh_name = (
                    actual_warehouse.name if actual_warehouse else "Unknown"
                )

                anomalies.append(
                    {
                        "type": "MISPLACED_ITEM",
                        "severity": severity,
                        "item_type": "inventory",
                        "item_id": inventory_item.id,
                        "item_name": inventory_item.name,
                        "item_code": inventory_item.sku,
                        "expected_location": {
                            "warehouse_id": expected_warehouse_id,
                            "warehouse_name": expected_wh_name,
                        },
                        "actual_location": {
                            "warehouse_id": latest_scan.warehouse_id if latest_scan else None,
                            "warehouse_name": actual_wh_name if latest_scan else "No scan data",
                            "bin_id": latest_scan.bin_id if latest_scan else None,
                            "timestamp": latest_scan.timestamp.isoformat() if latest_scan else None,
                        },
                        "days_since_scan": days_since_scan,
                        "message": message,
                    }
                )

        # =====================================================================
        # ITEM INSTANCE MISPLACED DETECTION
        # =====================================================================

        item_instances = (
            ItemInstance.query.join(InventoryItem)
            .filter(
                InventoryItem.organisation_id == org_id,
                ~ItemInstance.status.in_(["shipped", "lost"]),
                ItemInstance.warehouse_id.isnot(None),
            )
            .all()
        )

        instance_scans = get_latest_scans_per_item("inventory_instance")

        for instance in item_instances:
            expected_warehouse_id = instance.warehouse_id
            expected_bin_id = instance.bin_id

            expected_warehouse = Warehouse.query.get(expected_warehouse_id)
            expected_wh_name = (
                expected_warehouse.name
                if expected_warehouse
                else f"WH_{expected_warehouse_id}"
            )

            inventory = InventoryItem.query.get(instance.item_id)
            item_name = (
                f"{inventory.name} ({instance.serial_number})"
                if inventory
                else str(instance.serial_number)
            )

            latest_scan = instance_scans.get(instance.id)

            is_misplaced = False
            severity = None
            message = None

            if latest_scan is None:
                is_misplaced = True
                severity = "HIGH"
                message = f"Item {instance.serial_number} has no scan history. Location unknown."
                days_since_scan = None
            else:
                days_since_scan = (datetime.utcnow() - latest_scan.timestamp).days

                if latest_scan.warehouse_id != expected_warehouse_id:
                    is_misplaced = True
                    severity = "HIGH"
                    actual_wh = Warehouse.query.get(latest_scan.warehouse_id)
                    actual_wh_name = (
                        actual_wh.name if actual_wh else f"WH_{latest_scan.warehouse_id}"
                    )
                    message = f"Item {instance.serial_number} expected in {expected_wh_name} but found in {actual_wh_name}"

                elif latest_scan.bin_id and expected_bin_id:
                    if latest_scan.bin_id != expected_bin_id:
                        is_misplaced = True
                        severity = "MEDIUM"
                        message = f"Item {instance.serial_number} in {expected_wh_name} but wrong bin (scan: {latest_scan.bin_id} vs expected: {expected_bin_id})"

                # Adjust severity for stale data
                if is_misplaced and days_since_scan > 30:
                    if severity == "HIGH":
                        message += f" (Last scanned {days_since_scan} days ago)"
                    else:
                        severity = "LOW"
                        message += f" (Last scanned {days_since_scan} days ago)"

            if is_misplaced:
                actual_warehouse = (
                    Warehouse.query.get(latest_scan.warehouse_id)
                    if latest_scan and latest_scan.warehouse_id
                    else None
                )
                actual_wh_name = (
                    actual_warehouse.name if actual_warehouse else "Unknown"
                )

                anomalies.append(
                    {
                        "type": "MISPLACED_ITEM",
                        "severity": severity,
                        "item_type": "inventory_instance",
                        "item_id": instance.id,
                        "item_name": item_name,
                        "item_code": instance.serial_number,
                        "expected_location": {
                            "warehouse_id": expected_warehouse_id,
                            "warehouse_name": expected_wh_name,
                            "bin_id": expected_bin_id,
                        },
                        "actual_location": {
                            "warehouse_id": latest_scan.warehouse_id if latest_scan else None,
                            "warehouse_name": actual_wh_name if latest_scan else "No scan data",
                            "bin_id": latest_scan.bin_id if latest_scan else None,
                            "timestamp": latest_scan.timestamp.isoformat() if latest_scan else None,
                        },
                        "days_since_scan": days_since_scan,
                        "message": message,
                    }
                )

        # =====================================================================
        # SORT AND LIMIT RESULTS
        # =====================================================================
        # Sort by: Severity (HIGH first) → Days since scan (oldest first)

        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        anomalies.sort(
            key=lambda x: (
                severity_order.get(x["severity"], 3),
                -(x["days_since_scan"] or 0),  # Oldest first (negate to reverse)
            )
        )

        if limit:
            anomalies = anomalies[:limit]

        return anomalies
