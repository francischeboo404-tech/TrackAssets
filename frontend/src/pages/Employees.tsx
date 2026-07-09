import React, { useState, useEffect } from 'react';
import { useEmployees, useCreateEmployee, useUpdateEmployee, useDeleteEmployee } from '../hooks/useEmployees';
import { useDepartments } from '../hooks/useDepartments';
import { Link } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import Spinner from '../components/ui/Spinner';
import { useWarehouse } from '../context/WarehouseContext';

const Employees: React.FC = () => {
  const [page, setPage] = useState<number>(1);
  const [perPage, setPerPage] = useState<number>(10);
  const [search, setSearch] = useState<string>('');
  const [sort, setSort] = useState<string>('name');
  const [departmentFilter, setDepartmentFilter] = useState<number | undefined>(undefined);
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, isLoading } = useEmployees({ page, per_page: perPage, q: debouncedSearch || undefined, sort, department_id: departmentFilter });
  const employees = data?.employees || [];
  const pagination = data?.pagination || { page: 1, per_page: perPage, total: 0 };
  const { activeWarehouseId } = useWarehouse();
  const { data: departments = [] } = useDepartments(activeWarehouseId ? { warehouse_id: activeWarehouseId } : {});
  const createEmployee = useCreateEmployee();
  const updateEmployee = useUpdateEmployee();
  const deleteEmployee = useDeleteEmployee();
  const { addToast } = useToast();

  const [form, setForm] = useState({ name: '', code: '', email: '', phone: '', department_id: undefined as number | undefined });
  const [editing, setEditing] = useState<null | any>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.code || !form.department_id) {
      addToast('error', 'Validation', 'Name, code and department are required');
      return;
    }
    createEmployee.mutate({ name: form.name, code: form.code, email: form.email, phone: form.phone, department_id: form.department_id }, {
      onSuccess: () => setForm({ name: '', code: '', email: '', phone: '', department_id: undefined }),
    });
  };

  const startEdit = (emp: any) => {
    setEditing(emp);
    setForm({ name: emp.name, code: emp.code, email: emp.email || '', phone: emp.phone || '', department_id: emp.department_id });
  };

  const submitEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    if (!form.department_id) {
      addToast('error', 'Validation', 'Department is required');
      return;
    }
    updateEmployee.mutate({ id: editing.id, data: { name: form.name, email: form.email, phone: form.phone, department_id: form.department_id } }, {
      onSuccess: () => setEditing(null),
    });
  };

  const confirmDelete = (id: number) => setConfirmDeleteId(id);

  const doDelete = () => {
    if (!confirmDeleteId) return;
    setDeletingId(confirmDeleteId);
    deleteEmployee.mutate(confirmDeleteId, {
      onSettled: () => {
        setDeletingId(null);
        setConfirmDeleteId(null);
      }
    });
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-semibold mb-4">Employees</h2>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <form onSubmit={submit} className="space-y-3 bg-white p-4 rounded shadow">
            <div>
              <label className="block text-sm">Name</label>
              <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="input-field w-full" />
            </div>
            <div>
              <label className="block text-sm">Code</label>
              <input value={form.code} onChange={e => setForm({...form, code: e.target.value})} className="input-field w-full" />
            </div>
            <div>
              <label className="block text-sm">Email</label>
              <input value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="input-field w-full" />
            </div>
            <div>
              <label className="block text-sm">Phone</label>
              <input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} className="input-field w-full" />
            </div>
            <div>
              <label className="block text-sm">Department</label>
              <select value={form.department_id ?? ''} onChange={e => setForm({...form, department_id: e.target.value ? Number(e.target.value) : undefined})} className="input-field w-full">
                <option value="">Select</option>
                {departments.map((d:any) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <button type="submit" className="btn btn-primary" disabled={createEmployee.status === 'pending'}>
                {createEmployee.status === 'pending' ? 'Creating...' : 'Create Employee'}
              </button>
            </div>
          </form>
        </div>
        <div>
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-semibold mb-2">Employee List</h3>
            <div className="flex gap-2 mb-3">
              <div className="flex items-center gap-2 flex-1">
                <input placeholder="Search by name, code, email" value={search} onChange={e=>{ setSearch(e.target.value); setPage(1); }} className="input-field flex-1" />
                {search !== debouncedSearch && (
                  <Spinner size="sm" className="ml-2" ariaLabel="Searching" />
                )}
              </div>
              <select value={departmentFilter ?? ''} onChange={e=>{ setDepartmentFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1); }} className="input-field w-44">
                <option value="">All departments</option>
                {departments.map((d:any)=><option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
              <select value={sort} onChange={e=>{ setSort(e.target.value); setPage(1); }} className="input-field w-44">
                <option value="name">Name ↑</option>
                <option value="-name">Name ↓</option>
                <option value="code">Code ↑</option>
                <option value="-code">Code ↓</option>
                <option value="date_of_join">Joined ↑</option>
                <option value="-date_of_join">Joined ↓</option>
              </select>
            </div>
            {isLoading ? <div>Loading...</div> : (
              <ul>
                {employees.map((emp:any) => (
                  <li key={emp.id} className="py-1 border-b flex items-center justify-between">
                    <div>
                      <Link to={`/employees/${emp.id}`} className="font-medium text-brand-primary hover:underline">{emp.name}</Link>
                      <div className="text-xs text-slate-500">{emp.code} — {departments.find((d:any)=>d.id===emp.department_id)?.name || emp.department_name || emp.department_id}</div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => startEdit(emp)} className="btn btn-sm" disabled={updateEmployee.status === 'pending'}>
                        {updateEmployee.status === 'pending' && editing?.id === emp.id ? 'Saving...' : 'Edit'}
                      </button>
                      <button onClick={() => confirmDelete(emp.id)} className="btn btn-ghost btn-sm text-rose-600" disabled={deletingId === emp.id}>
                        {deletingId === emp.id || (deleteEmployee.status === 'pending' && deletingId === emp.id) ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3 flex items-center justify-between">
              <div className="text-sm text-slate-600">Showing {Math.min((page-1)*perPage+1, pagination.total)} - {Math.min(page*perPage, pagination.total)} of {pagination.total}</div>
              <div className="flex items-center gap-2">
                <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }} className="input-field">
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
                <button className="btn btn-sm" onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}>Prev</button>
                <button className="btn btn-sm" onClick={() => { if ((page * perPage) < pagination.total) setPage(p => p+1); }} disabled={page * perPage >= pagination.total}>Next</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded shadow w-[480px]">
            <h3 className="font-semibold mb-3">Edit Employee</h3>
            <form onSubmit={submitEdit} className="space-y-3">
              <div>
                <label className="block text-sm">Name</label>
                <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-sm">Code</label>
                <input value={form.code} onChange={e => setForm({...form, code: e.target.value})} disabled className="input-field w-full bg-slate-100" />
              </div>
              <div>
                <label className="block text-sm">Email</label>
                <input value={form.email} onChange={e => setForm({...form, email: e.target.value})} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-sm">Phone</label>
                <input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} className="input-field w-full" />
              </div>
              <div>
                <label className="block text-sm">Department</label>
                <select value={form.department_id ?? ''} onChange={e => setForm({...form, department_id: e.target.value ? Number(e.target.value) : undefined})} className="input-field w-full">
                  <option value="">Select</option>
                  {departments.map((d:any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={() => setEditing(null)} className="btn">Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={updateEmployee.status === 'pending'}>{updateEmployee.status === 'pending' ? 'Saving...' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded shadow w-[420px]">
            <h3 className="font-semibold mb-3">Confirm Delete</h3>
            <p className="mb-4">Are you sure you want to delete this employee? This action will soft-delete the record.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmDeleteId(null)} className="btn" disabled={deleteEmployee.status === 'pending' || deletingId !== null}>Cancel</button>
              <button onClick={doDelete} className="btn btn-rose" disabled={deleteEmployee.status === 'pending' || deletingId !== null}>{deleteEmployee.status === 'pending' || deletingId !== null ? 'Deleting...' : 'Delete'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Employees;
