import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Navigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { LogScanModal } from '../ui/LogScanModal';

export const LayoutShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);

  if (loading) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-slate-50 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(50,156,255,0.05),transparent_50%)]" />
        <div className="w-12 h-12 border-4 border-slate-200 border-t-brand-primary rounded-full animate-spin mb-4" />
        <div className="text-brand-primary font-bold tracking-widest uppercase text-sm animate-pulse">
          Initializing Workspace...
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" />;

  return (
    <div className="flex h-screen bg-slate-50 font-sans overflow-hidden">
      <a 
        href="#main-content" 
        className="fixed top-[-100px] left-0 bg-brand-primary text-white px-6 py-3 z-[100] transition-all focus:top-0 focus:outline-none focus:ring-4 focus:ring-brand-accent/50 font-bold rounded-br-2xl shadow-lg"
      >
        Skip to main content
      </a>
      
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        <TopBar onMenuClick={() => setIsSidebarOpen(true)} onScanClick={() => setIsScanModalOpen(true)} />
        
        <main id="main-content" className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 relative">
          {/* Subtle background glow effect */}
          <div className="fixed top-20 right-0 w-[500px] h-[500px] bg-brand-primary/5 rounded-full blur-3xl pointer-events-none" />
          
          <div className="max-w-[1600px] mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out relative z-10 pb-20">
            {children}
          </div>
        </main>
      </div>

      <LogScanModal isOpen={isScanModalOpen} onClose={() => setIsScanModalOpen(false)} />
    </div>
  );
};
