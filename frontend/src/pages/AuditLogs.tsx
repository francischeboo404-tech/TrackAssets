import { useState } from 'react';
import { History, Search, Filter, ArrowRight, User, Terminal, Database, Clock, X, Code2, CloudDownload } from 'lucide-react';
import { downloadAuthenticatedFile } from '../lib/download';
import { useToast } from '../context/ToastContext';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuditLogs } from '../hooks/useAuditLogs';
import { cn } from '../lib/utils';

const AuditLogs = () => {
  const [search, setSearch] = useState('');
  const { data: logs, isLoading } = useAuditLogs({ q: search || undefined });
  const [selectedLog, setSelectedLog] = useState<any | null>(null);
  const [exporting, setExporting] = useState(false);
  const { addToast } = useToast();

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      await downloadAuthenticatedFile(
        '/audit/export',
        {},
        `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`,
      );
      addToast('success', 'Export Complete', 'Audit log CSV has been downloaded.');
    } catch {
      addToast('error', 'Export Failed', 'Could not export audit logs.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-10"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-4xl font-black text-slate-900 tracking-tighter flex items-center gap-3">
            <History className="text-brand-primary w-10 h-10" />
            Audit Ledger
          </h1>
          <p className="text-slate-500 font-medium tracking-tight">Immutable record of all system interactions and data mutations.</p>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exporting}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            <CloudDownload className="w-4 h-4" />
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
          <button
            type="button"
            onClick={() => setSearch('')}
            className="btn-secondary flex items-center gap-2"
          >
            <Filter className="w-4 h-4" /> Clear Filters
          </button>
        </div>
      </div>

      <div className="enterprise-card p-0 overflow-hidden border-none shadow-2xl bg-white/40 backdrop-blur-md">
        <div className="p-8 border-b border-slate-100 bg-slate-50/30 flex flex-col sm:flex-row gap-6 justify-between items-center">
          <div className="relative w-full sm:max-w-md group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-brand-primary transition-colors" />
            <input 
              type="text" 
              placeholder="Search by action, user or SKU..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-2xl py-3 pl-12 pr-4 text-sm focus:ring-4 focus:ring-brand-primary/5 focus:border-brand-primary/20 transition-all outline-none font-medium"
            />
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-500 font-black tracking-widest uppercase">
             <span>Showing {logs?.length || 0} Records</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50">
                <th className="table-header py-6">Operation</th>
                <th className="table-header py-6">Actor</th>
                <th className="table-header py-6">Identity / Entity</th>
                <th className="table-header py-6">Timestamp</th>
                <th className="table-header py-6 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                [1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                  <tr key={i} className="animate-pulse">
                    <td colSpan={5} className="px-8 py-8 h-20 bg-slate-50/20" />
                  </tr>
                ))
              ) : (
                logs?.map((log) => (
                  <tr key={log.id} className="hover:bg-brand-primary/5 transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110",
                          log.action.includes('DELETE') ? "bg-rose-50 text-rose-500" :
                          log.action.includes('CREATE') ? "bg-emerald-50 text-emerald-500" : "bg-brand-primary/5 text-brand-primary"
                        )}>
                          <Terminal className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="font-black text-slate-900 tracking-tight">{log.action}</p>
                          <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest leading-none mt-1">{log.entity_type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
                          <User className="w-4 h-4 text-slate-500" />
                        </div>
                        <span className="text-sm font-bold text-slate-700">{log.username || `User ID: ${log.user_id}`}</span>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-slate-300" />
                        <span className="text-sm font-mono font-medium text-slate-500">{String(log.entity_id).substring(0, 8)}...</span>
                      </div>
                    </td>
                    <td className="px-8 py-5 text-sm font-semibold text-slate-500">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-slate-300" />
                        {new Date(log.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-8 py-5 text-right">
                       <button 
                         onClick={() => setSelectedLog(log)}
                         disabled={!log.details}
                         className="text-xs font-black text-brand-primary hover:text-brand-primary/80 flex items-center gap-1 ml-auto group/btn uppercase tracking-widest disabled:opacity-30 disabled:grayscale transition-all"
                       >
                         JSON <ArrowRight className="w-3 h-3 group-hover/btn:translate-x-0.5 transition-transform" />
                       </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {selectedLog && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              className="w-full max-w-2xl overflow-hidden bg-white border shadow-2xl rounded-3xl border-slate-200"
            >
              <div className="flex items-center justify-between p-6 border-b bg-slate-50/50 border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-100 text-slate-500">
                    <Code2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold tracking-tight text-slate-900 text-lg">Transaction Details</h3>
                    <p className="text-xs font-black tracking-widest text-slate-400 uppercase">{selectedLog.action} • {selectedLog.entity_type}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="p-2 transition-colors rounded-xl hover:bg-slate-100 text-slate-400"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 bg-[#0f172a] overflow-x-auto max-h-[60vh] overflow-y-auto custom-scrollbar">
                <pre className="text-sm font-mono text-emerald-400 leading-relaxed">
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
              <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end">
                <button onClick={() => setSelectedLog(null)} className="btn-secondary">Close Inspector</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AuditLogs;
