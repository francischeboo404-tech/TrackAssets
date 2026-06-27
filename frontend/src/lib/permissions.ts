import type { UserRole } from '../types';

/**
 * Spec → codebase role mapping:
 * Admin → admin | Procurement → dept_head | Logistics → staff
 * Inventory Manager → store_manager | Viewer → viewer
 */
export const ROLE_LABELS: Record<UserRole, string> = {
  superadmin: 'Super Administrator',
  admin: 'Admin',
  store_manager: 'Inventory Manager',
  logistics_officer: 'Logistics Officer',
  procurement_officer: 'Procurement Officer',
  employee: 'Staff',
  viewer: 'Viewer',
  auditor: 'Auditor',
  dept_head: 'Procurement Officer',
  staff: 'Logistics Officer',
};

const PRIVILEGED: UserRole[] = ['admin', 'superadmin'];
const READ_ONLY: UserRole[] = ['viewer', 'auditor'];

const ROLE_EQUIVALENTS: Record<UserRole, UserRole[]> = {
  superadmin: ['superadmin'],
  admin: ['admin'],
  store_manager: ['store_manager'],
  logistics_officer: ['logistics_officer', 'staff'],
  procurement_officer: ['procurement_officer', 'dept_head'],
  employee: ['employee', 'viewer'],
  viewer: ['employee', 'viewer'],
  auditor: ['auditor'],
  dept_head: ['procurement_officer', 'dept_head'],
  staff: ['logistics_officer', 'staff'],
};

function getRoleEquivalents(role?: string): UserRole[] {
  if (!role) return [];
  const normalized = role as UserRole;
  return ROLE_EQUIVALENTS[normalized] ?? [normalized];
}

function roleMatches(role: string | undefined, allowedRole: UserRole): boolean {
  const equivalents = getRoleEquivalents(role);
  const allowedEquivalents = getRoleEquivalents(allowedRole);
  return equivalents.some((equivalent) => allowedEquivalents.includes(equivalent));
}

export function isPrivileged(role?: string): boolean {
  return !!role && PRIVILEGED.includes(role as UserRole);
}

export function isReadOnly(role?: string): boolean {
  if (!role) return false;
  const equivalents = getRoleEquivalents(role);
  return equivalents.some((equivalent) => READ_ONLY.includes(equivalent));
}

export function canAccess(role: string | undefined, allowed: UserRole[]): boolean {
  if (!role) return false;
  if (isPrivileged(role)) return true;
  return allowed.some((allowedRole) => roleMatches(role, allowedRole));
}

const STATUS_TRANSITIONS: Record<string, Record<string, UserRole[]>> = {
  available: {
    assigned: ['store_manager', 'dept_head'],
    under_maintenance: ['staff', 'store_manager'],
    lost: ['store_manager'],
    damaged: ['store_manager'],
    disposed: ['admin'],
  },
  assigned: {
    available: ['store_manager', 'dept_head'],
    under_maintenance: ['staff', 'store_manager'],
    lost: ['store_manager'],
    damaged: ['store_manager'],
    disposed: ['admin'],
  },
  under_maintenance: {
    available: ['staff', 'store_manager'],
    assigned: ['store_manager', 'dept_head'],
    disposed: ['admin'],
  },
  lost: {
    available: ['store_manager'],
    disposed: ['admin'],
  },
  damaged: {
    under_maintenance: ['staff', 'store_manager'],
    disposed: ['admin'],
  },
};

export function canTransitionAsset(
  role: string | undefined,
  fromStatus: string,
  toStatus: string,
): boolean {
  if (!role || isReadOnly(role)) return false;
  if (isPrivileged(role)) return true;
  if (toStatus === 'disposed') return false;
  const allowed = STATUS_TRANSITIONS[fromStatus]?.[toStatus];
  if (!allowed) return false;
  return allowed.some((allowedRole) => roleMatches(role, allowedRole));
}

export function canAssignAsset(role?: string): boolean {
  return canAccess(role, ['store_manager', 'dept_head']);
}

export function canReturnAsset(role?: string): boolean {
  return canAccess(role, ['store_manager', 'dept_head']);
}

export function canCreateAsset(role?: string): boolean {
  return canAccess(role, ['staff', 'store_manager']);
}

export function canEditAsset(role?: string): boolean {
  return canAccess(role, ['staff', 'store_manager']);
}

export function canEditInventory(role?: string): boolean {
  return canAccess(role, ['store_manager']);
}

export function canAdjustStock(role?: string): boolean {
  return canAccess(role, ['staff', 'store_manager']);
}

export function canDeleteInventory(role?: string): boolean {
  return isPrivileged(role);
}

export function canRequestTransfer(role?: string): boolean {
  return canAccess(role, ['staff', 'dept_head', 'store_manager']);
}

const SCAN_ACTION_ROLES: Record<string, UserRole[]> = {
  VERIFY: ['admin', 'staff', 'store_manager', 'dept_head', 'viewer', 'auditor'],
  AUDIT: ['admin', 'staff', 'store_manager', 'dept_head', 'viewer', 'auditor'],
  CHECK_IN: ['admin', 'staff', 'store_manager'],
  CHECK_OUT: ['admin', 'staff', 'store_manager'],
  TRANSFER: ['admin', 'staff', 'store_manager', 'dept_head'],
};

export function canPerformScanAction(role: string | undefined, action: string): boolean {
  if (!role) return false;
  if (isPrivileged(role)) return true;
  const allowed = SCAN_ACTION_ROLES[action.toUpperCase()];
  return !!allowed?.includes(role as UserRole);
}

export function isReadOnlyScanner(role?: string): boolean {
  return isReadOnly(role);
}
