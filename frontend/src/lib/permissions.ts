import type { UserRole } from '../types';

/**
 * Spec → codebase role mapping:
 * Admin → admin | Procurement → dept_head | Logistics → staff
 * Inventory Manager → store_manager | Viewer → viewer
 */
export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Admin',
  dept_head: 'Procurement Officer',
  staff: 'Logistics Manager',
  store_manager: 'Inventory Manager',
  viewer: 'Viewer',
  auditor: 'Auditor',
};

const PRIVILEGED: UserRole[] = ['admin'];
const READ_ONLY: UserRole[] = ['viewer', 'auditor'];

export function isPrivileged(role?: string): boolean {
  return !!role && PRIVILEGED.includes(role as UserRole);
}

export function isReadOnly(role?: string): boolean {
  return !!role && READ_ONLY.includes(role as UserRole);
}

export function canAccess(role: string | undefined, allowed: UserRole[]): boolean {
  if (!role) return false;
  if (isPrivileged(role)) return true;
  return allowed.includes(role as UserRole);
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
  return !!allowed?.includes(role as UserRole);
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
