import React from 'react';
import { motion } from 'framer-motion';
import { FileText } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';

export default function SuppliesLedger() {
  const [searchParams] = useSearchParams();
  const ledgerId = searchParams.get('ledger_id');

  const { data, isLoading, error } = useQuery({
    queryKey: ['ledger_card', ledgerId],
    queryFn: async () => {
      if (!ledgerId) return null;
      const res = await api.get(`/ledger/ledger-cards/${ledgerId}`);
      return res.data;
    },
    enabled: !!ledgerId,
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <div className="p-2 bg-slate-100 rounded-xl">
              <FileText className="w-6 h-6 text-slate-600" />
            </div>
            Supplies Ledger
          </h1>
          <p className="text-slate-500 mt-1">Government ledger view for supplies ledger cards and period summaries.</p>
        </div>
      </div>

      {!ledgerId ? (
        <div className="glass-panel p-8 text-center text-slate-500">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-bold text-slate-700 mb-2">Select a ledger to view</h3>
          <p className="max-w-md mx-auto">Open an inventory item and click its Ledger Card to view the supplies ledger here.</p>
        </div>
      ) : isLoading ? (
        <div className="glass-panel p-8 text-center text-slate-500">Loading ledger card...</div>
      ) : error ? (
        <div className="glass-panel p-8 text-center text-slate-500">Ledger details are unavailable. (Endpoint may be missing)</div>
      ) : (
        <div className="glass-panel p-6">
          <h2 className="font-bold text-slate-800">Ledger Card Details</h2>
          <pre className="mt-3 text-sm text-slate-700 bg-slate-50 p-3 rounded">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </motion.div>
  );
}
