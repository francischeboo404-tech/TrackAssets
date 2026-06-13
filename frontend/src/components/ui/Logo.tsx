import React from 'react';
import { cn } from '../../lib/utils';

interface LogoProps {
  className?: string;
  showText?: boolean;
  variant?: 'light' | 'dark';
}

export const Logo: React.FC<LogoProps> = ({ className, showText = true, variant = 'dark' }) => {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative group">
        {/* Glow effect for logo */}
        <div className="absolute inset-0 bg-brand-primary/20 rounded-xl blur-xl group-hover:bg-brand-primary/30 transition-all duration-500" />
        
        <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-lg border border-slate-100 relative z-10 overflow-hidden">
           {/* Nova Lite N-Node Logo SVG */}
           <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-8 h-8">
              {/* The "N" shape with nodes */}
              <path 
                d="M25 80V20L75 80V20" 
                stroke="#0ea5e9" 
                strokeWidth="12" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
              />
              {/* Nodes at the ends */}
              <circle cx="25" cy="80" r="10" fill="#0ea5e9" />
              <circle cx="75" cy="20" r="10" fill="#0ea5e9" />
              {/* Subtle inner nodes */}
              <circle cx="25" cy="20" r="6" fill="#0ea5e9" stroke="white" strokeWidth="2" />
              <circle cx="75" cy="80" r="6" fill="#0ea5e9" stroke="white" strokeWidth="2" />
           </svg>
        </div>
      </div>
      
      {showText && (
        <div className="flex flex-col leading-none">
          <span className={cn(
            "font-black text-[22px] tracking-tighter uppercase",
            variant === 'dark' ? "text-slate-900" : "text-white"
          )} style={{ fontFamily: 'Outfit' }}>
            Nova Lite
          </span>
          <span className={cn(
            "text-[9px] font-bold tracking-[0.3em] uppercase opacity-60",
            variant === 'dark' ? "text-slate-500" : "text-slate-300"
          )}>
            Limited
          </span>
        </div>
      )}
    </div>
  );
};
