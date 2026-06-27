"""
# ==========================================
# CENTRALIZED ROLE-BASED ACCESS CONTROL
# ==========================================
# 1. Admin / Superadmin: System configuration, disposal approval
# 2. Procurement Officer: Requisitions, POs, Approvals
# 3. Store Manager: Stock keeping, receipt validation, storage
# 4. Logistics Officer: Assignment, transition, issuing
# 5. Employee: Requested drafts, view-only (scoped)
# ==========================================
"""



ROLE_ALIASES = {
    "staff": "logistics_officer",
    "dept_head": "procurement_officer",
    "viewer": "employee",
}

READ_ONLY_ROLES = frozenset({"employee", "auditor"})
PRIVILEGED_ROLES = frozenset({"admin", "superadmin"})

# (from_status, to_status) → roles allowed (excluding privileged bypass)
STATUS_TRANSITION_ROLES = {
    ("requested", "approved"): frozenset({"procurement_officer"}),
    ("requested", "rejected"): frozenset({"procurement_officer"}),
    ("rejected", "requested"): frozenset({"logistics_officer", "procurement_officer"}),
    ("approved", "in_use"): frozenset({"store_manager", "logistics_officer"}),
    ("in_use", "maintenance"): frozenset({"store_manager", "logistics_officer"}),
    ("maintenance", "in_use"): frozenset({"store_manager", "logistics_officer"}),
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


def normalize_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)


def is_privileged(role: str) -> bool:
    return normalize_role(role) in PRIVILEGED_ROLES


def is_read_only_role(role: str) -> bool:
    return normalize_role(role) in READ_ONLY_ROLES


def assert_not_read_only(role: str, action: str = "perform this action"):
    if is_read_only_role(role):
        from app.errors import AuthorizationError

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
        from app.errors import AuthorizationError

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

    if role == "procurement_officer":
        limited = dict(payload)
        limited.pop("insights", None)
        limited["scope"] = "department"
        return limited

    if role == "employee":
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

    if role == "logistics_officer":
        limited = dict(payload)
        limited.pop("insights", None)
        limited["scope"] = "operations"
        return limited

    return payload


REPORT_ACCESS = {
    "assets": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "procurement_officer", "logistics_officer", "employee"}
    ),
    "inventory": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "procurement_officer", "logistics_officer"}
    ),
    "tracking": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "procurement_officer", "logistics_officer"}
    ),
    "dashboard": frozenset(
        {"admin", "superadmin", "auditor", "store_manager", "procurement_officer", "logistics_officer", "employee"}
    ),
}


def assert_can_access_report(role: str, report_type: str):
    role = normalize_role(role)
    allowed = REPORT_ACCESS.get(report_type, frozenset())
    if is_privileged(role) or role in allowed:
        return
    from app.errors import AuthorizationError

    raise AuthorizationError(
        f"Role '{role}' cannot access '{report_type}' analytics"
    )


def filter_report_payload(role: str, report_type: str, data: dict) -> dict:
    """Scope JSON report payloads by role."""
    role = normalize_role(role)
    if is_privileged(role) or role == "store_manager":
        return data

    if role == "auditor":
        if report_type == "tracking":
            data = dict(data)
            data.pop("movement_timeline", None)
        return data

    if role == "procurement_officer":
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

    if role == "employee":
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

    if role == "logistics_officer":
        if report_type == "dashboard":
            limited = dict(data)
            limited.pop("asset_roi", None)
            limited["scope"] = "operations"
            return limited
        return data

    return data


# Centralized permissions mapping for role -> permission strings
# Permission format: 'resource:action' e.g. 'assets:edit'
ROLE_PERMISSIONS = {
    "superadmin": ["*:*"],
    "admin": ["*:*", "inventory:delete", "assets:dispose"],
    "store_manager": [
        "assets:*",
        "inventory:view",
        "inventory:create",
        "inventory:edit",
        "inventory:stock",
        "transfers:*",
        "warehouses:*",
        "disposal:create",
        "variance:create",
        "variance:resolve",
        "analytics:view",
        "users:view",
        "reports:view",
    ],
    "logistics_officer": [
        "assets:view",
        "assets:create",
        "assets:edit",
        "assets:transition",
        "inventory:view",
        "inventory:stock",
        "transfers:create",
        "transfers:view",
        "warehouses:view",
        "disposal:create",
        "variance:create",
    ],
    "procurement_officer": [
        "assets:view",
        "assets:approve",
        "assets:transition",
        "inventory:view",
        "warehouses:view",
        "transfers:approve",
        "transfers:create",
        "transfers:view",
        "reports:view",
    ],
    "employee": [
        "assets:view",
        "inventory:view",
        "warehouses:view",
        "reports:view",
    ],
    "auditor": [
        "assets:view",
        "inventory:view",
        "audit:view",
        "reports:view",
    ],
}


# Human-friendly labels for UI display (kept server-side as source-of-truth)
ROLE_LABELS = {
    "superadmin": "Super Administrator",
    "admin": "Administrator",
    "store_manager": "Store Manager",
    "logistics_officer": "Logistics Officer",
    "procurement_officer": "Procurement Officer",
    "employee": "Staff",
    "auditor": "Auditor",
    "viewer": "Viewer",
    # legacy alias — kept for compatibility with older DB rows
    "dept_head": "Department Head",
}


def role_has_permission(role: str, permission: str) -> bool:
    """Return True if `role` grants `permission`.

    Supports resource-level wildcards (e.g. 'assets:*') and global wildcard '*:*'.
    """
    if not role or not permission:
        return False

    # Superadmin / admin bypass
    if role in ("superadmin", "admin"):
        return True

    # First, prefer DB-backed mappings when available
    try:
        from app.models.role_mapping import RoleMapping

        rm = RoleMapping.query.filter_by(role=role, is_active=True).first()
        if rm and rm.permissions:
            allowed = rm.permissions or []
            if "*:*" in allowed:
                return True
            if permission in allowed:
                return True
            try:
                resource, _action = permission.split(":", 1)
            except Exception:
                return False
            if f"{resource}:*" in allowed:
                return True
            return False
    except Exception:
        # If DB is not available or query fails, fall back to static mapping
        pass

    allowed = ROLE_PERMISSIONS.get(role, [])
    if "*:*" in allowed:
        return True
    if permission in allowed:
        return True

    # resource-level wildcard match
    try:
        resource, _action = permission.split(":", 1)
    except Exception:
        return False
    if f"{resource}:*" in allowed:
        return True

    return False
