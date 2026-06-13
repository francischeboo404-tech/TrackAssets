import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ShieldAlert, Lock, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import type { UserRole } from '../../types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  allowedRoles 
}) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-50">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-6"
        >
          <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center shadow-2xl relative">
            <Lock className="w-8 h-8 text-brand-primary animate-pulse" />
          </div>
          <p className="text-slate-400 font-black animate-pulse tracking-[0.3em] uppercase text-[10px]">Verifying Clearance</p>
        </motion.div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: { pathname: location.pathname, search: location.search } }} replace />;
  }

  if (
    allowedRoles
    && user.role !== 'admin'
    && !allowedRoles.includes(user.role as UserRole)
  ) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-8">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="enterprise-card max-w-sm w-full text-center p-10 space-y-6"
        >
          <div className="w-20 h-20 bg-rose-50 rounded-full flex items-center justify-center mx-auto text-rose-500 shadow-inner">
            <ShieldAlert className="w-10 h-10" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-black text-slate-800 tracking-tighter">Access Denied</h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed italic">
              Level {user.role.toUpperCase()} credentials lack the necessary clearance for this system module.
            </p>
          </div>
          <button 
            onClick={() => window.history.back()}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Revert to Safety
          </button>
        </motion.div>
      </div>
    );
  }

  return <>{children}</>;
};
