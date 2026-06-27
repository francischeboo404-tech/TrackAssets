import React from 'react';
import { motion } from 'framer-motion';
import { FileStack } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';

export default function StockCards() {
  const [searchParams] = useSearchParams();
  const cardId = searchParams.get('card_id');

  const { data, isLoading, error } = useQuery({
    queryKey: ['stock_card', cardId],
    queryFn: async () => {
      if (!cardId) return null;
      const res = await api.get(`/ledger/stock-cards/${cardId}`);
      return res.data;
    },
    enabled: !!cardId,
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <div className="p-2 bg-slate-100 rounded-xl">
              <FileStack className="w-6 h-6 text-slate-600" />
            </div>
            Stock & Ledger Cards
          </h1>
          <p className="text-slate-500 mt-1">Official government ledger format for stock movement tracking.</p>
        </div>
      </div>

      {!cardId ? (
        <div className="glass-panel p-8 text-center text-slate-500">
          <FileStack className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-bold text-slate-700 mb-2">Select an item to view its ledger</h3>
          <p className="max-w-md mx-auto">Open an inventory item and click a Stock Card to view details here.</p>
        </div>
      ) : isLoading ? (
        <div className="glass-panel p-8 text-center text-slate-500">Loading stock card...</div>
      ) : error ? (
        <div className="glass-panel p-8 text-center text-slate-500">Stock card details are unavailable. (Endpoint may be missing)</div>
      ) : (
        <div className="glass-panel p-6">
          <h2 className="font-bold text-slate-800">Stock Card Details</h2>
          <pre className="mt-3 text-sm text-slate-700 bg-slate-50 p-3 rounded">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </motion.div>
  );
}
