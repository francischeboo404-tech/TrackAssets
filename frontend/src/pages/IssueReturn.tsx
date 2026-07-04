import React, { useState } from 'react';
import { useInventory } from '../hooks/useInventory';
import { useWarehouses } from '../hooks/useWarehouses';
import { useDepartments } from '../hooks/useDepartments';
import { useEmployees } from '../hooks/useEmployees';
import { issueItem, returnItem } from '../services/movements';
import { useToast } from '../context/ToastContext';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const IssueReturn: React.FC = () => {
  const [departmentId, setDepartmentId] = useState<number | undefined>(undefined);
  const { data: inventoryData } = useInventory({ per_page: 100, department_id: departmentId });
  const items = inventoryData?.inventory || [];
  const { data: warehouses = [] } = useWarehouses();
  const { data: departments = [] } = useDepartments();
  const { data: employees = [] } = useEmployees();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const issueMutation = useMutation({
    mutationFn: (payload: any) => issueItem(payload),
    onSuccess: () => {
      addToast('success', 'Issued', 'Item issued successfully');
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
    onError: (err: any) => addToast('error', 'Issue failed', err.response?.data?.message || err.message),
  });

  const returnMutation = useMutation({
    mutationFn: (payload: any) => returnItem(payload),
    onSuccess: () => {
      addToast('success', 'Returned', 'Item returned successfully');
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
    onError: (err: any) => addToast('error', 'Return failed', err.response?.data?.message || err.message),
  });

  const [issueForm, setIssueForm] = useState({ item_id: undefined as number|undefined, from_warehouse_id: undefined as number|undefined, to_department_id: undefined as number|undefined, employee_id: undefined as number|undefined, quantity: 1, reference: '', notes: '' });
  const [returnForm, setReturnForm] = useState({ item_id: undefined as number|undefined, from_department_id: undefined as number|undefined, to_warehouse_id: undefined as number|undefined, employee_id: undefined as number|undefined, quantity: 1, condition: 'good', remarks: '', reference: '' });

  const issueDepartments = issueForm.from_warehouse_id
    ? departments.filter((d:any) => d.warehouse_id == null || d.warehouse_id === issueForm.from_warehouse_id)
    : departments;

  const filteredIssueEmployees = issueForm.to_department_id
    ? employees.filter((emp:any) => emp.department_id === issueForm.to_department_id)
    : employees;

  const filteredReturnEmployees = returnForm.from_department_id
    ? employees.filter((emp:any) => emp.department_id === returnForm.from_department_id)
    : employees;

  const submitIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    // Validation
    if (!issueForm.item_id || !issueForm.from_warehouse_id || !issueForm.to_department_id || !issueForm.employee_id || issueForm.quantity <= 0) {
      addToast('error', 'Validation', 'Please fill item, warehouse, department, employee and quantity');
      return;
    }
    issueMutation.mutate(issueForm as any, { onSuccess: () => setIssueForm({ item_id: undefined, from_warehouse_id: undefined, to_department_id: undefined, employee_id: undefined, quantity: 1, reference: '', notes: '' }) });
  };

  const submitReturn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!returnForm.item_id || !returnForm.from_department_id || !returnForm.to_warehouse_id || !returnForm.employee_id || returnForm.quantity <= 0) {
      addToast('error', 'Validation', 'Please fill item, department, warehouse, employee and quantity');
      return;
    }
    returnMutation.mutate(returnForm as any, { onSuccess: () => setReturnForm({ item_id: undefined, from_department_id: undefined, to_warehouse_id: undefined, employee_id: undefined, quantity: 1, condition: 'good', remarks: '', reference: '' }) });
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-semibold">Scope by department:</label>
        <select className="input-field" value={departmentId ?? ''} onChange={(e)=>setDepartmentId(e.target.value?Number(e.target.value):undefined)}>
          <option value="">All Departments</option>
          {departments.map((d:any)=>(<option key={d.id} value={d.id}>{d.name}</option>))}
        </select>
      </div>

      <div className="p-4 grid grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded shadow">
          <h3 className="font-semibold mb-2">Issue Item</h3>
          <form onSubmit={submitIssue} className="space-y-3">
            <div>
              <label>Item</label>
              <select className="input-field w-full" value={issueForm.item_id ?? ''} onChange={e=>setIssueForm({...issueForm, item_id: e.target.value ? Number(e.target.value) : undefined})}>
                <option value="">Select</option>
                {items.map((it:any) => (<option key={it.id} value={it.id}>{it.name}</option>))}
              </select>
            </div>

            <div>
              <label>From Warehouse</label>
              <select
                className="input-field w-full"
                value={issueForm.from_warehouse_id ?? ''}
                onChange={e=>{
                  const warehouseId = e.target.value ? Number(e.target.value) : undefined;
                  const validDepartments = warehouseId
                    ? departments.filter((d:any) => d.warehouse_id == null || d.warehouse_id === warehouseId)
                    : departments;
                  const validDepartmentIds = new Set(validDepartments.map((d:any) => d.id));

                  setIssueForm({
                    ...issueForm,
                    from_warehouse_id: warehouseId,
                    to_department_id: issueForm.to_department_id && validDepartmentIds.has(issueForm.to_department_id)
                      ? issueForm.to_department_id
                      : undefined,
                    employee_id: issueForm.employee_id && issueForm.to_department_id && validDepartmentIds.has(issueForm.to_department_id)
                      ? issueForm.employee_id
                      : undefined,
                  });
                }}
              >
                <option value="">Select</option>
                {warehouses.map((w:any)=>(<option key={w.id} value={w.id}>{w.name}</option>))}
              </select>
            </div>

            <div>
              <label>To Department</label>
              <select className="input-field w-full" value={issueForm.to_department_id ?? ''} onChange={e=>{
                const deptId = e.target.value ? Number(e.target.value) : undefined;
                setIssueForm({
                  ...issueForm,
                  to_department_id: deptId,
                  employee_id: deptId && issueForm.employee_id && filteredIssueEmployees.every((emp:any) => emp.id !== issueForm.employee_id) ? undefined : issueForm.employee_id,
                });
              }}>
                <option value="">Select</option>
                {issueDepartments.map((d:any)=>(<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
            </div>

            <div>
              <label>Employee</label>
              <select className="input-field w-full" value={issueForm.employee_id ?? ''} onChange={e=>setIssueForm({...issueForm, employee_id: e.target.value ? Number(e.target.value) : undefined})}>
                <option value="">Select</option>
                {filteredIssueEmployees.map((emp:any)=>(<option key={emp.id} value={emp.id}>{emp.name}</option>))}
              </select>
            </div>

            <div>
              <label>Quantity</label>
              <input type="number" min={1} value={issueForm.quantity} onChange={e=>setIssueForm({...issueForm, quantity: Number(e.target.value)})} className="input-field w-full" />
            </div>

            <div>
              <button className="btn btn-primary" disabled={issueMutation.status === 'pending'}>{issueMutation.status === 'pending' ? 'Issuing...' : 'Issue'}</button>
            </div>
          </form>
        </div>

        <div className="bg-white p-4 rounded shadow">
          <h3 className="font-semibold mb-2">Return Item</h3>
          <form onSubmit={submitReturn} className="space-y-3">
            <div>
              <label>Item</label>
              <select className="input-field w-full" value={returnForm.item_id ?? ''} onChange={e=>setReturnForm({...returnForm, item_id: e.target.value ? Number(e.target.value) : undefined})}>
                <option value="">Select</option>
                {items.map((it:any) => (<option key={it.id} value={it.id}>{it.name}</option>))}
              </select>
            </div>

            <div>
              <label>From Department</label>
              <select className="input-field w-full" value={returnForm.from_department_id ?? ''} onChange={e=>{
                const deptId = e.target.value ? Number(e.target.value) : undefined;
                setReturnForm({
                  ...returnForm,
                  from_department_id: deptId,
                  employee_id: deptId && returnForm.employee_id && filteredReturnEmployees.every((emp:any) => emp.id !== returnForm.employee_id) ? undefined : returnForm.employee_id,
                });
              }}>
                <option value="">Select</option>
                {departments.map((d:any)=>(<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
            </div>

            <div>
              <label>To Warehouse</label>
              <select className="input-field w-full" value={returnForm.to_warehouse_id ?? ''} onChange={e=>setReturnForm({...returnForm, to_warehouse_id: e.target.value ? Number(e.target.value) : undefined})}>
                <option value="">Select</option>
                {warehouses.map((w:any)=>(<option key={w.id} value={w.id}>{w.name}</option>))}
              </select>
            </div>

            <div>
              <label>Employee</label>
              <select className="input-field w-full" value={returnForm.employee_id ?? ''} onChange={e=>setReturnForm({...returnForm, employee_id: e.target.value ? Number(e.target.value) : undefined})}>
                <option value="">Select</option>
                {filteredReturnEmployees.map((emp:any)=>(<option key={emp.id} value={emp.id}>{emp.name}</option>))}
              </select>
            </div>

            <div>
              <label>Quantity</label>
              <input type="number" min={1} value={returnForm.quantity} onChange={e=>setReturnForm({...returnForm, quantity: Number(e.target.value)})} className="input-field w-full" />
            </div>

            <div>
              <button className="btn btn-primary" disabled={returnMutation.status === 'pending'}>{returnMutation.status === 'pending' ? 'Returning...' : 'Return'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default IssueReturn;
