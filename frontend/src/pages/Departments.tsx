import { useState } from 'react';
import { Plus, Search, Building2, MoreHorizontal, Edit, Trash2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDepartments, useCreateDepartment, useUpdateDepartment, useDeleteDepartment } from '../hooks/useDepartments';
import type { Department } from '../hooks/useDepartments';
import { useUsers } from '../hooks/useUsers';
import { Can } from '../components/auth/Can';
import { cn } from '../lib/utils';

interface DepartmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  department: Department | null;
}

const DepartmentModal = ({ isOpen, onClose, department }: DepartmentModalProps) => {
  const [formData, setFormData] = useState({
    name: department?.name || '',
    code: department?.code || '',
    description: department?.description || '',
    head_id: department?.head?.id || '' as number | '',
  });

  const createDept = useCreateDepartment();
  const updateDept = useUpdateDepartment();
  const { data: usersData, isLoading: usersLoading } = useUsers({ per_page: 100 } as any); // Load enough users for dropdown

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...formData,
      head_id: formData.head_id === '' ? null : Number(formData.head_id)
    };

    if (department) {
      updateDept.mutate({ id: department.id, data: payload }, {
        onSuccess: () => onClose()
      });
    } else {
      createDept.mutate(payload, {
        onSuccess: () => onClose()
      });
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-lg bg-white shadow-2xl rounded-3xl overflow-hidden border border-slate-200"
          >
            <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-black text-slate-900 text-lg tracking-tight">
                    {department ? 'Edit Department' : 'New Department'}
                  </h3>
                  <p className="text-xs font-black tracking-widest text-slate-400 uppercase">Institutional Division</p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 text-slate-400 hover:bg-slate-100 rounded-xl transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-black tracking-widest uppercase text-slate-500">Department Name <span className="text-rose-500">*</span></label>
                  <input
                    required
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/30 outline-none transition-all"
                    placeholder="e.g. IT Infrastructure"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs font-black tracking-widest uppercase text-slate-500">Department Code <span className="text-rose-500">*</span></label>
                  <input
                    required
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/30 outline-none transition-all uppercase"
                    placeholder="e.g. IT-INF"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-black tracking-widest uppercase text-slate-500">Head of Department</label>
                  <select
                    value={formData.head_id}
                    onChange={(e) => setFormData({ ...formData, head_id: e.target.value === '' ? '' : Number(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/30 outline-none transition-all"
                    disabled={usersLoading}
                  >
                    <option value="">-- Unassigned --</option>
                    {usersData?.users?.map(user => (
                      <option key={user.id} value={user.id}>
                        {user.first_name ? `${user.first_name} ${user.last_name}` : user.username}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-black tracking-widest uppercase text-slate-500">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/30 outline-none transition-all resize-none h-24 custom-scrollbar"
                    placeholder="Optional description..."
                  />
                </div>
              </div>
              
              <div className="pt-6 border-t border-slate-100 flex justify-end gap-3">
                <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-100 transition-colors">Cancel</button>
                <button 
                  type="submit" 
                  disabled={createDept.isPending || updateDept.isPending}
                  className="btn-primary"
                >
                  {createDept.isPending || updateDept.isPending ? 'Saving...' : 'Save Department'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

const Departments = () => {
  const [search, setSearch] = useState('');
  const { data: departments, isLoading } = useDepartments({ search: search || undefined });
  const deleteDept = useDeleteDepartment();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);

  const handleEdit = (dept: Department) => {
    setSelectedDept(dept);
    setIsModalOpen(true);
  };

  const handleCreate = () => {
    setSelectedDept(null);
    setIsModalOpen(true);
  };

  const handleDelete = (dept: Department) => {
    if (window.confirm(`Are you sure you want to delete ${dept.name}? This cannot be undone.`)) {
      deleteDept.mutate(dept.id);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter flex items-center gap-4" style={{ fontFamily: 'Outfit' }}>
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100 text-brand-primary">
              <Building2 className="w-8 h-8" />
            </div>
            Departments
          </h1>
          <p className="text-slate-500 font-medium tracking-tight text-lg ml-1">Manage institutional divisions and asset allocation.</p>
        </div>
        <Can roles={['admin']}>
          <button onClick={handleCreate} className="btn-primary flex items-center gap-2 group">
            <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-500" /> New Department
          </button>
        </Can>
      </div>

      <div className="glass-panel p-2 rounded-2xl border-slate-200/50 bg-white/40 flex items-center gap-4">
        <div className="relative flex-1 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors" />
          <input 
            type="text" 
            placeholder="Search departments..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-transparent rounded-xl py-2.5 pl-11 pr-4 text-sm font-bold focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 transition-all outline-none"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
           {[1, 2, 3, 4].map(i => <div key={i} className="h-64 bg-white rounded-3xl animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {departments?.map((dept: Department, index: number) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              key={dept.id}
              className="enterprise-card bg-white p-6 hover:-translate-y-1 transition-transform group flex flex-col"
            >
              <div className="flex justify-between items-start mb-6">
                <div className="flex gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-brand-50 group-hover:text-brand-primary transition-colors">
                    <Building2 className="w-7 h-7" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-slate-900 leading-tight">{dept.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                        {dept.code}
                      </span>
                      <span className="text-xs font-bold text-slate-500">
                        Head: {dept.head ? `${dept.head.first_name || dept.head.username}` : 'Unassigned'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 border-t border-slate-100 pt-6 mt-auto">
                <div className="flex flex-col">
                  <span className="text-2xl font-black text-slate-900">{dept.asset_count || 0}</span>
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Tracked Assets</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-2xl font-black text-slate-900">N/A</span>
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Active Staff</span>
                </div>
              </div>

              <Can roles={['admin']}>
                <div className="mt-6 flex gap-2">
                  <button 
                    onClick={() => handleEdit(dept)}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-xl text-xs font-bold transition-all"
                  >
                    <Edit className="w-4 h-4" /> Edit
                  </button>
                  <button 
                    onClick={() => handleDelete(dept)}
                    className={cn(
                      "px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center",
                      dept.asset_count > 0 
                        ? "bg-slate-50 text-slate-300 cursor-not-allowed" 
                        : "bg-rose-50 hover:bg-rose-100 text-rose-600"
                    )} 
                    disabled={dept.asset_count > 0 || deleteDept.isPending}
                    title={dept.asset_count > 0 ? "Cannot delete department with assigned assets" : "Delete department"}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Can>
            </motion.div>
          ))}
        </div>
      )}

      {isModalOpen && (
        <DepartmentModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          department={selectedDept} 
        />
      )}
    </div>
  );
};

export default Departments;
