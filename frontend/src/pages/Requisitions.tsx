import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ClipboardList, Plus, Search, Filter, CheckCircle2, Clock, XCircle, Send } from "lucide-react";
import ReturnRISModal from "../components/ui/ReturnRISModal";
import { useRequisitions, useApproveRequisition, useIssueRequisition } from '../hooks/useRequisitions';
import NewRequisitionModal from '../components/ui/NewRequisitionModal';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import ViewRISModal from '../components/ui/ViewRISModal';

export default function Requisitions() {
  const [returnModalOpen, setReturnModalOpen] = useState(false);
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [viewModalId, setViewModalId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading } = useRequisitions();
  const approve = useApproveRequisition();
  const issue = useIssueRequisition();
  const { addToast } = useToast();
  const { user } = useAuth();

  const requisitions = data?.items || [];

  const handleApprove = async (id: number) => {
    try {
      await approve.mutateAsync(id);
      addToast('success', 'Approved', `Requisition #${id} approved successfully`);
    } catch (err: any) {
      addToast('error', 'Approval Failed', err.response?.data?.message || 'Failed to approve requisition');
    }
  };

  const handleIssue = async (id: number) => {
    try {
      await issue.mutateAsync(id);
      addToast('success', 'Issued', `Requisition #${id} issued successfully`);
    } catch (err: any) {
      addToast('error', 'Issue Failed', err.response?.data?.message || 'Failed to issue requisition');
    }
  };

  const filteredRequisitions = requisitions.filter((r: any) => {
    const matchesSearch = r.ris_number?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          r.id?.toString().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const canApprove = user?.role === 'admin' || user?.role === 'procurement_officer';
  const canIssue = user?.role === 'admin' || user?.role === 'logistics_officer';

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-6"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
              <div className="p-2 bg-sky-100 rounded-xl">
                <ClipboardList className="w-6 h-6 text-sky-600" />
              </div>
              Requisition Slips (RIS)
            </h1>
            <p className="text-slate-500 mt-1">
              Manage departmental requests for stock issuance.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              className="btn-secondary flex items-center justify-center gap-2"
              onClick={() => setReturnModalOpen(true)}
            >
              Return RIS
            </button>
            <button className="btn-primary flex items-center justify-center gap-2" onClick={() => setIsNewModalOpen(true)}>
              <Plus className="w-4 h-4" /> New Requisition
            </button>
          </div>
        </div>

        <div className="enterprise-card overflow-hidden p-0">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
            <h3 className="font-bold text-slate-700">Recent Requisitions</h3>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search RIS..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="input-field pl-9 py-1.5 text-sm w-48 focus:w-64 transition-all"
                />
              </div>
              <div className="relative">
                <Filter className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="input-field pl-9 py-1.5 text-sm appearance-none"
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="issued">Issued</option>
                  <option value="rejected">Rejected</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>
          </div>
          <div className="table-container">
            <table className="w-full text-left border-collapse responsive-table">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">RIS Number</th>
                  <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Requested Date</th>
                  <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="table-header px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr><td colSpan={4} className="px-6 py-8 text-center text-slate-400">Loading requisitions...</td></tr>
                ) : (
                  filteredRequisitions.map((r: any) => (
                    <tr key={r.id} className="table-row hover:bg-slate-50 transition-colors">
                      <td data-label="Detail" className="table-cell px-6 py-4 font-semibold text-slate-800 whitespace-nowrap">{r.ris_number ?? `RIS-${r.id}`}</td>
                      <td data-label="Detail" className="table-cell px-6 py-4 text-slate-500 text-sm whitespace-nowrap">{r.requested_date ? new Date(r.requested_date).toLocaleDateString() : '—'}</td>
                      <td data-label="Detail" className="table-cell px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                          r.status === 'issued' ? 'bg-emerald-100 text-emerald-700' : 
                          r.status === 'approved' ? 'bg-blue-100 text-blue-700' : 
                          r.status === 'rejected' || r.status === 'cancelled' ? 'bg-rose-100 text-rose-700' : 
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {r.status === 'issued' && <CheckCircle2 className="w-3.5 h-3.5" />}
                          {r.status === 'approved' && <CheckCircle2 className="w-3.5 h-3.5" />}
                          {(r.status === 'rejected' || r.status === 'cancelled') && <XCircle className="w-3.5 h-3.5" />}
                          {r.status === 'pending' && <Clock className="w-3.5 h-3.5" />}
                          {String(r.status).toUpperCase()}
                        </span>
                      </td>
                      <td data-label="Detail" className="table-cell px-6 py-4 text-right whitespace-nowrap">
                        <div className="flex gap-2 justify-end">
                          {r.status === 'pending' && canApprove && (
                            <button onClick={() => handleApprove(r.id)} disabled={approve.isPending} className="text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 px-3 py-1.5 rounded-lg transition-colors">
                              Approve
                            </button>
                          )}
                          {r.status === 'approved' && canIssue && (
                            <button onClick={() => handleIssue(r.id)} disabled={issue.isPending} className="text-sm font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg transition-colors">
                              Issue
                            </button>
                          )}
                          <button 
                            className="text-sm font-semibold text-slate-600 hover:text-slate-700 bg-slate-100 px-3 py-1.5 rounded-lg transition-colors"
                            onClick={() => setViewModalId(r.id)}
                          >
                            View
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
                {!isLoading && filteredRequisitions.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <div className="mx-auto w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                          <ClipboardList className="w-6 h-6 text-slate-400" />
                      </div>
                      <p className="text-slate-500 font-medium">No requisitions found.</p>
                      <p className="text-slate-400 text-sm mt-1">Create a new requisition to get started.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
      <NewRequisitionModal isOpen={isNewModalOpen} onClose={() => setIsNewModalOpen(false)} />
      <ReturnRISModal
        isOpen={returnModalOpen}
        onClose={() => setReturnModalOpen(false)}
      />
      <ViewRISModal isOpen={!!viewModalId} onClose={() => setViewModalId(null)} risId={viewModalId} />
    </>
  );
}
