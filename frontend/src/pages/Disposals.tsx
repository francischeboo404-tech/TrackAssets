import React from 'react';
import { motion } from 'framer-motion';
import { Trash2, Plus } from 'lucide-react';

export default function Disposals() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <div className="p-2 bg-rose-100 rounded-xl">
              <Trash2 className="w-6 h-6 text-rose-600" />
            </div>
            Disposal Requests
          </h1>
          <p className="text-slate-500 mt-1">Manage boarding and disposal of damaged/expired inventory.</p>
        </div>
        <button className="btn-primary flex items-center justify-center gap-2">
          <Plus className="w-4 h-4" /> Request Disposal
        </button>
      </div>
      
      <div className="glass-panel p-8 text-center text-slate-500">
        <Trash2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <h3 className="text-lg font-bold text-slate-700 mb-2">No Disposal Requests</h3>
        <p className="max-w-md mx-auto">Create requests for items that need to be disposed. Items over KES 50,000 require Board approval.</p>
      </div>
    </motion.div>
  );
}
