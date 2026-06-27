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
          {Object.keys(roles).map(roleKey => (
            <div key={roleKey} className="p-4 border rounded-lg bg-white">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold">{roleLabel(roleKey)} <span className="text-xs text-slate-400 ml-2">{roleKey}</span></div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleRemoveRole(roleKey)} className="text-rose-500">Remove</button>
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
