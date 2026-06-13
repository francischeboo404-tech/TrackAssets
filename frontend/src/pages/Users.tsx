import { useState } from 'react';
import { Users as UsersIcon, UserX, UserCheck, Mail, Search, Plus, X, Shield, Lock } from 'lucide-react';
import { useUsers, useUpdateUserRole, useToggleUserStatus } from '../hooks/useUsers';
import { useToast } from '../context/ToastContext';
import { cn } from '../lib/utils';
import { useAuth } from '../context/AuthContext';

const ROLE_OPTIONS = [
  'admin', 'staff', 'dept_head', 'store_manager', 'viewer', 'auditor'
];

const Users = () => {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [page, setPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    password: '',
    role: 'staff',
    first_name: '',
    last_name: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { data, isLoading } = useUsers({ 
    search: search || undefined,
    role: roleFilter || undefined, 
    page 
  });
  
  const users = (data as any)?.users || [];
  const pagination = (data as any)?.pagination;

  const updateRoleMutation = useUpdateUserRole();
  const toggleStatusMutation = useToggleUserStatus();
  const { addToast } = useToast();
  const { user: currentUser } = useAuth();

  const handleRoleChange = async (id: number, newRole: string) => {
    try {
      await updateRoleMutation.mutateAsync({ id, role: newRole });
      addToast('success', 'Role Updated', `User role changed to ${newRole}`);
    } catch (err) {
      addToast('error', 'Update Failed', 'Failed to change user role.');
    }
  };

  const handleToggleStatus = async (id: number, currentStatus: boolean) => {
    try {
      await toggleStatusMutation.mutateAsync({ id, is_active: !currentStatus });
      addToast('info', 'Status Updated', 'User access has been modified.');
    } catch (err) {
      addToast('error', 'Update Failed', 'Action not permitted or server error.');
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const api = (await import('../services/api')).default;
      await api.post('/users', newUser);
      addToast('success', 'User Created', `${newUser.username} has been added to the institution.`);
      setIsModalOpen(false);
      setNewUser({ username: '', email: '', password: '', role: 'staff', first_name: '', last_name: '' });
      window.location.reload(); // Simple refresh to show new user
    } catch (err: any) {
      addToast('error', 'Creation Failed', err.response?.data?.message || 'Failed to create user.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
            <UsersIcon className="text-brand-primary w-8 h-8" />
            Team Management
          </h1>
          <p className="text-slate-500 mt-1 font-medium">Manage access, roles, and security for organization staff.</p>
        </div>
        {currentUser?.role === 'admin' && (
          <button 
            onClick={() => setIsModalOpen(true)}
            className="btn-primary flex items-center gap-2 px-6 py-3 shadow-lg shadow-indigo-100"
          >
            <Plus className="w-5 h-5" /> Add Team Member
          </button>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full sm:max-w-sm group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
          <input 
            type="text" 
            placeholder="Search users..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="input-field pl-10"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
          <button
            onClick={() => { setRoleFilter(''); setPage(1); }}
            className={cn(
              "px-4 py-2 rounded-lg text-xs font-bold transition-all border whitespace-nowrap",
              !roleFilter ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-slate-500 border-slate-200 hover:border-indigo-300"
            )}
          >
            All Roles
          </button>
          {ROLE_OPTIONS.map((role) => (
            <button
              key={role}
              onClick={() => { setRoleFilter(role); setPage(1); }}
              className={cn(
                "px-4 py-2 rounded-lg text-xs font-bold transition-all capitalize border whitespace-nowrap",
                roleFilter === role 
                  ? "bg-indigo-600 text-white border-indigo-600" 
                  : "bg-white text-slate-500 border-slate-200 hover:border-indigo-300"
              )}
            >
              {role.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="enterprise-card p-0 overflow-hidden shadow-xl bg-white/50 backdrop-blur-sm border-none">
        <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <div className="text-sm font-bold text-slate-400 uppercase tracking-widest">
            {pagination ? `${pagination.total} Organization Members` : 'Loading members...'}
          </div>
        </div>

        <div className="overflow-visible md:overflow-x-auto">
          <table className="w-full text-left border-collapse responsive-table">
            <thead>
              <tr className="bg-slate-50/30">
                <th className="table-header">User Profile</th>
                <th className="table-header">System Role</th>
                <th className="table-header">Access Status</th>
                <th className="table-header">Last Presence</th>
                <th className="table-header text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white/30 truncate">
              {isLoading ? (
                [1, 2, 3].map(i => <tr key={i} className="h-20 animate-pulse bg-slate-50/20" />)
              ) : (
                users?.map((user: any) => (
                  <tr key={user.id} className="table-row group">
                    <td className="table-cell" data-label="User Profile">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold relative overflow-hidden group-hover:scale-105 transition-transform flex-shrink-0">
                           {user.username.substring(0, 2).toUpperCase()}
                           <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 to-transparent" />
                        </div>
                        <div>
                          <p className="font-bold text-slate-900 leading-tight uppercase tracking-tight text-left">{user.username}</p>
                          <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5 text-left">
                             <Mail className="w-3 h-3" /> {user.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell md:text-left" data-label="System Role">
                      <select 
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                        disabled={user.id === currentUser?.id}
                        className="bg-white border border-slate-200 rounded-lg py-1 px-3 text-xs font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500/20 outline-none hover:border-indigo-300 transition-all disabled:opacity-50"
                        aria-label="Change user role"
                      >
                        {ROLE_OPTIONS.map(role => (
                          <option key={role} value={role}>{role.replace('_', ' ').toUpperCase()}</option>
                        ))}
                      </select>
                    </td>
                    <td className="table-cell md:text-left" data-label="Access Status">
                      <div className={cn(
                        "px-2.5 py-1 rounded-md text-[10px] font-bold border uppercase tracking-wider w-fit",
                        user.is_active ? "text-emerald-700 bg-emerald-50 border-emerald-100" : "text-slate-400 bg-slate-50 border-slate-200"
                      )}>
                        {user.is_active ? 'Authorized' : 'Suspended'}
                      </div>
                    </td>
                    <td className="table-cell text-xs text-slate-500 font-medium md:text-left" data-label="Last Presence">
                      {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never logged in'}
                    </td>
                    <td className="table-cell text-right" data-label="Actions">
                      <button 
                        onClick={() => handleToggleStatus(user.id, user.is_active)}
                        disabled={user.id === currentUser?.id}
                        className={cn(
                          "p-2 rounded-lg transition-all transform hover:scale-110 disabled:opacity-20",
                          user.is_active ? "text-rose-500 hover:bg-rose-50" : "text-emerald-500 hover:bg-emerald-50"
                        )}
                        title={user.is_active ? "Deactivate User" : "Activate User"}
                      >
                        {user.is_active ? <UserX className="w-5 h-5" /> : <UserCheck className="w-5 h-5" />}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {pagination && pagination.pages > 1 && (
        <div className="flex justify-center items-center gap-4 pt-8">
          <button 
            disabled={!pagination.has_prev}
            onClick={() => setPage(p => p - 1)}
            className="btn-secondary px-4 py-2 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm font-bold text-slate-600">
            Page {pagination.page} of {pagination.pages}
          </span>
          <button 
            disabled={!pagination.has_next}
            onClick={() => setPage(p => p + 1)}
            className="btn-secondary px-4 py-2 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Add User Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-[2rem] shadow-2xl w-full max-w-lg overflow-hidden border border-slate-100 animate-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <Plus className="text-brand-primary w-5 h-5" /> Add New Member
              </h2>
              <button onClick={() => setIsModalOpen(false)} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>
            
            <form onSubmit={handleCreateUser} className="p-8 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">First Name</label>
                  <input 
                    type="text"
                    required
                    value={newUser.first_name}
                    onChange={(e) => setNewUser({...newUser, first_name: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Last Name</label>
                  <input 
                    type="text"
                    required
                    value={newUser.last_name}
                    onChange={(e) => setNewUser({...newUser, last_name: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all text-sm"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Username</label>
                <input 
                  type="text"
                  required
                  value={newUser.username}
                  onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input 
                    type="email"
                    required
                    value={newUser.email}
                    onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Initial Password</label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input 
                      type="password"
                      required
                      value={newUser.password}
                      onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                      className="w-full pl-10 pr-4 py-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all text-sm"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">System Role</label>
                  <div className="relative">
                    <Shield className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <select 
                      value={newUser.role}
                      onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                      className="w-full pl-10 pr-4 py-3 bg-slate-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all text-sm appearance-none"
                    >
                      {ROLE_OPTIONS.map(role => (
                        <option key={role} value={role}>{role.toUpperCase()}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="pt-4 flex gap-4">
                <button 
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-3 bg-slate-100 text-slate-600 rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-slate-200 transition-all"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Create Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Users;
