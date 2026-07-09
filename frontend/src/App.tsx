import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import { WarehouseProvider } from "./context/WarehouseContext";
import { LayoutShell } from "./components/layout/LayoutShell";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { ToastContainer } from "./components/ui/ToastContainer";
import { useSSE } from "./hooks/useSSE";
import { LiveTrackingProvider } from "./context/LiveTrackingContext";
import { Suspense, lazy } from "react";

// Pages
const Login = lazy(() => import("./pages/Login"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const Register = lazy(() => import("./pages/Register"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Inventory = lazy(() => import("./pages/Inventory"));
const Assets = lazy(() => import("./pages/Assets"));
const Warehouses = lazy(() => import("./pages/Warehouses"));
const Analytics = lazy(() => import("./pages/Analytics"));
const AuditLogs = lazy(() => import("./pages/AuditLogs"));
const Transfers = lazy(() => import("./pages/Transfers"));
const Users = lazy(() => import("./pages/Users"));
const Tracking = lazy(() => import("./pages/Tracking"));
const Reports = lazy(() => import("./pages/Reports"));
const Departments = lazy(() => import("./pages/Departments"));
const Settings = lazy(() => import("./pages/Settings"));
const Requisitions = lazy(() => import("./pages/Requisitions"));
const PurchaseRequests = lazy(
  () => import("./pages/procurement/PurchaseRequests"),
);
const PurchaseOrders = lazy(() => import("./pages/procurement/PurchaseOrders"));
const GoodsReceipts = lazy(() => import("./pages/receiving/GoodsReceipts"));
const Suppliers = lazy(() => import("./pages/procurement/Suppliers"));
const Employees = lazy(() => import("./pages/Employees"));
const EmployeeDetails = lazy(() => import("./pages/EmployeeDetails"));
const IssueReturn = lazy(() => import("./pages/IssueReturn"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes (prevents aggressive refetching)
      gcTime: 10 * 60 * 1000,   // 10 minutes cache garbage collection
      retry: 1,                 // Retry failed queries once
      refetchOnWindowFocus: false, // Don't refetch every time the user switches tabs
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <WarehouseProvider>
            <LiveTrackingProvider>
              <AppContent />
            </LiveTrackingProvider>
          </WarehouseProvider>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function AppContent() {
  useSSE(); // Global real-time listener

  return (
    <Router>
      <Suspense
        fallback={
          <div className="h-screen w-screen flex items-center justify-center bg-slate-50 text-brand-primary font-black animate-pulse uppercase tracking-[0.2em] text-xs">
            Loading TrackIT Core...
          </div>
        }
      >
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
                    <Route path="/requisitions" element={<Requisitions />} />
                    <Route
                      path="/purchase-requests"
                      element={<PurchaseRequests />}
                    />
                    <Route
                      path="/purchase-orders"
                      element={<PurchaseOrders />}
                    />
                    <Route path="/goods-receipts" element={<GoodsReceipts />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/transfers" element={<Transfers />} />
                    <Route
                      path="/users"
                      element={
                        <ProtectedRoute allowedRoles={["admin"]}>
                          <Users />
                        </ProtectedRoute>
                      }
                    />
                    <Route path="/tracking" element={<Tracking />} />
                    <Route
                      path="/reports"
                      element={
                        <ProtectedRoute
                          allowedRoles={[
                            "admin",
                            "superadmin",
                            "auditor",
                            "store_manager",
                            "procurement_officer",
                            "logistics_officer",
                            "employee",
                          ]}
                        >
                          <Reports />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/suppliers"
                      element={
                        <ProtectedRoute
                          allowedRoles={[
                            "admin",
                            "procurement_officer",
                            "store_manager",
                            "logistics_officer",
                            "auditor",
                          ]}
                        >
                          <Suppliers />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/departments"
                      element={
                        <ProtectedRoute allowedRoles={["admin"]}>
                          <Departments />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/employees"
                      element={
                        <ProtectedRoute allowedRoles={["admin"]}>
                          <Employees />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/employees/:id"
                      element={
                        <ProtectedRoute allowedRoles={["admin"]}>
                          <EmployeeDetails />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/movements"
                      element={
                        <ProtectedRoute allowedRoles={["admin","store_manager"]}>
                          <IssueReturn />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/settings"
                      element={
                        <ProtectedRoute allowedRoles={["admin"]}>
                          <Settings />
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="/audit-logs"
                      element={
                        <ProtectedRoute allowedRoles={["admin", "auditor"]}>
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
