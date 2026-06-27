import React, { useState } from 'react';
import { Modal } from './Modal';
import { Package, Hash, Layers, AlertTriangle, DollarSign, Settings } from 'lucide-react';
import { useCreateInventoryItem } from '../../hooks/useInventory';
import { useCategories } from '../../hooks/useCategories';
import { useSuppliers } from '../../hooks/useSuppliers';
import { useToast } from '../../context/ToastContext';

type InventoryItemType =
  | 'consumable'
  | 'asset'
  | 'raw'
  | 'finished'
  | 'service';

interface InventoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InventoryModal: React.FC<InventoryModalProps> = ({ isOpen, onClose }) => {
  const { addToast } = useToast();
  const createItem = useCreateInventoryItem();
  const { data: categoriesData, isLoading: isCategoriesLoading } = useCategories() as any;
  const { data: suppliersData, isLoading: isSuppliersLoading } = useSuppliers() as any;
  const categories = Array.isArray(categoriesData?.categories) ? categoriesData.categories : [];
  const suppliers = Array.isArray(suppliersData?.suppliers) ? suppliersData.suppliers : [];

  interface InventoryFormData {
    name: string;
    sku: string;
    description: string;
    reorder_level: number;
    unit_price: number;
    unit: string;
    category_id?: number;
    item_type: InventoryItemType;
    status: string;
    preferred_supplier_id?: number;
    supplier_item_reference: string;
    purchase_cost: number;
    last_purchase_cost: number;
    tax_category: string;
    lead_time_days: number;
    min_stock_level: number;
    max_stock_level: number;
    safety_stock: number;
    opening_stock: number;
    batch_tracking: boolean;
    serial_tracking: boolean;
    expiry_tracking: boolean;
  }

  const [formData, setFormData] = useState<InventoryFormData>({
    name: '',
    sku: '',
    description: '',
    reorder_level: 10,
    unit_price: 0,
    unit: 'pcs',
    // Item Identification
    category_id: undefined,
    item_type: 'consumable',
    status: 'active',
    // Procurement Data
    preferred_supplier_id: undefined,
    supplier_item_reference: '',
    purchase_cost: 0,
    last_purchase_cost: 0,
    tax_category: '',
    lead_time_days: 7,
    // Inventory Control
    min_stock_level: 0,
    max_stock_level: 0,
    safety_stock: 0,
    opening_stock: 0,
    // Traceability flags
    batch_tracking: false,
    serial_tracking: false,
    expiry_tracking: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Frontend Validation
    if (!formData.name.trim()) return addToast('error', 'Validation Error', 'Item name is required');
    if (!formData.sku.trim()) return addToast('error', 'Validation Error', 'SKU is required');
    
    try {
      await createItem.mutateAsync({
        ...formData,
        sku: formData.sku.trim(),
        unit_price: Number(formData.unit_price),
        reorder_level: Number(formData.reorder_level),
        purchase_cost: Number(formData.purchase_cost),
        last_purchase_cost: Number(formData.last_purchase_cost),
        lead_time_days: Number(formData.lead_time_days),
        min_stock_level: Number(formData.min_stock_level),
        max_stock_level: Number(formData.max_stock_level),
        safety_stock: Number(formData.safety_stock),
        opening_stock: Number(formData.opening_stock),
      });
      addToast('success', 'SKU Created', `${formData.name} has been added to inventory.`);
      onClose();
      setFormData({
        name: '',
        sku: '',
        description: '',
        reorder_level: 10,
        unit_price: 0,
        unit: 'pcs',
        category_id: undefined,
        item_type: 'consumable',
        status: 'active',
        preferred_supplier_id: undefined,
        supplier_item_reference: '',
        purchase_cost: 0,
        last_purchase_cost: 0,
        tax_category: '',
        lead_time_days: 7,
        min_stock_level: 0,
        max_stock_level: 0,
        safety_stock: 0,
        opening_stock: 0,
        batch_tracking: false,
        serial_tracking: false,
        expiry_tracking: false,
      });
    } catch (err: any) {
      // Extract detailed validation errors if available
      const backendErrors = err.response?.data?.validation_errors;
      let msg = err.response?.data?.message || 'Please verify form data and try again.';
      
      if (backendErrors) {
        const firstError = Object.values(backendErrors)[0];
        if (Array.isArray(firstError)) msg = firstError[0];
      }
      
      addToast('error', 'Creation Failed', msg);
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title="Create New Inventory SKU" 
      size="lg"
      footer={
        <>
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button 
            type="submit"
            form="inventory-form"
            disabled={createItem.isPending}
            className="btn-primary"
          >
            {createItem.isPending ? 'Creating...' : 'Create SKU'}
          </button>
        </>
      }
    >
      <form id="inventory-form" onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <fieldset className="space-y-4 border-b pb-4">
          <legend className="text-sm font-bold text-slate-700 mb-3">Basic Information</legend>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Package className="w-3 h-3" /> Item Name
            </label>
            <input 
              type="text" 
              required
              className="input-field" 
              placeholder="e.g. Ethernet Cable Cat6"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <Hash className="w-3 h-3" /> SKU / Model
              </label>
              <input 
                type="text" 
                required
                className="input-field font-mono" 
                placeholder="e.g. LAPTOP 001"
                value={formData.sku}
                onChange={e => setFormData({...formData, sku: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <Settings className="w-3 h-3" /> Unit Type
              </label>
              <select 
                className="input-field"
                value={formData.unit}
                onChange={e => setFormData({...formData, unit: e.target.value})}
              >
                <option value="pcs">Pieces (pcs)</option>
                <option value="box">Boxes (box)</option>
                <option value="kg">Kilograms (kg)</option>
                <option value="m">Meters (m)</option>
                <option value="ltr">Liters (ltr)</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-3 h-3" /> Description
            </label>
            <textarea 
              className="input-field h-20 resize-none" 
              placeholder="Operational details and specifications..."
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
            />
          </div>
        </fieldset>

        {/* Item Classification */}
        <fieldset className="space-y-4 border-b pb-4">
          <legend className="text-sm font-bold text-slate-700 mb-3">Item Classification</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Category</label>
              <select
                className="input-field"
                value={formData.category_id ?? ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    category_id: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                disabled={isCategoriesLoading}
              >
                <option value="">Select category</option>
                {categories.map((category: any) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Item Type</label>
              <select 
                className="input-field"
                value={formData.item_type}
                onChange={e => setFormData({...formData, item_type: e.target.value as any})}
              >
                <option value="consumable">Consumable</option>
                <option value="asset">Asset</option>
                <option value="raw">Raw Material</option>
                <option value="finished">Finished Product</option>
                <option value="service">Service</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Status</label>
              <select 
                className="input-field"
                value={formData.status}
                onChange={e => setFormData({...formData, status: e.target.value})}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="discontinued">Discontinued</option>
                <option value="pending">Pending</option>
              </select>
            </div>
          </div>
        </fieldset>

        {/* Pricing & Procurement */}
        <fieldset className="space-y-4 border-b pb-4">
          <legend className="text-sm font-bold text-slate-700 mb-3">Pricing & Procurement</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <DollarSign className="w-3 h-3" /> Unit Price (KES)
              </label>
              <input 
                type="number" 
                required
                min="0"
                step="0.01"
                className="input-field"
                value={formData.unit_price}
                onChange={e => setFormData({...formData, unit_price: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Purchase Cost</label>
              <input 
                type="number" 
                min="0"
                step="0.01"
                className="input-field"
                value={formData.purchase_cost}
                onChange={e => setFormData({...formData, purchase_cost: Number(e.target.value)})}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Last Purchase Cost</label>
              <input 
                type="number" 
                min="0"
                step="0.01"
                className="input-field"
                value={formData.last_purchase_cost}
                onChange={e => setFormData({...formData, last_purchase_cost: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Preferred Supplier</label>
              <select
                className="input-field"
                value={formData.preferred_supplier_id ?? ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    preferred_supplier_id: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                disabled={isSuppliersLoading}
              >
                <option value="">Select supplier</option>
                {suppliers.map((supplier: any) => (
                  <option key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lead Time (days)</label>
              <input 
                type="number" 
                min="0"
                className="input-field"
                value={formData.lead_time_days}
                onChange={e => setFormData({...formData, lead_time_days: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Tax Category</label>
              <input 
                type="text"
                className="input-field"
                placeholder="e.g. Standard, Exempt"
                value={formData.tax_category}
                onChange={e => setFormData({...formData, tax_category: e.target.value})}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Supplier Reference</label>
            <input 
              type="text"
              className="input-field"
              placeholder="Supplier's item code/reference"
              value={formData.supplier_item_reference}
              onChange={e => setFormData({...formData, supplier_item_reference: e.target.value})}
            />
          </div>
        </fieldset>

        {/* Stock Levels */}
        <fieldset className="space-y-4 border-b pb-4">
          <legend className="text-sm font-bold text-slate-700 mb-3">Stock Levels & Thresholds</legend>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="w-3 h-3" /> Reorder Level
              </label>
              <input 
                type="number" 
                required
                min="0"
                className="input-field" 
                value={formData.reorder_level}
                onChange={e => setFormData({...formData, reorder_level: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Min Stock</label>
              <input 
                type="number" 
                min="0"
                className="input-field"
                value={formData.min_stock_level}
                onChange={e => setFormData({...formData, min_stock_level: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Max Stock</label>
              <input 
                type="number" 
                min="0"
                className="input-field"
                value={formData.max_stock_level}
                onChange={e => setFormData({...formData, max_stock_level: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Safety Stock</label>
              <input 
                type="number" 
                min="0"
                className="input-field"
                value={formData.safety_stock}
                onChange={e => setFormData({...formData, safety_stock: Number(e.target.value)})}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Opening Stock</label>
              <input 
                type="number" 
                min="0"
                className="input-field"
                value={formData.opening_stock}
                onChange={e => setFormData({...formData, opening_stock: Number(e.target.value)})}
              />
            </div>
          </div>
        </fieldset>

        {/* Traceability */}
        <fieldset className="space-y-4">
          <legend className="text-sm font-bold text-slate-700 mb-3">Traceability Configuration</legend>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <input 
                type="checkbox" 
                id="batch_tracking"
                checked={formData.batch_tracking} 
                onChange={e => setFormData({...formData, batch_tracking: e.target.checked})}
              />
              <label htmlFor="batch_tracking" className="text-sm font-medium cursor-pointer">
                Batch Tracking
              </label>
            </div>
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <input 
                type="checkbox" 
                id="serial_tracking"
                checked={formData.serial_tracking} 
                onChange={e => setFormData({...formData, serial_tracking: e.target.checked})}
              />
              <label htmlFor="serial_tracking" className="text-sm font-medium cursor-pointer">
                Serial Tracking
              </label>
            </div>
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <input 
                type="checkbox" 
                id="expiry_tracking"
                checked={formData.expiry_tracking} 
                onChange={e => setFormData({...formData, expiry_tracking: e.target.checked})}
              />
              <label htmlFor="expiry_tracking" className="text-sm font-medium cursor-pointer">
                Expiry Tracking
              </label>
            </div>
          </div>
        </fieldset>
      </form>
    </Modal>
  );
};
