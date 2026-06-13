"""
Centralized role-based access control.

Role mapping (spec → codebase):
  Admin              → admin, superadmin
  Procurement Officer→ dept_head
  Logistics Manager  → staff
  Inventory Manager  → store_manager
  Viewer             → viewer
  (auditor is read-only compliance role in codebase)
"""

from app.errors import AuthorizationError

READ_ONLY_ROLES = frozenset({"viewer", "auditor"})
PRIVILEGED_ROLES = frozenset({"admin", "superadmin"})

# (from_status, to_status) → roles allowed (excluding privileged bypass)
STATUS_TRANSITION_ROLES = {
    ("requested", "approved"): frozenset({"dept_head"}),
    ("requested", "rejected"): frozenset({"dept_head"}),
    ("rejected", "requested"): frozenset({"staff", "dept_head"}),
    ("approved", "in_use"): frozenset({"staff", "store_manager"}),
    ("in_use", "maintenance"): frozenset({"staff", "store_manager"}),
    ("maintenance", "in_use"): frozenset({"staff", "store_manager"}),
    ("in_use", "disposed"): frozenset(),  # admin only (privileged)
    ("maintenance", "disposed"): frozenset(),  # admin only (privileged)
}

ACTION_LABELS = {
    ("requested", "approved"): "approve",
    ("requested", "rejected"): "reject",
    ("approved", "in_use"): "assign",
    ("in_use", "maintenance"): "maintenance",
    ("maintenance", "in_use"): "return_to_use",
    ("in_use", "disposed"): "dispose",
    ("maintenance", "disposed"): "dispose",
    ("rejected", "requested"): "re_request",
}


def is_privileged(role: str) -> bool:
    return role in PRIVILEGED_ROLES


def is_read_only_role(role: str) -> bool:
    return role in READ_ONLY_ROLES


def assert_not_read_only(role: str, action: str = "perform this action"):
    if is_read_only_role(role):
        raise AuthorizationError(
            f"Role '{role}' is read-only and cannot {action}"
        )


def can_transition_status(role: str, from_status: str, to_status: str) -> bool:
    """Return True if role may perform the status transition."""
    if is_privileged(role):
        return True
    if is_read_only_role(role):
        return False

    key = (from_status, to_status)
    allowed = STATUS_TRANSITION_ROLES.get(key)
    if allowed is None:
        return False

    if to_status == "disposed":
        return False

    return role in allowed


def assert_can_transition_status(role: str, from_status: str, to_status: str):
    if not can_transition_status(role, from_status, to_status):
        raise AuthorizationError(
            f"Role '{role}' cannot transition asset from '{from_status}' to '{to_status}'"
        )


def get_available_transitions(role: str, current_status: str) -> list[dict]:
    """Return UI-friendly transition options for a role and current status."""
    from app.models.asset import Asset

    asset = Asset.__new__(Asset)
    asset.status = current_status
    options = []
    for target in (
        "approved",
        "rejected",
        "requested",
        "in_use",
        "maintenance",
        "disposed",
    ):
        if not asset.can_transition_to(target):
            continue
        if can_transition_status(role, current_status, target):
            options.append(
                {
                    "status": target,
                    "action": ACTION_LABELS.get(
                        (current_status, target), target
                    ),
                }
            )
    return options


def filter_analytics_payload(role: str, payload: dict) -> dict:
    """Scope analytics response by role (defense in depth with route guards)."""
    if is_privileged(role) or role == "store_manager":
        return payload

    if role == "auditor":
        return {
            k: payload[k]
            for k in (
                "inventory",
                "assets",
                "recent_activity",
                "currency",
                "total_valuation",
            )
            if k in payload
        }

    if role == "dept_head":
        limited = dict(payload)
        limited.pop("insights", None)
        limited["scope"] = "department"
        return limited

    if role == "viewer":
        assets = payload.get("assets") or {}
        return {
            "inventory": payload.get("inventory"),
            "assets": {
                "total_assets": assets.get("total_assets"),
                "status_breakdown": assets.get("status_breakdown"),
            },
            "currency": payload.get("currency"),
            "scope": "read_only",
        }

    if role == "staff":
        limited = dict(payload)
        limited.pop("insights", None)
        limited["scope"] = "operations"
        return limited

    return payload


REPORT_ACCESS = {
    "assets": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "dept_head", "staff", "viewer"}
    ),
    "inventory": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "dept_head", "staff"}
    ),
    "tracking": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "staff", "dept_head"}
    ),
    "dashboard": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "dept_head", "staff", "viewer"}
    ),
}


def assert_can_access_report(role: str, report_type: str):
    allowed = REPORT_ACCESS.get(report_type, frozenset())
    if is_privileged(role) or role in allowed:
        return
    raise AuthorizationError(
        f"Role '{role}' cannot access '{report_type}' analytics"
    )


def filter_report_payload(role: str, report_type: str, data: dict) -> dict:
    """Scope JSON report payloads by role."""
    if is_privileged(role) or role == "store_manager":
        return data

    if role == "auditor":
        if report_type == "tracking":
            data = dict(data)
            data.pop("movement_timeline", None)
        return data

    if role == "dept_head":
        if report_type == "dashboard":
            return {
                "kpis": data.get("kpis"),
                "assets": data.get("assets"),
                "inventory": {
                    k: data.get("inventory", {}).get(k)
                    for k in (
                        "total_skus",
                        "total_units",
                        "low_stock_count",
                        "stock_levels_chart",
                        "movement_over_time",
                    )
                    if data.get("inventory")
                },
                "critical_alerts": data.get("critical_alerts"),
                "period_days": data.get("period_days"),
                "scope": "department",
            }
        return data

    if role == "viewer":
        if report_type == "assets":
            return {
                "total_count": data.get("total_count"),
                "by_status": data.get("by_status"),
                "utilization_rate": data.get("utilization_rate"),
                "period_days": data.get("period_days"),
                "scope": "read_only",
            }
        if report_type == "dashboard":
            return {
                "kpis": {
                    k: data.get("kpis", {}).get(k)
                    for k in (
                        "total_assets",
                        "total_inventory_units",
                        "utilization_rate",
                        "currency",
                    )
                },
                "assets": {
                    "total_count": data.get("assets", {}).get("total_count"),
                    "by_status": data.get("assets", {}).get("by_status"),
                },
                "critical_alerts": data.get("critical_alerts", [])[:3],
                "scope": "read_only",
            }
        return {"scope": "read_only", "period_days": data.get("period_days")}

    if role == "staff":
        if report_type == "dashboard":
            limited = dict(data)
            limited.pop("asset_roi", None)
            limited["scope"] = "operations"
            return limited
        return data

    return data
