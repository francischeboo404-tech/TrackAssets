export const ROLE_OPTIONS = [
  'superadmin',
  'admin',
  'store_manager',
  'logistics_officer',
  'procurement_officer',
  'employee',
  'auditor',
  'staff',
];

export const ROLE_LABELS: Record<string, string> = {
  superadmin: 'Super Administrator',
  admin: 'Administrator',
  store_manager: 'Store Manager',
  logistics_officer: 'Logistics Officer',
  procurement_officer: 'Procurement Officer',
  employee: 'Staff',
  auditor: 'Auditor',
};

export function roleLabel(role?: string | null) {
  if (!role) return '';
  return ROLE_LABELS[role] ?? role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
