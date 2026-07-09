import React, { useMemo, useState } from 'react';
import { useInventory } from '../hooks/useInventory';
import { useWarehouses } from '../hooks/useWarehouses';
import { useDepartments } from '../hooks/useDepartments';
import { useEmployees } from '../hooks/useEmployees';
import { useAssets } from '../hooks/useAssets';
import { issueItem, returnItem, listMovementHistory } from '../services/movements';
import { useToast } from '../context/ToastContext';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useWarehouse } from '../context/WarehouseContext';

const IssueReturn: React.FC = () => {
  const [departmentId, setDepartmentId] = useState<number | undefined>(undefined);
  const { activeWarehouseId } = useWarehouse();
  const { data: inventoryData } = useInventory({ per_page: 100, department_id: departmentId, ...(activeWarehouseId ? { warehouse_id: activeWarehouseId } : {}) });
  const items = inventoryData?.inventory || [];
  const { data: assetsData } = useAssets({ per_page: 100, department_id: departmentId, ...(activeWarehouseId ? { warehouse_id: activeWarehouseId } : {}) });
  const assets = assetsData?.assets || [];
  const { data: warehouses = [] } = useWarehouses();
  const { data: departments = [] } = useDepartments(activeWarehouseId ? { warehouse_id: activeWarehouseId } : {});
  const { data: employees = [] } = useEmployees();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['movements-history', departmentId],
    queryFn: () => listMovementHistory({ department_id: departmentId, per_page: 100 }),
  });

  const issueMutation = useMutation({
    mutationFn: (payload: any) => issueItem(payload),
    onSuccess: () => {
      addToast('success', 'Issued', 'Movement recorded successfully');
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['movements-history'] });
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.message || err?.message;
      const message = typeof detail === 'string' && detail.length > 0 && !detail.toLowerCase().includes('traceback') && !detail.toLowerCase().includes('sqlalchemy')
        ? detail
        : 'We could not complete the issue request. Please verify the selected item, department, warehouse, and employee and try again.';
      addToast('error', 'Issue failed', message);
    },
  });

  const returnMutation = useMutation({
    mutationFn: (payload: any) => returnItem(payload),
    onSuccess: () => {
      addToast('success', 'Returned', 'Movement recorded successfully');
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['movements-history'] });
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.message || err?.message;
      const message = typeof detail === 'string' && detail.length > 0 && !detail.toLowerCase().includes('traceback') && !detail.toLowerCase().includes('sqlalchemy')
        ? detail
        : 'We could not complete the return request. Please verify the selected item, department, warehouse, and employee and try again.';
      addToast('error', 'Return failed', message);
    },
  });

  const [issueForm, setIssueForm] = useState({ item_type: 'inventory' as 'inventory' | 'asset', item_id: undefined as number|undefined, asset_id: undefined as number|undefined, from_warehouse_id: undefined as number|undefined, to_department_id: undefined as number|undefined, employee_id: undefined as number|undefined, quantity: 1, reference: '', notes: '' });
  const [returnForm, setReturnForm] = useState({ item_type: 'inventory' as 'inventory' | 'asset', item_id: undefined as number|undefined, asset_id: undefined as number|undefined, from_department_id: undefined as number|undefined, to_warehouse_id: undefined as number|undefined, employee_id: undefined as number|undefined, quantity: 1, condition: 'good', remarks: '', reference: '' });

  const issueDepartments = issueForm.from_warehouse_id
    ? departments.filter((d:any) => d.warehouse_id == null || d.warehouse_id === issueForm.from_warehouse_id)
    : departments;

  const filteredIssueEmployees = issueForm.to_department_id
    ? employees.filter((emp:any) => emp.department_id === issueForm.to_department_id)
    : employees;

  const filteredReturnEmployees = returnForm.from_department_id
    ? employees.filter((emp:any) => emp.department_id === returnForm.from_department_id)
    : employees;

  const selectedIssueLabel = useMemo(() => {
    if (issueForm.item_type === 'asset') {
      return assets.find((asset:any) => asset.id === issueForm.asset_id)?.name || 'Selected asset';
    }
    return items.find((item:any) => item.id === issueForm.item_id)?.name || 'Selected inventory item';
  }, [assets, issueForm.asset_id, issueForm.item_id, issueForm.item_type, items]);

  const selectedReturnLabel = useMemo(() => {
    if (returnForm.item_type === 'asset') {
      return assets.find((asset:any) => asset.id === returnForm.asset_id)?.name || 'Selected asset';
    }
    return items.find((item:any) => item.id === returnForm.item_id)?.name || 'Selected inventory item';
  }, [assets, returnForm.asset_id, returnForm.item_id, returnForm.item_type, items]);

  const submitIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueForm.from_warehouse_id || !issueForm.to_department_id || !issueForm.employee_id || issueForm.quantity <= 0 || (issueForm.item_type === 'asset' ? !issueForm.asset_id : !issueForm.item_id)) {
      addToast('error', 'Validation', 'Please fill the movement details completely');
      return;
    }
    issueMutation.mutate({ ...issueForm, item_id: issueForm.item_type === 'inventory' ? issueForm.item_id : undefined, asset_id: issueForm.item_type === 'asset' ? issueForm.asset_id : undefined }, {
      onSuccess: () => setIssueForm({ item_type: 'inventory', item_id: undefined, asset_id: undefined, from_warehouse_id: undefined, to_department_id: undefined, employee_id: undefined, quantity: 1, reference: '', notes: '' }),
    });
  };

  const submitReturn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!returnForm.from_department_id || !returnForm.to_warehouse_id || !returnForm.employee_id || returnForm.quantity <= 0 || (returnForm.item_type === 'asset' ? !returnForm.asset_id : !returnForm.item_id)) {
      addToast('error', 'Validation', 'Please fill the movement details completely');
      return;
    }
    returnMutation.mutate({ ...returnForm, item_id: returnForm.item_type === 'inventory' ? returnForm.item_id : undefined, asset_id: returnForm.item_type === 'asset' ? returnForm.asset_id : undefined }, {
      onSuccess: () => setReturnForm({ item_type: 'inventory', item_id: undefined, asset_id: undefined, from_department_id: undefined, to_warehouse_id: undefined, employee_id: undefined, quantity: 1, condition: 'good', remarks: '', reference: '' }),
    });
  };

  const issueHistory = Array.isArray(historyData?.issues) ? historyData.issues : (historyData?.history || []).filter((row:any) => row.movement_type === 'issue');
  const returnHistory = Array.isArray(historyData?.returns) ? historyData.returns : (historyData?.history || []).filter((row:any) => row.movement_type === 'return');

  return (
    <div className="space-y-6">
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-semibold">Scope by department:</label>
        <select className="input-field" value={departmentId ?? ''} onChange={(e)=>setDepartmentId(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">All Departments</option>
          {departments.map((d:any)=>(<option key={d.id} value={d.id}>{d.name}</option>))}
        </select>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded shadow">
          <h3 className="font-semibold mb-2">Issue Item</h3>
          <form onSubmit={submitIssue} className="space-y-3">
            <div>
              <label>Movement Type</label>
              <select className="input-field w-full" value={issueForm.item_type} onChange={e => setIssueForm({ ...issueForm, item_type: e.target.value as 'inventory' | 'asset', item_id: undefined, asset_id: undefined })}>
                <option value="inventory">Inventory Item</option>
                <option value="asset">Asset</option>
              </select>
            </div>
            <div>
              <label>{issueForm.item_type === 'asset' ? 'Asset' : 'Inventory Item'}</label>
              <select className="input-field w-full" value={issueForm.item_type === 'asset' ? issueForm.asset_id ?? '' : issueForm.item_id ?? ''} onChange={e => issueForm.item_type === 'asset' ? setIssueForm({ ...issueForm, asset_id: e.target.value ? Number(e.target.value) : undefined }) : setIssueForm({ ...issueForm, item_id: e.target.value ? Number(e.target.value) : undefined })}>
                <option value="">Select</option>
                {(issueForm.item_type === 'asset' ? assets : items).map((entry:any) => (<option key={entry.id} value={entry.id}>{entry.name}</option>))}
              </select>
            </div>
            <div>
              <label>From Warehouse</label>
              <select className="input-field w-full" value={issueForm.from_warehouse_id ?? ''} onChange={e => { const warehouseId = e.target.value ? Number(e.target.value) : undefined; const validDepartments = warehouseId ? departments.filter((d:any) => d.warehouse_id == null || d.warehouse_id === warehouseId) : departments; const validDepartmentIds = new Set(validDepartments.map((d:any) => d.id)); setIssueForm({ ...issueForm, from_warehouse_id: warehouseId, to_department_id: issueForm.to_department_id && validDepartmentIds.has(issueForm.to_department_id) ? issueForm.to_department_id : undefined, employee_id: issueForm.employee_id && issueForm.to_department_id && validDepartmentIds.has(issueForm.to_department_id) ? issueForm.employee_id : undefined }); }}>
                <option value="">Select</option>
                {warehouses.map((w:any)=>(<option key={w.id} value={w.id}>{w.name}</option>))}
              </select>
            </div>
            <div>
              <label>To Department</label>
              <select className="input-field w-full" value={issueForm.to_department_id ?? ''} onChange={e => { const deptId = e.target.value ? Number(e.target.value) : undefined; setIssueForm({ ...issueForm, to_department_id: deptId, employee_id: deptId && issueForm.employee_id && filteredIssueEmployees.every((emp:any) => emp.id !== issueForm.employee_id) ? undefined : issueForm.employee_id }); }}>
                <option value="">Select</option>
                {issueDepartments.map((d:any)=>(<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
            </div>
            <div>
              <label>Employee</label>
              <select className="input-field w-full" value={issueForm.employee_id ?? ''} onChange={e => setIssueForm({ ...issueForm, employee_id: e.target.value ? Number(e.target.value) : undefined })}>
                <option value="">Select</option>
                {filteredIssueEmployees.map((emp:any)=>(<option key={emp.id} value={emp.id}>{emp.name}</option>))}
              </select>
            </div>
            <div>
              <label>Quantity</label>
              <input type="number" min={1} value={issueForm.quantity} onChange={e => setIssueForm({ ...issueForm, quantity: Number(e.target.value) })} className="input-field w-full" />
            </div>
            <div className="text-sm text-gray-600">Selected: {selectedIssueLabel}</div>
            <div>
              <label>Reference</label>
              <input className="input-field w-full" value={issueForm.reference} onChange={e => setIssueForm({ ...issueForm, reference: e.target.value })} />
            </div>
            <div>
              <label>Notes</label>
              <textarea className="input-field w-full" rows={3} value={issueForm.notes} onChange={e => setIssueForm({ ...issueForm, notes: e.target.value })} />
            </div>
            <div>
              <button className="btn btn-primary" disabled={issueMutation.status === 'pending'}>{issueMutation.status === 'pending' ? 'Recording...' : 'Issue'}</button>
            </div>
          </form>
        </div>

        <div className="bg-white p-4 rounded shadow">
          <h3 className="font-semibold mb-2">Return Item</h3>
          <form onSubmit={submitReturn} className="space-y-3">
            <div>
              <label>Movement Type</label>
              <select className="input-field w-full" value={returnForm.item_type} onChange={e => setReturnForm({ ...returnForm, item_type: e.target.value as 'inventory' | 'asset', item_id: undefined, asset_id: undefined })}>
                <option value="inventory">Inventory Item</option>
                <option value="asset">Asset</option>
              </select>
            </div>
            <div>
              <label>{returnForm.item_type === 'asset' ? 'Asset' : 'Inventory Item'}</label>
              <select className="input-field w-full" value={returnForm.item_type === 'asset' ? returnForm.asset_id ?? '' : returnForm.item_id ?? ''} onChange={e => returnForm.item_type === 'asset' ? setReturnForm({ ...returnForm, asset_id: e.target.value ? Number(e.target.value) : undefined }) : setReturnForm({ ...returnForm, item_id: e.target.value ? Number(e.target.value) : undefined })}>
                <option value="">Select</option>
                {(returnForm.item_type === 'asset' ? assets : items).map((entry:any) => (<option key={entry.id} value={entry.id}>{entry.name}</option>))}
              </select>
            </div>
            <div>
              <label>From Department</label>
              <select className="input-field w-full" value={returnForm.from_department_id ?? ''} onChange={e => { const deptId = e.target.value ? Number(e.target.value) : undefined; setReturnForm({ ...returnForm, from_department_id: deptId, employee_id: deptId && returnForm.employee_id && filteredReturnEmployees.every((emp:any) => emp.id !== returnForm.employee_id) ? undefined : returnForm.employee_id }); }}>
                <option value="">Select</option>
                {departments.map((d:any)=>(<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
            </div>
            <div>
              <label>To Warehouse</label>
              <select className="input-field w-full" value={returnForm.to_warehouse_id ?? ''} onChange={e => setReturnForm({ ...returnForm, to_warehouse_id: e.target.value ? Number(e.target.value) : undefined })}>
                <option value="">Select</option>
                {warehouses.map((w:any)=>(<option key={w.id} value={w.id}>{w.name}</option>))}
              </select>
            </div>
            <div>
              <label>Employee</label>
              <select className="input-field w-full" value={returnForm.employee_id ?? ''} onChange={e => setReturnForm({ ...returnForm, employee_id: e.target.value ? Number(e.target.value) : undefined })}>
                <option value="">Select</option>
                {filteredReturnEmployees.map((emp:any)=>(<option key={emp.id} value={emp.id}>{emp.name}</option>))}
              </select>
            </div>
            <div>
              <label>Quantity</label>
              <input type="number" min={1} value={returnForm.quantity} onChange={e => setReturnForm({ ...returnForm, quantity: Number(e.target.value) })} className="input-field w-full" />
            </div>
            <div className="text-sm text-gray-600">Selected: {selectedReturnLabel}</div>
            <div>
              <label>Condition</label>
              <select className="input-field w-full" value={returnForm.condition} onChange={e => setReturnForm({ ...returnForm, condition: e.target.value })}>
                <option value="good">Good</option>
                <option value="damaged">Damaged</option>
                <option value="worn">Worn</option>
                <option value="partial">Partial</option>
              </select>
            </div>
            <div>
              <label>Reference</label>
              <input className="input-field w-full" value={returnForm.reference} onChange={e => setReturnForm({ ...returnForm, reference: e.target.value })} />
            </div>
            <div>
              <label>Remarks</label>
              <textarea className="input-field w-full" rows={3} value={returnForm.remarks} onChange={e => setReturnForm({ ...returnForm, remarks: e.target.value })} />
            </div>
            <div>
              <button className="btn btn-primary" disabled={returnMutation.status === 'pending'}>{returnMutation.status === 'pending' ? 'Recording...' : 'Return'}</button>
            </div>
          </form>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded shadow overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h3 className="font-semibold">Issued item history</h3>
            <p className="text-sm text-gray-600">Items issued from warehouses to departments and employees.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Item</th>
                  <th className="px-3 py-2 text-left">Department</th>
                  <th className="px-3 py-2 text-left">Warehouse</th>
                  <th className="px-3 py-2 text-left">Employee</th>
                  <th className="px-3 py-2 text-left">Qty</th>
                  <th className="px-3 py-2 text-left">Reference</th>
                  <th className="px-3 py-2 text-left">Handled by</th>
                </tr>
              </thead>
              <tbody>
                {historyLoading ? (
                  <tr><td className="px-3 py-4" colSpan={8}>Loading issued item history…</td></tr>
                ) : issueHistory.length === 0 ? (
                  <tr><td className="px-3 py-4" colSpan={8}>No issued item history found.</td></tr>
                ) : issueHistory.map((row:any) => (
                  <tr key={`issue-${row.id}`} className="border-t">
                    <td className="px-3 py-2">{row.issued_date || row.created_at || '—'}</td>
                    <td className="px-3 py-2">{row.item_name || `${row.item_type} #${row.item_id || row.asset_id}`}</td>
                    <td className="px-3 py-2">{row.to_department_name || '—'}</td>
                    <td className="px-3 py-2">{row.from_warehouse_name || '—'}</td>
                    <td className="px-3 py-2">{row.employee_name || '—'}</td>
                    <td className="px-3 py-2">{row.quantity}</td>
                    <td className="px-3 py-2">{row.reference || '—'}</td>
                    <td className="px-3 py-2">{row.performed_by || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded shadow overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h3 className="font-semibold">Returned item history</h3>
            <p className="text-sm text-gray-600">Items returned from departments back to warehouses.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Item</th>
                  <th className="px-3 py-2 text-left">Department</th>
                  <th className="px-3 py-2 text-left">Warehouse</th>
                  <th className="px-3 py-2 text-left">Employee</th>
                  <th className="px-3 py-2 text-left">Qty</th>
                  <th className="px-3 py-2 text-left">Condition</th>
                  <th className="px-3 py-2 text-left">Reference</th>
                  <th className="px-3 py-2 text-left">Handled by</th>
                </tr>
              </thead>
              <tbody>
                {historyLoading ? (
                  <tr><td className="px-3 py-4" colSpan={9}>Loading returned item history…</td></tr>
                ) : returnHistory.length === 0 ? (
                  <tr><td className="px-3 py-4" colSpan={9}>No returned item history found.</td></tr>
                ) : returnHistory.map((row:any) => (
                  <tr key={`return-${row.id}`} className="border-t">
                    <td className="px-3 py-2">{row.return_date || row.created_at || '—'}</td>
                    <td className="px-3 py-2">{row.item_name || `${row.item_type} #${row.item_id || row.asset_id}`}</td>
                    <td className="px-3 py-2">{row.from_department_name || '—'}</td>
                    <td className="px-3 py-2">{row.to_warehouse_name || '—'}</td>
                    <td className="px-3 py-2">{row.employee_name || '—'}</td>
                    <td className="px-3 py-2">{row.quantity}</td>
                    <td className="px-3 py-2">{row.condition || '—'}</td>
                    <td className="px-3 py-2">{row.reference || '—'}</td>
                    <td className="px-3 py-2">{row.performed_by || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IssueReturn;
