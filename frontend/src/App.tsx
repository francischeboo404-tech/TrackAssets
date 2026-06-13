import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { LayoutShell } from './components/layout/LayoutShell';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { ToastContainer } from './components/ui/ToastContainer';
import { useSSE } from './hooks/useSSE';
import { Suspense, lazy } from 'react';

// Pages
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Inventory = lazy(() => import('./pages/Inventory'));
const Assets = lazy(() => import('./pages/Assets'));
const Warehouses = lazy(() => import('./pages/Warehouses'));
const Analytics = lazy(() => import('./pages/Analytics'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const Transfers = lazy(() => import('./pages/Transfers'));
const Users = lazy(() => import('./pages/Users'));
const Tracking = lazy(() => import('./pages/Tracking'));
const Reports = lazy(() => import('./pages/Reports'));
const Departments = lazy(() => import('./pages/Departments'));
const Settings = lazy(() => import('./pages/Settings'));

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <AppContent />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function AppContent() {
  useSSE(); // Global real-time listener

  return (
    <Router>
      <Suspense fallback={<div className="h-screen w-screen flex items-center justify-center bg-slate-50 text-brand-primary font-black animate-pulse uppercase tracking-[0.2em] text-xs">Loading TrackIT Core...</div>}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route 
            path="/*" 
            element={
              <ProtectedRoute>
                <LayoutShell>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/inventory" element={<Inventory />} />
                    <Route path="/assets" element={<Assets />} />
                    <Route path="/warehouses" element={<Warehouses />} />
                    <Route 
                      path="/analytics" 
                      element={
                        <ProtectedRoute allowedRoles={['admin', 'store_manager', 'auditor', 'dept_head', 'staff', 'viewer']}>
                          <Analytics />
                        </ProtectedRoute>
                      } 
                    />
                    <Route path="/transfers" element={<Transfers />} />
                    <Route 
                      path="/users" 
                      element={
                        <ProtectedRoute allowedRoles={['admin']}>
                          <Users />
                        </ProtectedRoute>
                      } 
                    />
                    <Route path="/tracking" element={<Tracking />} />
                    <Route 
                      path="/reports" 
                      element={
                        <ProtectedRoute allowedRoles={['admin', 'auditor', 'store_manager']}>
                          <Reports />
                        </ProtectedRoute>
                      } 
                    />
                    <Route 
                      path="/departments" 
                      element={
                        <ProtectedRoute allowedRoles={['admin']}>
                          <Departments />
                        </ProtectedRoute>
                      } 
                    />
                    <Route 
                      path="/settings" 
                      element={
                        <ProtectedRoute allowedRoles={['admin']}>
                          <Settings />
                        </ProtectedRoute>
                      } 
                    />
                    <Route 
                      path="/audit-logs" 
                      element={
                        <ProtectedRoute allowedRoles={['admin', 'auditor']}>
                          <AuditLogs />
                        </ProtectedRoute>
                      } 
                    />
                  </Routes>
                </LayoutShell>
              </ProtectedRoute>
            } 
          />
        </Routes>
      </Suspense>
      <ToastContainer />
    </Router>
  );
}

export default App;
