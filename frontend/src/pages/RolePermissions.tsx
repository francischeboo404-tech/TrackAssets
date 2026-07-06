import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { roleLabel } from '../lib/roles';

const RolePermissionsPage: React.FC = () => {
  const { addToast } = useToast();
  const { hasPermission } = useAuth();

  const [roles, setRoles] = useState<Record<string, string[]>>({});
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const resp = await api.get('/auth/roles', { skipAuthRedirect: true } as const);
        setRoles(resp.data.roles || {});
        setLabels(resp.data.labels || {});
      } catch (err: any) {
        setError(err.response?.data?.message || 'Failed to load role mappings');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handlePermissionChange = (roleKey: string, text: string) => {
    const perms = text.split(',').map(s => s.trim()).filter(Boolean);
    setRoles(prev => ({ ...prev, [roleKey]: perms }));
  };

  const handleLabelChange = (roleKey: string, newLabel: string) => {
    setLabels(prev => ({ ...prev, [roleKey]: newLabel }));
  };

  const handleAddRole = () => {
    // Add with temporary name
    const tmp = `new_role_${Date.now()}`;
    setRoles(prev => ({ ...prev, [tmp]: [] }));
    setLabels(prev => ({ ...prev, [tmp]: 'New Role' }));
  };

  const handleRemoveRole = (roleKey: string) => {
    const { [roleKey]: _r, ...rest } = roles;
    const { [roleKey]: _l, ...restLabels } = labels;
    setRoles(rest);
    setLabels(restLabels);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/auth/roles', { roles, labels });
      addToast('success', 'Saved', 'Role mappings updated');
    } catch (err: any) {
      addToast('error', 'Save Failed', err.response?.data?.message || 'Failed to save role mappings');
    } finally {
      setSaving(false);
    }
  };

  const PRESET_PERMISSIONS = ['movements:issue', 'movements:return'];

  const applyPresetsToRole = async (roleKey: string) => {
    const prev = roles || {};
    const existing = new Set(prev[roleKey] || []);
    PRESET_PERMISSIONS.forEach(p => existing.add(p));
    const newRoles = { ...prev, [roleKey]: Array.from(existing) };
    setRoles(newRoles);

    setSaving(true);
    try {
      await api.put('/auth/roles', { roles: newRoles, labels });
      addToast('success', 'Saved', 'Movement permissions added and saved');
    } catch (err: any) {
      addToast('error', 'Save Failed', err.response?.data?.message || 'Failed to save role mappings');
    } finally {
      setSaving(false);
    }
  };

  if (!hasPermission('users:view')) {
    return <div className="p-6">Not authorized</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Role Permissions</h1>
        <div className="flex gap-2">
          <button onClick={handleAddRole} className="btn-secondary">Add Role</button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
        </div>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : error ? (
        <div className="text-rose-600">{error}</div>
      ) : (
        <div className="space-y-4">
          <div className="p-3 bg-slate-50 border rounded text-sm text-slate-700">
            <div className="font-semibold">Common movement permissions</div>
            <div className="text-xs mt-1">Quick-add permissions for movements (issue/return). Click to add to a role.</div>
            <div className="mt-2 flex gap-2">
              {PRESET_PERMISSIONS.map(p => (
                <button key={p} onClick={() => {
                  // If no roles selected, apply to all default roles
                  // by default we won't auto-apply to all; user should click per-role
                  addToast('info', 'Tip', `Use the \"Add Role\" button then click a role's Add button to insert '${p}'`);
                }} className="px-2 py-1 bg-white border rounded text-xs">{p}</button>
              ))}
            </div>
          </div>
          {Object.keys(roles).map(roleKey => (
            <div key={roleKey} className="p-4 border rounded-lg bg-white">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold">{roleLabel(roleKey)} <span className="text-xs text-slate-400 ml-2">{roleKey}</span></div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleRemoveRole(roleKey)} className="text-rose-500">Remove</button>
                  <button onClick={() => applyPresetsToRole(roleKey)} className="text-sky-600" disabled={saving}>{saving ? 'Saving...' : 'Add movement perms'}</button>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-400">Label</label>
                  <input className="w-full mt-1 px-3 py-2 border rounded" value={labels[roleKey] ?? ''} onChange={(e) => handleLabelChange(roleKey, e.target.value)} />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-400">Permissions (comma separated)</label>
                  <textarea className="w-full mt-1 px-3 py-2 border rounded" rows={3} value={(roles[roleKey] || []).join(', ')} onChange={(e) => handlePermissionChange(roleKey, e.target.value)} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RolePermissionsPage;
