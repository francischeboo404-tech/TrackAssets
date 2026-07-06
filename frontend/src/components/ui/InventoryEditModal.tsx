import React, { useEffect, useState } from "react";
import { Modal } from "./Modal";
import { Package } from "lucide-react";
import { useUpdateInventoryItem } from "../../hooks/useInventory";
import { useCategories } from "../../hooks/useCategories";
import { useSuppliers } from "../../hooks/useSuppliers";
import { useToast } from "../../context/ToastContext";
import type { InventoryItem } from "../../types";

type InventoryItemType =
  | "consumable"
  | "asset"
  | "raw"
  | "finished"
  | "service"
  | "other";

interface InventoryEditFormData {
  name: string;
  sku: string;
  quantity: number;
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
}

interface InventoryEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: InventoryItem | null;
}

export const InventoryEditModal: React.FC<InventoryEditModalProps> = ({
  isOpen,
  onClose,
  item,
}) => {
  const { addToast } = useToast();
  const updateItem = useUpdateInventoryItem();
  const { data: categoriesData } = useCategories() as any;
  const { data: suppliersData } = useSuppliers() as any;
  const categories = Array.isArray(categoriesData?.categories)
    ? categoriesData.categories
    : [];
  const suppliers = Array.isArray(suppliersData?.suppliers)
    ? suppliersData.suppliers
    : [];

  const [formData, setFormData] = useState<InventoryEditFormData>({
    name: "",
    sku: "",
    quantity: 0,
    description: "",
    reorder_level: 10,
    unit_price: 0,
    unit: "pcs",
    category_id: undefined,
    item_type: "consumable",
    status: "active",
    preferred_supplier_id: undefined,
    supplier_item_reference: "",
    purchase_cost: 0,
    last_purchase_cost: 0,
    tax_category: "",
    lead_time_days: 7,
  });

  useEffect(() => {
    if (item) {
      setFormData({
        name: item.name,
        sku: item.sku,
        quantity: item.quantity,
        description: item.description || "",
        reorder_level: item.reorder_level,
        unit_price: item.unit_price,
        unit: item.unit || "pcs",
        category_id: item.category_id,
        item_type: item.item_type || "consumable",
        status: item.status || "active",
        preferred_supplier_id: item.preferred_supplier_id,
        supplier_item_reference: item.supplier_item_reference || "",
        purchase_cost: item.purchase_cost || 0,
        last_purchase_cost: item.last_purchase_cost || 0,
        tax_category: item.tax_category || "",
        lead_time_days: item.lead_time_days || 7,
      });
    }
  }, [item]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!item) return;
    try {
      await updateItem.mutateAsync({
        id: item.id,
        ...formData,
        purchase_cost: Number(formData.purchase_cost),
        last_purchase_cost: Number(formData.last_purchase_cost),
        lead_time_days: Number(formData.lead_time_days),
        reorder_level: Number(formData.reorder_level),
        quantity: Number(formData.quantity),
        unit_price: Number(formData.unit_price),
      });
      addToast("success", "Item Updated", `${formData.name} was saved.`);
      onClose();
    } catch (err: any) {
      const msg =
        err.response?.data?.message ||
        (err.response?.status === 403
          ? "You do not have permission to edit inventory."
          : "Update failed.");
      addToast("error", "Update Failed", msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Inventory Item"
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4 p-1">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-brand-50 rounded-lg">
            <Package className="w-5 h-5 text-brand-primary" />
          </div>
          <p className="text-sm text-slate-500">
            Stock quantity is adjusted via IN/OUT movements only.
          </p>
        </div>
        <input
          className="input-field w-full"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Item name"
          required
        />
        <input
          className="input-field w-full font-mono text-sm"
          value={formData.sku}
          onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
          placeholder="SKU"
          required
        />
        <textarea
          className="input-field w-full min-h-[80px]"
          value={formData.description}
          onChange={(e) =>
            setFormData({ ...formData, description: e.target.value })
          }
          placeholder="Description"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Category
            </label>
            <select
              className="input-field w-full"
              value={formData.category_id ?? ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  category_id: e.target.value
                    ? Number(e.target.value)
                    : undefined,
                })
              }
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
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Item Type
            </label>
            <select
              className="input-field w-full"
              value={formData.item_type}
              onChange={(e) =>
                setFormData({ ...formData, item_type: e.target.value as any })
              }
            >
              <option value="consumable">Consumable</option>
              <option value="asset">Asset</option>
              <option value="raw">Raw Material</option>
              <option value="finished">Finished Product</option>
              <option value="service">Service</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Status
            </label>
            <select
              className="input-field w-full"
              value={formData.status}
              onChange={(e) =>
                setFormData({ ...formData, status: e.target.value })
              }
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="discontinued">Discontinued</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <input
            type="number"
            min={0}
            className="input-field w-full"
            value={formData.reorder_level}
            onChange={(e) =>
              setFormData({
                ...formData,
                reorder_level: Number(e.target.value),
              })
            }
            placeholder="Reorder level"
          />
          <input
            type="number"
            min={0}
            required
            className="input-field w-full"
            value={formData.quantity}
            onChange={(e) =>
              setFormData({ ...formData, quantity: Number(e.target.value) })
            }
            placeholder="Quantity"
          />
          <input
            type="number"
            min={0}
            step="0.01"
            className="input-field w-full"
            value={formData.unit_price}
            onChange={(e) =>
              setFormData({ ...formData, unit_price: Number(e.target.value) })
            }
            placeholder="Unit price"
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            type="number"
            min={0}
            step="0.01"
            className="input-field w-full"
            value={formData.purchase_cost}
            onChange={(e) =>
              setFormData({
                ...formData,
                purchase_cost: Number(e.target.value),
              })
            }
            placeholder="Purchase cost"
          />
          <input
            type="number"
            min={0}
            step="0.01"
            className="input-field w-full"
            value={formData.last_purchase_cost}
            onChange={(e) =>
              setFormData({
                ...formData,
                last_purchase_cost: Number(e.target.value),
              })
            }
            placeholder="Last purchase cost"
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Preferred Supplier
            </label>
            <select
              className="input-field w-full"
              value={formData.preferred_supplier_id ?? ""}
              onChange={(e) => {
                const supplierId = e.target.value
                  ? Number(e.target.value)
                  : undefined;
                const supplier = suppliers.find(
                  (supplier: any) => supplier.id === supplierId,
                );
                const previousSupplier = suppliers.find(
                  (supplier: any) =>
                    supplier.id === formData.preferred_supplier_id,
                );
                const shouldAutoFill =
                  !formData.supplier_item_reference ||
                  formData.supplier_item_reference === previousSupplier?.code;

                setFormData({
                  ...formData,
                  preferred_supplier_id: supplierId,
                  supplier_item_reference: supplier
                    ? shouldAutoFill
                      ? supplier.code || ""
                      : formData.supplier_item_reference
                    : formData.supplier_item_reference,
                });
              }}
            >
              <option value="">Select supplier</option>
              {suppliers.map((supplier: any) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </select>
          </div>
          <input
            type="text"
            className="input-field w-full"
            placeholder="Supplier reference"
            value={formData.supplier_item_reference}
            onChange={(e) =>
              setFormData({
                ...formData,
                supplier_item_reference: e.target.value,
              })
            }
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            type="number"
            min={0}
            className="input-field w-full"
            value={formData.lead_time_days}
            onChange={(e) =>
              setFormData({
                ...formData,
                lead_time_days: Number(e.target.value),
              })
            }
            placeholder="Lead time (days)"
          />
          <input
            type="text"
            className="input-field w-full"
            placeholder="Tax category"
            value={formData.tax_category}
            onChange={(e) =>
              setFormData({ ...formData, tax_category: e.target.value })
            }
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={updateItem.isPending}
          >
            Save Changes
          </button>
        </div>
      </form>
    </Modal>
  );
};
