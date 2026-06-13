import { Sparkles, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface Insight {
  id: string;
  type: 'positive' | 'negative' | 'warning' | 'info';
  title: string;
  description: string;
  value?: string;
  trend?: string;
}

interface AIInsightsProps {
  insights?: Insight[];
}

export const AIInsights: React.FC<AIInsightsProps> = ({ insights = [] }) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-black text-slate-900 tracking-tight flex items-center gap-2 uppercase text-xs" style={{ fontFamily: 'Outfit' }}>
          <Sparkles className="w-4 h-4 text-brand-primary animate-pulse" />
          AI Intelligence Insights
        </h3>
        <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">Live Engine v2.0</span>
      </div>

      <div className="space-y-4">
        {insights.length === 0 ? (
          <div className="text-sm text-slate-400 p-4 text-center">No insights available at this time.</div>
        ) : (
          insights.map((insight, index) => (
            <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            key={insight.id}
            className="p-5 bg-white border border-slate-100 rounded-[1.5rem] shadow-sm hover:shadow-md transition-all group relative overflow-hidden"
          >
            {/* Type Indicator */}
            <div className={cn(
               "absolute top-0 left-0 w-1 h-full",
               insight.type === 'positive' ? "bg-emerald-500" :
               insight.type === 'warning' ? "bg-amber-500" :
               insight.type === 'negative' ? "bg-rose-500" : "bg-brand-primary"
            )} />

            <div className="flex justify-between items-start">
              <div className="space-y-1">
                <h4 className="font-bold text-slate-900 text-sm group-hover:text-brand-primary transition-colors">{insight.title}</h4>
                <p className="text-xs text-slate-500 leading-relaxed">{insight.description}</p>
              </div>
              <div className="text-right flex flex-col items-end">
                <span className={cn(
                  "text-[11px] font-black tracking-tighter",
                  insight.type === 'positive' ? "text-emerald-600" :
                  insight.type === 'warning' ? "text-amber-600" : "text-brand-primary"
                )}>{insight.value}</span>
                <span className="text-[9px] font-bold text-slate-300 uppercase tracking-widest">{insight.trend}</span>
              </div>
            </div>
          </motion.div>
        )))}
      </div>

      <div className="p-6 bg-slate-900 rounded-[2rem] text-white overflow-hidden relative group">
         <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-125 transition-transform duration-700">
            <ShieldCheck className="w-16 h-16" />
         </div>
         <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 mb-2">Predictive Logic Engine</p>
         <h4 className="text-sm font-bold leading-tight">
           Live Data Evaluation Active. System continuously monitoring movement variance and stock thresholds.
         </h4>
         <div className="mt-4 flex gap-1">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 2, repeat: Infinity, delay: i * 0.1 }}
                  className="h-full bg-brand-primary"
                />
              </div>
            ))}
         </div>
      </div>
    </div>
  );
};
