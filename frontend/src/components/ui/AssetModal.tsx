import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import { Barcode, Tag, MapPin, Calendar, DollarSign, Activity } from 'lucide-react';
import { useCreateAsset, useUpdateAsset } from '../../hooks/useAssets';
import { useDepartments } from '../../hooks/useDepartments';
import { useWarehouses, useWarehouseDetails } from '../../hooks/useWarehouses';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import { canCreateAsset, canEditAsset } from '../../lib/permissions';
import type { Asset } from '../../types';

interface AssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset?: Asset | null;
}

export const AssetModal: React.FC<AssetModalProps> = ({ isOpen, onClose, asset }) => {
  const { addToast } = useToast();
  const { user } = useAuth();
  const readOnly = asset ? !canEditAsset(user?.role) : !canCreateAsset(user?.role);
  const createAsset = useCreateAsset();
  const updateAsset = useUpdateAsset();
  const { data: departments } = useDepartments();
  const { data: warehouses } = useWarehouses();
  
  const [formData, setFormData] = useState({
    name: '',
    type: 'Hardware',
    asset_code: '',
    serial_number: '',
    purchase_date: new Date().toISOString().split('T')[0],
    purchase_value: 0,
    useful_life: 5,
    department_id: '',
    warehouse_id: '',
    bin_id: '',
    location: '',
  });

  useEffect(() => {
    if (asset) {
      setFormData({
        name: asset.name || '',
        type: asset.type || 'Hardware',
        asset_code: asset.asset_code || '',
        serial_number: asset.serial_number || '',
        purchase_date: asset.purchase_date ? new Date(asset.purchase_date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
        purchase_value: Number(asset.purchase_value) || 0,
        useful_life: Number(asset.useful_life) || 5,
        department_id: String(asset.department_id) || '',
        warehouse_id: asset.warehouse_id ? String(asset.warehouse_id) : '',
        bin_id: asset.bin_id ? String(asset.bin_id) : '',
        location: asset.location || '',
      });
    } else {
      setFormData({
        name: '',
        type: 'Hardware',
        asset_code: '',
        serial_number: '',
        purchase_date: new Date().toISOString().split('T')[0],
        purchase_value: 0,
        useful_life: 5,
        department_id: '',
        warehouse_id: '',
        bin_id: '',
        location: '',
      });
    }
  }, [asset, isOpen]);

  const { data: bins } = useWarehouseDetails(Number(formData.warehouse_id));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (readOnly) {
      addToast('error', 'Read Only', 'You do not have permission to save changes.');
      return;
    }

    // Frontend Validation
    if (!formData.name.trim()) return addToast('error', 'Validation Error', 'Asset name is required');
    if (!formData.department_id) return addToast('error', 'Validation Error', 'Please select a department');
    
    try {
      const finalAssetCode = formData.asset_code.trim();
      
      const payload = {
        ...formData,
        asset_code: finalAssetCode || undefined,
        department_id: Number(formData.department_id),
        warehouse_id: formData.warehouse_id ? Number(formData.warehouse_id) : undefined,
        bin_id: formData.bin_id ? Number(formData.bin_id) : undefined,
        purchase_value: Number(formData.purchase_value),
        useful_life: Number(formData.useful_life),
      };

      if (asset) {
        await updateAsset.mutateAsync({ id: asset.id, ...payload });
        addToast('success', 'Asset Updated', `${formData.name} has been updated.`);
      } else {
        await createAsset.mutateAsync(payload);
        addToast('success', 'Asset Registered', `${formData.name} has been added to the portfolio.`);
      }
      
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.message || 'Please verify form data and try again.';
      addToast('error', asset ? 'Update Failed' : 'Registration Failed', msg);
    }
  };

  const isPending = createAsset.isPending || updateAsset.isPending;

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={asset ? (readOnly ? 'Asset Details' : 'Edit Asset') : 'Register New Asset'} 
      size="xl"
      footer={
        <>
          <button onClick={onClose} className="btn-secondary">{readOnly ? 'Close' : 'Cancel'}</button>
          {!readOnly && (
          <button 
            type="submit"
            form="asset-form"
            disabled={isPending}
            className="btn-primary"
          >
            {isPending ? (asset ? 'Updating...' : 'Registering...') : (asset ? 'Save Changes' : 'Register Asset')}
          </button>
          )}
        </>
      }
    >
      <form id="asset-form" onSubmit={handleSubmit} className="space-y-6">
        {readOnly && (
          <p className="text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3">
            View-only mode. Status changes are available from the asset card actions.
          </p>
        )}
        <fieldset disabled={readOnly} className="space-y-6 border-0 p-0 m-0 min-w-0">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Tag className="w-3 h-3" /> Asset Name
            </label>
            <input 
              type="text" 
              required
              className="input-field" 
              placeholder="e.g. MacBook Pro 16 - IT-042"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-3 h-3" /> Asset Type
            </label>
            <select 
              className="input-field"
              value={formData.type}
              onChange={e => setFormData({...formData, type: e.target.value})}
            >
              <option value="Hardware">Hardware</option>
              <option value="Software">Software</option>
              <option value="Furniture">Furniture</option>
              <option value="Vehicle">Vehicle</option>
              <option value="Infrastructure">Infrastructure</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Barcode className="w-3 h-3" /> Asset Code
            </label>
            <input 
              type="text" 
              className="input-field font-mono" 
              placeholder="Leave empty for auto-gen"
              value={formData.asset_code}
              onChange={e => setFormData({...formData, asset_code: e.target.value})}
              disabled={!!asset}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Barcode className="w-3 h-3" /> Serial Number
            </label>
            <input 
              type="text" 
              className="input-field font-mono" 
              placeholder="S/N: XXX-XXX-XXX"
              value={formData.serial_number}
              onChange={e => setFormData({...formData, serial_number: e.target.value})}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Calendar className="w-3 h-3" /> Purchase Date
            </label>
            <input 
              type="date" 
              required
              className="input-field" 
              value={formData.purchase_date}
              onChange={e => setFormData({...formData, purchase_date: e.target.value})}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <DollarSign className="w-3 h-3" /> Purchase Value (KES)
            </label>
            <input 
              type="number" 
              required
              min="0"
              step="0.01"
              className="input-field" 
              value={formData.purchase_value}
              onChange={e => setFormData({...formData, purchase_value: Number(e.target.value)})}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Calendar className="w-3 h-3" /> Useful Life (Years)
            </label>
            <input 
              type="number" 
              required
              min="1"
              max="50"
              className="input-field" 
              value={formData.useful_life}
              onChange={e => setFormData({...formData, useful_life: Number(e.target.value)})}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Tag className="w-3 h-3" /> Assigned Department
            </label>
            <select 
              required
              className="input-field"
              value={formData.department_id}
              onChange={e => setFormData({...formData, department_id: e.target.value})}
            >
              <option value="">Select Department</option>
              {departments?.map((dept: any) => (
                <option key={dept.id} value={dept.id}>{dept.name} ({dept.code})</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <MapPin className="w-3 h-3" /> Warehouse
            </label>
            <select 
              className="input-field"
              value={formData.warehouse_id}
              onChange={e => setFormData({...formData, warehouse_id: e.target.value, bin_id: ''})}
            >
              <option value="">Select Warehouse</option>
              {warehouses?.map((wh: any) => (
                <option key={wh.id || wh.warehouse_id} value={wh.id || wh.warehouse_id}>{wh.name || wh.warehouse_name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <MapPin className="w-3 h-3" /> Specific Bin
            </label>
            <select 
              className="input-field"
              value={formData.bin_id}
              onChange={e => setFormData({...formData, bin_id: e.target.value})}
              disabled={!formData.warehouse_id}
            >
              <option value="">Select Bin (Optional)</option>
              {bins?.map((bin: any) => (
                <option key={bin.id} value={bin.id}>{bin.code} {bin.description ? `- ${bin.description}` : ''}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <MapPin className="w-3 h-3" /> Legacy Location String
            </label>
            <input 
              type="text" 
              className="input-field" 
              placeholder="e.g. Floor 2, Zone B"
              value={formData.location}
              onChange={e => setFormData({...formData, location: e.target.value})}
            />
          </div>
        </div>
        </fieldset>
      </form>
    </Modal>
  );
};
