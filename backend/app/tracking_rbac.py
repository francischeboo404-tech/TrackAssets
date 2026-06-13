"""Role-based rules for QR scan actions."""

from app.errors import AuthorizationError
from app.rbac import is_read_only_role, is_privileged

# Spec mapping: Logistics → staff/store_manager; Viewer → read-only verify/audit
SCAN_ACTION_ROLES = {
    "VERIFY": frozenset(
        {"admin", "staff", "store_manager", "dept_head", "viewer", "auditor"}
    ),
    "AUDIT": frozenset(
        {"admin", "staff", "store_manager", "dept_head", "viewer", "auditor"}
    ),
    "CHECK_IN": frozenset({"admin", "staff", "store_manager"}),
    "CHECK_OUT": frozenset({"admin", "staff", "store_manager"}),
    "TRANSFER": frozenset({"admin", "staff", "store_manager", "dept_head"}),
}

READ_ONLY_ACTIONS = frozenset({"VERIFY", "AUDIT"})


def assert_can_scan(role: str, action_type: str):
    action = (action_type or "").upper()
    if is_privileged(role):
        return
    allowed = SCAN_ACTION_ROLES.get(action)
    if not allowed or role not in allowed:
        raise AuthorizationError(
            f"Role '{role}' cannot perform scan action '{action}'"
        )
    if is_read_only_role(role) and action not in READ_ONLY_ACTIONS:
        raise AuthorizationError(
            f"Role '{role}' is read-only; only VERIFY/AUDIT scans are allowed"
        )


def is_state_mutating_action(action_type: str) -> bool:
    return (action_type or "").upper() not in READ_ONLY_ACTIONS
