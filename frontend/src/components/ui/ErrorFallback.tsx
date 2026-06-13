import React from 'react';
import { AlertCircle, RotateCcw, Home } from 'lucide-react';

interface ErrorFallbackProps {
  error: any;
  resetErrorBoundary: () => void;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8 bg-rose-50/30 rounded-3xl border border-rose-100 animate-in fade-in zoom-in duration-300">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="w-16 h-16 bg-rose-100 rounded-full flex items-center justify-center mx-auto shadow-sm">
          <AlertCircle className="w-8 h-8 text-rose-600" />
        </div>
        
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Something went wrong</h2>
          <p className="text-slate-500 text-sm leading-relaxed">
            The application encountered an unexpected error. Our engineering team has been notified.
          </p>
        </div>

        <div className="bg-white/50 p-4 rounded-xl border border-rose-100 text-left">
          <p className="text-[10px] font-bold text-rose-500 uppercase tracking-widest mb-1">Error Trace</p>
          <p className="text-xs font-mono text-slate-600 break-all">{error.message}</p>
        </div>

        <div className="flex items-center justify-center gap-4 pt-2">
          <button 
            onClick={resetErrorBoundary}
            className="btn-primary bg-rose-600 hover:bg-rose-700 shadow-rose-500/20 flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" /> Try Again
          </button>
          <a 
            href="/"
            className="btn-secondary flex items-center gap-2"
          >
            <Home className="w-4 h-4" /> Go Dashboard
          </a>
        </div>
      </div>
    </div>
  );
};
