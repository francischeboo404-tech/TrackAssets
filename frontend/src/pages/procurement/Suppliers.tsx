import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  Plus,
  Search,
  Filter,
  Edit2,
  Trash2,
  Mail,
  Phone,
  Clock,
  ShieldCheck,
} from "lucide-react";
import {
  useSuppliers,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
  type Supplier,
} from "../../hooks/useSuppliers";
import { useToast } from "../../context/ToastContext";

export default function Suppliers() {
  const [showModal, setShowModal] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    code: "",
    email: "",
    phone: "",
    average_lead_time_days: 7,
    reliability_score: 1.0,
  });

  const { data: suppliersData, isLoading } = useSuppliers() as any;
  const createSupplier = useCreateSupplier();
  const updateSupplier = useUpdateSupplier();
  const deleteSupplier = useDeleteSupplier();
  const { addToast } = useToast();

  const suppliers = Array.isArray(suppliersData?.suppliers)
    ? suppliersData.suppliers
    : [];

  const filteredSuppliers = suppliers.filter(
    (s: Supplier) =>
      s.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.code?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleOpenModal = (supplier: Supplier | null = null) => {
    if (supplier) {
      setEditingSupplier(supplier);
      setFormData({
        name: supplier.name || "",
        code: supplier.code || "",
        email: supplier.email || "",
        phone: supplier.phone || "",
        average_lead_time_days: supplier.average_lead_time_days || 7,
        reliability_score: supplier.reliability_score || 1.0,
      });
    } else {
      setEditingSupplier(null);
      setFormData({
        name: "",
        code: "",
        email: "",
        phone: "",
        average_lead_time_days: 7,
        reliability_score: 1.0,
      });
    }
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingSupplier) {
        await updateSupplier.mutateAsync({
          id: editingSupplier.id,
          data: formData,
        });
        addToast("success", "Success", "Supplier updated successfully");
      } else {
        await createSupplier.mutateAsync(formData);
        addToast("success", "Success", "Supplier created successfully");
      }
      setShowModal(false);
    } catch (err: any) {
      addToast(
        "error",
        "Error",
        err.response?.data?.message || "Operation failed",
      );
    }
  };

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this supplier?")) {
      try {
        await deleteSupplier.mutateAsync(id);
        addToast("success", "Success", "Supplier deleted successfully");
      } catch (err: any) {
        addToast(
          "error",
          "Error",
          err.response?.data?.message || "Failed to delete supplier",
        );
      }
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <div className="p-2 bg-indigo-100 rounded-xl">
              <Building2 className="w-6 h-6 text-indigo-600" />
            </div>
            Suppliers
          </h1>
          <p className="text-slate-500 mt-1">
            Manage vendor directory and performance metrics.
          </p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="btn-primary flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" /> Add Supplier
        </button>
      </div>

      <div className="enterprise-card overflow-hidden p-0">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search suppliers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field pl-9 py-2 text-sm w-full"
            />
          </div>
        </div>

        <div className="table-container">
          <table className="w-full text-left border-collapse responsive-table">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase">
                  Supplier
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase">
                  Contact
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase text-center">
                  Lead Time
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase text-center">
                  Reliability
                </th>
                <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-8 text-center text-slate-400"
                  >
                    Loading suppliers...
                  </td>
                </tr>
              ) : filteredSuppliers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="mx-auto w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                      <Building2 className="w-6 h-6 text-slate-400" />
                    </div>
                    <p className="text-slate-500 font-medium">
                      No suppliers found.
                    </p>
                  </td>
                </tr>
              ) : (
                filteredSuppliers.map((supplier: Supplier) => (
                  <tr
                    key={supplier.id}
                    className="table-row hover:bg-slate-50 transition-colors"
                  >
                    <td data-label="Supplier" className="table-cell px-6 py-4">
                      <div>
                        <div className="font-bold text-slate-800">
                          {supplier.name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {supplier.code || "No Code"}
                        </div>
                      </div>
                    </td>
                    <td data-label="Contact" className="table-cell px-6 py-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-sm text-slate-600">
                          <Mail className="w-3.5 h-3.5" />{" "}
                          {supplier.email || "—"}
                        </div>
                        <div className="flex items-center gap-1.5 text-sm text-slate-600">
                          <Phone className="w-3.5 h-3.5" />{" "}
                          {supplier.phone || "—"}
                        </div>
                      </div>
                    </td>
                    <td
                      data-label="Lead Time"
                      className="table-cell px-6 py-4 text-center"
                    >
                      <div className="inline-flex items-center gap-1.5 bg-slate-100 px-2.5 py-1 rounded-md text-xs font-semibold text-slate-700">
                        <Clock className="w-3.5 h-3.5" />{" "}
                        {supplier.average_lead_time_days} days
                      </div>
                    </td>
                    <td
                      data-label="Reliability"
                      className="table-cell px-6 py-4 text-center"
                    >
                      <div className="inline-flex items-center gap-1.5 bg-indigo-50 px-2.5 py-1 rounded-md text-xs font-semibold text-indigo-700">
                        <ShieldCheck className="w-3.5 h-3.5" />{" "}
                        {(supplier.reliability_score * 100).toFixed(0)}%
                      </div>
                    </td>
                    <td
                      data-label="Actions"
                      className="table-cell px-6 py-4 text-right"
                    >
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleOpenModal(supplier)}
                          className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(supplier.id)}
                          className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 z-[70] flex items-center justify-center px-4 py-6 bg-slate-950/60 backdrop-blur-sm overflow-y-auto">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-[28px] shadow-2xl w-full max-w-2xl max-h-[calc(100vh-4rem)] overflow-hidden border border-slate-200"
            >
              <div className="sticky top-0 z-10 p-6 border-b border-slate-100 flex items-center justify-between bg-white">
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-[0.18em] mb-2">
                    {editingSupplier ? "Edit Supplier" : "New Supplier"}
                  </p>
                  <h2 className="text-2xl font-semibold text-slate-900">
                    {editingSupplier
                      ? "Update supplier details"
                      : "Add supplier to sourcing"}
                  </h2>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="h-11 w-11 flex items-center justify-center rounded-xl bg-slate-100 text-slate-500 hover:bg-slate-200 transition-colors"
                  aria-label="Close supplier modal"
                >
                  ✕
                </button>
              </div>

              <form
                onSubmit={handleSubmit}
                className="p-6 space-y-4 overflow-y-auto min-h-0"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">
                      Supplier Name *
                    </label>
                    <input
                      required
                      type="text"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      className="input-field w-full"
                      placeholder="Acme Corp"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">
                      Code
                    </label>
                    <input
                      type="text"
                      value={formData.code}
                      onChange={(e) =>
                        setFormData({ ...formData, code: e.target.value })
                      }
                      className="input-field w-full"
                      placeholder="SUP-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">
                      Phone
                    </label>
                    <input
                      type="text"
                      value={formData.phone}
                      onChange={(e) =>
                        setFormData({ ...formData, phone: e.target.value })
                      }
                      className="input-field w-full"
                      placeholder="+1 234 567 890"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-semibold text-slate-700 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) =>
                        setFormData({ ...formData, email: e.target.value })
                      }
                      className="input-field w-full"
                      placeholder="contact@acme.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">
                      Avg Lead Time (Days)
                    </label>
                    <input
                      required
                      type="number"
                      min="0"
                      value={formData.average_lead_time_days}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          average_lead_time_days: Number(e.target.value),
                        })
                      }
                      className="input-field w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">
                      Reliability Score (0-1)
                    </label>
                    <input
                      required
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      value={formData.reliability_score}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          reliability_score: Number(e.target.value),
                        })
                      }
                      className="input-field w-full"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">
                    {editingSupplier ? "Update Supplier" : "Create Supplier"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
