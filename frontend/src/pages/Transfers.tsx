import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Share2, Clock, CheckCircle2, XCircle, MessageSquare, ArrowRightLeft, Search, Package } from 'lucide-react';
import { useTransferRequests, useApproveTransfer, useRejectTransfer, useTransferStats, useDispatchTransfer, useReceiveTransfer } from '../hooks/useTransfers';
import { cn } from '../lib/utils';
import { useToast } from '../context/ToastContext';
import { Can } from '../components/auth/Can';

const Transfers = () => {
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'approved' | 'in_transit' | 'completed' | 'rejected'>('pending');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const { data, isLoading } = useTransferRequests(statusFilter, page, search);
  const { data: stats } = useTransferStats();
  const requests = (data as any)?.transfer_requests || [];
  const pagination = (data as any)?.pagination;
  
  const queryClient = useQueryClient();
  const approveMutation = useApproveTransfer();
  const rejectMutation = useRejectTransfer();
  const dispatchMutation = useDispatchTransfer();
  const receiveMutation = useReceiveTransfer();
  const { addToast } = useToast();

  const handleApprove = async (id: number) => {
    try {
      await approveMutation.mutateAsync({ id });
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      addToast('success', 'Transfer Approved', 'Asset location has been updated.');
    } catch (err) {
      addToast('error', 'Action Failed', 'Failed to approve transfer.');
    }
  };

  const handleReject = async (id: number) => {
    const comments = prompt('Please enter rejection reason:');
    if (comments === null) return;
    
    try {
      await rejectMutation.mutateAsync({ id, comments });
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      addToast('warning', 'Transfer Rejected', 'Movement request was denied.');
    } catch (err) {
      addToast('error', 'Action Failed', 'Failed to reject transfer.');
    }
  };

  const handleDispatch = async (id: number) => {
    try {
      await dispatchMutation.mutateAsync({ id });
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      addToast('success', 'Asset Dispatched', 'Asset is now in transit.');
    } catch (err) {
      addToast('error', 'Action Failed', 'Failed to dispatch asset.');
    }
  };

  const handleReceive = async (id: number) => {
    try {
      await receiveMutation.mutateAsync({ id });
      queryClient.invalidateQueries({ queryKey: ['transfer-stats'] });
      addToast('success', 'Asset Received', 'Asset has arrived at its destination.');
    } catch (err) {
      addToast('error', 'Action Failed', 'Failed to mark asset as received.');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'text-sky-600 bg-sky-50 border-sky-100';
      case 'in_transit': return 'text-amber-600 bg-amber-50 border-amber-100';
      case 'completed': return 'text-emerald-600 bg-emerald-50 border-emerald-100';
      case 'rejected': return 'text-rose-600 bg-rose-50 border-rose-100';
      default: return 'text-slate-600 bg-slate-50 border-slate-100';
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
          <ArrowRightLeft className="text-brand-primary w-8 h-8" />
          Transfer Operations
        </h1>
        <p className="text-slate-500 mt-1 font-medium">Coordinate Asset movements between departments and locations.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex gap-2 p-1 bg-slate-100 w-fit rounded-xl overflow-x-auto max-w-full">
          {(['all', 'pending', 'approved', 'in_transit', 'completed', 'rejected'] as const).map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1); }}
              className={cn(
                "px-6 py-2 rounded-lg text-sm font-bold transition-all capitalize whitespace-nowrap",
                statusFilter === s 
                  ? "bg-white text-brand-primary shadow-sm" 
                  : "text-slate-500 hover:text-slate-700"
              )}
            >
              {s} {stats && `(${s === 'all' ? stats.total : stats[s as keyof typeof stats]})`}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input 
            type="text"
            placeholder="Search assets, codes or requesters..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-slate-200 text-slate-900 rounded-xl py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all outline-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {isLoading ? (
          [1, 2, 3].map(i => <div key={i} className="enterprise-card h-32 animate-pulse" />)
        ) : requests?.length === 0 ? (
          <div className="enterprise-card p-12 text-center flex flex-col items-center">
            <Clock className="w-12 h-12 text-slate-200 mb-4" />
            <h3 className="font-bold text-slate-900">No {statusFilter === 'all' ? 'transfer' : statusFilter} requests found</h3>
            <p className="text-slate-500 text-sm">
              {search ? "No requests match your search criteria." : `There are no ${statusFilter === 'all' ? '' : statusFilter} movement requests at the moment.`}
            </p>
          </div>
        ) : (
          requests?.map((req: any) => (
            <div key={req.id} className="enterprise-card group overflow-hidden">
              <div className="flex flex-col lg:flex-row">
                <div className="p-6 lg:border-r border-slate-100 flex-1">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-indigo-50 rounded-lg">
                        {req.item_type === 'inventory' ? (
                          <Package className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <Share2 className="w-5 h-5 text-indigo-600" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900">
                          {req.asset_name} 
                          {req.item_type === 'inventory' && <span className="ml-2 text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full font-mono">{req.quantity} Units</span>}
                        </h3>
                        <p className="text-xs font-mono text-slate-400 uppercase">
                          {req.item_type === 'inventory' ? 'INV' : 'AST'}-{req.asset_code}
                        </p>
                      </div>
                    </div>
                    <div className={cn("px-2.5 py-1 rounded-md text-[10px] font-bold border uppercase tracking-wider", getStatusColor(req.status))}>
                      {req.status}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-sm mt-4">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Origin</span>
                      <span className="font-semibold text-slate-700">{req.from_department_name}</span>
                    </div>
                    <ArrowRightLeft className="w-4 h-4 text-slate-300 mx-2" />
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Destination</span>
                      <span className="font-semibold text-indigo-600 font-bold">{req.to_department_name}</span>
                      {req.requested_location && (
                        <span className="text-[10px] text-slate-400 font-medium italic">{req.requested_location}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-slate-50/50 lg:w-96 flex flex-col justify-between border-t lg:border-t-0 border-slate-100">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Clock className="w-3.5 h-3.5" />
                      Requested {new Date(req.requested_at).toLocaleDateString()} by {req.requested_by}
                    </div>
                    {req.comment && (
                      <div className="flex items-start gap-2 bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
                        <MessageSquare className="w-3.5 h-3.5 text-slate-400 mt-0.5" />
                        <p className="text-xs text-slate-600 italic">"{req.comment}"</p>
                      </div>
                    )}
                  </div>

                  {req.status === 'pending' && (
                    <Can roles={['admin', 'dept_head']}>
                      <div className="flex gap-2 mt-4">
                        <button 
                          onClick={() => handleApprove(req.id)}
                          disabled={approveMutation.isPending}
                          className="flex-1 btn-primary py-2 text-xs bg-emerald-600 hover:bg-emerald-700 border-none flex items-center justify-center gap-1.5"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                        </button>
                        <button 
                          onClick={() => handleReject(req.id)}
                          disabled={rejectMutation.isPending}
                          className="flex-1 btn-secondary py-2 text-xs text-rose-600 hover:bg-rose-50 border-rose-200 flex items-center justify-center gap-1.5"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Reject
                        </button>
                      </div>
                    </Can>
                  )}

                  {req.status === 'approved' && (
                    <Can roles={['admin', 'dept_head']}>
                      <div className="flex gap-2 mt-4">
                        <button 
                          onClick={() => handleDispatch(req.id)}
                          disabled={dispatchMutation.isPending}
                          className="flex-1 btn-primary py-2 text-xs bg-amber-600 hover:bg-amber-700 border-none flex items-center justify-center gap-1.5"
                        >
                          <ArrowRightLeft className="w-3.5 h-3.5" /> Dispatch
                        </button>
                      </div>
                    </Can>
                  )}

                  {req.status === 'in_transit' && (
                    <Can roles={['admin', 'dept_head']}>
                      <div className="flex gap-2 mt-4">
                        <button 
                          onClick={() => handleReceive(req.id)}
                          disabled={receiveMutation.isPending}
                          className="flex-1 btn-primary py-2 text-xs bg-indigo-600 hover:bg-indigo-700 border-none flex items-center justify-center gap-1.5"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Mark Received
                        </button>
                      </div>
                    </Can>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {pagination && pagination.pages > 1 && (
        <div className="flex justify-center items-center gap-4 pt-8">
          <button 
            disabled={!pagination.has_prev}
            onClick={() => setPage(p => p - 1)}
            className="btn-secondary px-4 py-2 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm font-bold text-slate-600">
            Page {pagination.page} of {pagination.pages}
          </span>
          <button 
            disabled={!pagination.has_next}
            onClick={() => setPage(p => p + 1)}
            className="btn-secondary px-4 py-2 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default Transfers;
