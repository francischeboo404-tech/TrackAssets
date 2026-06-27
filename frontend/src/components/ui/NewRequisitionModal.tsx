import React, { useEffect, useMemo, useState } from 'react'
import { Modal } from './Modal'
import { useCreateRequisition } from '../../hooks/useRequisitions'
import { useToast } from '../../context/ToastContext'
import { useAuth } from '../../context/AuthContext'
import { useInventory } from '../../hooks/useInventory'
import { useWarehouses, useWarehouseBins } from '../../hooks/useWarehouses'
import { usePurchaseRequests } from '../../hooks/useProcurement'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

interface Props {
  isOpen: boolean
  onClose: () => void
}

type PickedItem = {
  id: number
  name?: string
  sku?: string
  unit?: string
  unit_price?: number
  quantity: number
  quantity_issued?: number
  unit_cost?: number
  available?: number
  bin_id?: number | null
}

export const NewRequisitionModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [selected, setSelected] = useState<PickedItem[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [warehouseId, setWarehouseId] = useState<number | null>(null)
  const [prId, setPrId] = useState("")

  const create = useCreateRequisition()
  const { addToast } = useToast()
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  const { data: prsData } = usePurchaseRequests() as any;
  const rawPRs = Array.isArray(prsData?.purchase_requests) ? prsData.purchase_requests : (Array.isArray(prsData) ? prsData : []);
  const purchaseRequests = rawPRs.filter((pr: any) => pr.status === 'approved');

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 250)
    return () => clearTimeout(t)
  }, [search])

  // useInventory returns { inventory, pagination }
  const inventoryQuery = useInventory({ search: debounced, per_page: 10, warehouse_id: warehouseId ?? undefined })
  const suggestions = useMemo(() => inventoryQuery.data?.inventory || [], [inventoryQuery.data])
  const { data: warehousesData } = useWarehouses()

  const addItem = (itm: any) => {
    // avoid duplicates
    if (selected.find((s) => s.id === itm.id)) return
    const available = itm.quantity_available ?? itm.quantity_on_hand ?? itm.quantity ?? 0
    setSelected((s) => [...s, { id: itm.id, name: itm.name, sku: itm.sku, unit: itm.unit, unit_price: itm.unit_price, quantity: 1, quantity_issued: 0, unit_cost: itm.unit_price || 0, available }])
    setSearch('')
  }

  // when warehouse selection changes, refresh availability for selected items
  useEffect(() => {
    if (warehouseId == null || selected.length === 0) return
    selected.forEach(async (it) => {
      const key = ['inventory', it.id]
      let data: any = queryClient.getQueryData(key)
      if (!data) {
        try {
          data = await queryClient.fetchQuery({
            queryKey: key,
            queryFn: async () => {
              const res = await api.get(`/inventory/${it.id}`)
              return res.data
            },
          })
        } catch (e) {
          return
        }
      }
      const wl = data?.warehouse_levels || []
      const found = wl.find((w: any) => w.warehouse_id === warehouseId)
      const avail = found?.quantity_available ?? data?.quantity ?? it.available ?? 0
      setSelected((prev) => prev.map((s) => (s.id === it.id ? { ...s, available: avail } : s)))
    })
  }, [warehouseId])

  const updateQty = (id: number, qty: number) => {
    const it = selected.find((i) => i.id === id)
    if (!it) return
    const avail = typeof it.available === 'number' ? it.available : Number.MAX_SAFE_INTEGER
    const clamped = Math.max(1, Math.min(qty, avail))
    if (qty > avail) {
      addToast('warning', 'Quantity limited', `Requested quantity adjusted to available (${avail})`)
    }
    setSelected((prev) => prev.map((i) => (i.id === id ? { ...i, quantity: clamped } : i)))
  }

  const updateIssuedQty = (id: number, qty: number) => {
    setSelected((prev) => prev.map((i) => (i.id === id ? { ...i, quantity_issued: qty } : i)))
  }

  const updateUnitCost = (id: number, cost: number) => {
    setSelected((prev) => prev.map((i) => (i.id === id ? { ...i, unit_cost: cost } : i)))
  }

  const removeItem = (id: number) => setSelected((prev) => prev.filter((it) => it.id !== id))

  const setItemBin = (id: number, bin_id: number | null) => {
    setSelected((prev) => prev.map((it) => (it.id === id ? { ...it, bin_id } : it)))
  }

  const handlePrSelect = (id: string) => {
    setPrId(id)
    if (!id) return
    const pr = purchaseRequests.find((p: any) => p.id === Number(id))
    if (pr && pr.items) {
      pr.items.forEach((it: any) => {
        if (!selected.find((s) => s.id === it.item_id)) {
          setSelected((s) => [...s, { 
            id: it.item_id, 
            name: it.name, 
            sku: it.sku, 
            quantity: it.quantity, 
            quantity_issued: 0, 
            unit_cost: it.estimated_cost || 0 
          }])
        }
      })
    }
  }

  const SelectedItemRow: React.FC<{ it: PickedItem }> = ({ it }) => {
    const [showBins, setShowBins] = useState(false)
    const binsQuery = useWarehouseBins(warehouseId ?? undefined, it.id)
    const { hasPermission } = useAuth()
    const canViewBins = hasPermission('warehouses:view')
    const canSelectBins = hasPermission('inventory:stock')

    return (
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col gap-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="font-bold text-slate-800">{it.name}</div>
            <div className="text-xs font-semibold text-slate-500 mt-1">{it.sku} • Available: {it.available ?? '—'}</div>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-[1.5fr_0.9fr_0.9fr_0.9fr_auto] items-end">
            <div className="min-w-0">
              <div className="font-bold text-slate-800 truncate">{it.name}</div>
              <div className="text-xs font-semibold text-slate-500 mt-1 truncate">{it.sku} • Available: {it.available ?? '—'}</div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Req Qty</label>
              <input type="number" min={1} className="input-field w-full py-1.5 px-2 text-sm" value={it.quantity} onChange={(e) => updateQty(it.id, Number(e.target.value || 1))} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Iss Qty</label>
              <input type="number" min={0} className="input-field w-full py-1.5 px-2 text-sm" value={it.quantity_issued || 0} onChange={(e) => updateIssuedQty(it.id, Number(e.target.value || 0))} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Unit Cost</label>
              <input type="number" min={0} step="0.01" className="input-field w-full py-1.5 px-2 text-sm" value={it.unit_cost || 0} onChange={(e) => updateUnitCost(it.id, Number(e.target.value || 0))} />
            </div>
            <div className="flex items-end justify-end gap-2">
              {canViewBins && (
                <button type="button" className="btn-secondary text-sm px-3 py-1.5 h-[34px] whitespace-nowrap" onClick={() => setShowBins((s) => !s)} disabled={!warehouseId}>{showBins ? 'Hide Bins' : 'Bins'}</button>
              )}
              <button type="button" className="p-2 h-[34px] text-rose-500 hover:bg-rose-100 rounded-lg transition-colors" onClick={() => removeItem(it.id)}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
            {!canViewBins && (
              <div className="text-[10px] text-slate-400 w-full mt-1 md:col-span-5">Bins hidden (permissions)</div>
            )}
          </div>
        </div>
        {showBins && (
          <div className="mt-2">
            {!warehouseId && <div className="text-sm text-slate-500">Select a warehouse to view bins.</div>}
            {warehouseId && binsQuery.isLoading && <div className="text-sm text-slate-500">Loading bins...</div>}
                    {warehouseId && binsQuery.data && (
              <div className="flex flex-wrap gap-2 mt-2">
                {binsQuery.data?.map((b: any) => (
                  <label key={b.id} className="flex items-center gap-1 text-sm border p-1 rounded bg-slate-50 cursor-pointer hover:bg-slate-100">
                    <input type="radio" name={`bin-${it.id}`} value={b.id} checked={it.bin_id === b.id} onChange={() => setItemBin(it.id, b.id)} disabled={!canSelectBins} />
                    {b.code || b.name || `Bin ${b.id}`}
                  </label>
                ))}
                <label className="flex items-center gap-1 text-sm border p-1 rounded bg-slate-50 cursor-pointer hover:bg-slate-100">
                  <input type="radio" name={`bin-${it.id}`} value="" checked={!it.bin_id} onChange={() => setItemBin(it.id, null)} disabled={!canSelectBins} />
                  Auto/None
                </label>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selected.length === 0) {
      addToast('error', 'Error', 'Add at least one item')
      return
    }
    setSubmitting(true)
    const payload = selected.map((it) => ({ 
      item_id: it.id, 
      quantity: Number(it.quantity), 
      quantity_issued: Number(it.quantity_issued || 0),
      unit_cost: Number(it.unit_cost || it.unit_price || 0),
      bin_id: it.bin_id ?? undefined 
    }))
    try {
      await create.mutateAsync({ items: payload, warehouse_id: warehouseId ?? undefined })
      addToast('success', 'Created', 'Requisition submitted')
      setSelected([])
      setWarehouseId(null)
      setPrId("")
      onClose()
    } catch (err: any) {
      addToast('error', 'Failed', err.response?.data?.message || 'Error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New Requisition" size="2xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-slate-700">Optional: Load from PR</label>
            <select
              value={prId}
              onChange={(e) => handlePrSelect(e.target.value)}
              className="input-field w-full"
            >
              <option value="">Select an Approved PR...</option>
              {purchaseRequests.map((pr: any) => (
                <option key={pr.id} value={pr.id}>{pr.pr_number} - {pr.reason}</option>
              ))}
            </select>
          </div>
          
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-slate-700">Source Warehouse</label>
            <select
              value={warehouseId || ''}
              onChange={(e) => setWarehouseId(e.target.value ? Number(e.target.value) : null)}
              className="input-field w-full"
            >
              <option value="">Any / Auto-assign</option>
              {(warehousesData || []).map((w: any) => (
                <option key={(w.id || w.warehouse_id)} value={(w.id || w.warehouse_id)}>
                  {(w.warehouse_name || w.name || w.code || `Warehouse ${(w.id || w.warehouse_id)}`)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Search items</label>
          <input
            className="input-field mt-1"
            placeholder="Search by name or SKU"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          {search.trim().length > 0 && (
            <div className="mt-2 border rounded max-h-40 overflow-y-auto bg-white">
              {inventoryQuery.isLoading && <div className="p-2 text-sm text-slate-500">Searching...</div>}
              {!inventoryQuery.isLoading && suggestions.length === 0 && <div className="p-2 text-sm text-slate-500">No items</div>}
              {suggestions.map((it: any) => (
                <div key={it.id} className="p-2 hover:bg-slate-50 flex justify-between items-center">
                  <div>
                    <div className="font-medium">{it.name}</div>
                    <div className="text-xs text-slate-500">{it.sku} • {it.unit} • Available: {it.quantity_available ?? it.quantity_on_hand ?? it.quantity ?? 0}</div>
                  </div>
                  <div>
                    <button className="btn" onClick={() => addItem(it)}>Add</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="text-sm font-medium">Selected items</label>
          <div className="mt-2 space-y-2">
            {selected.length === 0 && <div className="text-sm text-slate-500">No items selected</div>}
            {selected.map((it) => (
              <SelectedItemRow key={it.id} it={it} />
            ))}
          </div>
        </div>
        
        <div className="flex justify-end gap-3 pt-4 border-t">
          <button type="button" className="btn" onClick={onClose} disabled={submitting}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={submitting || selected.length === 0}>
            {submitting ? 'Creating...' : 'Create Requisition'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default NewRequisitionModal
