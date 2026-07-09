export const ROLE_PERMISSIONS: Record<string, string[]> = {
  superadmin: ['*:*'],
  admin: ['*:*', 'inventory:delete', 'assets:dispose'],
  store_manager: ['assets:*', 'inventory:create', 'inventory:edit', 'inventory:stock', 'transfers:*', 'warehouses:*', 'analytics:view', 'users:view', 'reports:view', 'disposal:create', 'variance:create', 'variance:resolve'],
  logistics_officer: ['assets:view', 'assets:create', 'assets:edit', 'assets:transition', 'inventory:view', 'inventory:stock', 'transfers:create', 'transfers:view', 'warehouses:view', 'disposal:create', 'variance:create'],
  procurement_officer: ['assets:view', 'assets:approve', 'assets:transition', 'transfers:approve', 'transfers:create', 'transfers:view', 'reports:view'],
  employee: ['assets:view', 'inventory:view', 'warehouses:view', 'reports:view'],
  auditor: ['assets:view', 'inventory:view', 'audit:view', 'reports:view'],
};

export function roleHasPermission(role: string | undefined | null, permission: string): boolean {
  if (!role) return false;
  if (role === 'admin' || role === 'superadmin') return true;
  const allowed = ROLE_PERMISSIONS[role] || [];
  if (allowed.includes('*:*')) return true;
  if (allowed.includes(permission)) return true;
  const [resource] = permission.split(':');
  if (allowed.includes(`${resource}:*`)) return true;
  return false;
}
