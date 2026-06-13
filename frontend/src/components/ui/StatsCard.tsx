import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';
import { motion } from 'framer-motion';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    isUp: boolean;
  };
  color?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'slate';
  description?: string;
  loading?: boolean;
}

const COLOR_MAP = {
  indigo: { bg: 'bg-brand-primary/10', text: 'text-brand-primary', shadow: 'shadow-brand-primary/20', gradient: 'from-brand-primary/20 to-transparent' },
  emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-500', shadow: 'shadow-emerald-500/20', gradient: 'from-emerald-500/20 to-transparent' },
  amber: { bg: 'bg-amber-500/10', text: 'text-amber-500', shadow: 'shadow-amber-500/20', gradient: 'from-amber-500/20 to-transparent' },
  rose: { bg: 'bg-rose-500/10', text: 'text-rose-500', shadow: 'shadow-rose-500/20', gradient: 'from-rose-500/20 to-transparent' },
  slate: { bg: 'bg-slate-500/10', text: 'text-slate-500', shadow: 'shadow-slate-500/20', gradient: 'from-slate-500/20 to-transparent' },
};

export const StatsCard: React.FC<StatsCardProps> = ({ 
  title, value, icon: Icon, trend, color = 'indigo', description, loading 
}) => {
  const styles = COLOR_MAP[color];

  if (loading) {
    return (
      <div className="glass-card p-6 animate-pulse space-y-5 h-[160px]">
        <div className="flex justify-between items-start">
          <div className="h-4 w-28 bg-slate-200/50 rounded-md" />
          <div className="h-12 w-12 bg-slate-200/50 rounded-2xl" />
        </div>
        <div className="h-10 w-24 bg-slate-200/50 rounded-lg mt-4" />
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -6, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="glass-card p-6 group relative overflow-hidden h-full flex flex-col justify-between"
    >
      {/* Dynamic Background Glow */}
      <div className={cn("absolute -top-12 -right-12 w-32 h-32 rounded-full blur-3xl opacity-50 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br pointer-events-none", styles.gradient)} />
      
      <div className="flex justify-between items-start relative z-10 mb-4">
        <div>
          <p className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.15em] mb-1.5 drop-shadow-sm">{title}</p>
          <h3 className="text-3xl font-extrabold text-slate-800 tracking-tight leading-none drop-shadow-sm" style={{ fontFamily: 'Outfit' }}>{value}</h3>
        </div>
        <div className={cn("p-3.5 rounded-2xl transition-all duration-500 group-hover:rotate-6 group-hover:scale-110 shadow-lg backdrop-blur-md border border-white/50", styles.bg, styles.text, styles.shadow)}>
          <Icon className="w-6 h-6 drop-shadow-md" strokeWidth={2.5} />
        </div>
      </div>
      
      {(trend || description) && (
        <div className="mt-auto flex items-center gap-3 relative z-10 pt-2 border-t border-slate-100/50">
          {trend && (
            <span className={cn(
              "text-[11px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1 shadow-sm",
              trend.isUp ? "bg-emerald-100/80 text-emerald-700 border border-emerald-200" : "bg-rose-100/80 text-rose-700 border border-rose-200"
            )}>
              {trend.isUp ? (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m18 15-6-6-6 6"/></svg>
              ) : (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
              )}
              {trend.value}%
            </span>
          )}
          {description && <span className="text-[11px] text-slate-500 font-medium tracking-wide truncate">{description}</span>}
        </div>
      )}
    </motion.div>
  );
};
