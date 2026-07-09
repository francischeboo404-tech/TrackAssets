import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer, size = 'md' }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-2xl',
    '2xl': 'max-w-4xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 lg:p-6 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200 overflow-y-auto">
      <div 
        ref={modalRef}
        className={cn(
          "bg-white w-full rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[95vh] animate-in zoom-in-95 duration-200",
          sizeClasses[size],
          "max-w-[min(100%,64rem)]"
        )}
      >
        <div className="flex items-center justify-between px-4 py-4 sm:px-6 sm:py-5 border-b border-slate-100">
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 pr-3">{title}</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="px-4 py-4 sm:px-6 sm:py-6 overflow-y-auto flex-1">
          {children}
        </div>

        {footer && (
          <div className="px-4 py-4 sm:px-6 sm:py-5 border-t border-slate-100 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3 bg-slate-50/50 rounded-b-2xl">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
