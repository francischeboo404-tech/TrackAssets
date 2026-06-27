import React from "react";
import {
  LayoutDashboard,
  Package,
  Barcode,
  Warehouse,
  ShoppingCart,
  ClipboardList,
  PackageOpen,
  BarChart3,
  History,
  LogOut,
  ArrowRightLeft,
  Users as UsersIcon,
  Zap,
  QrCode,
  FileText,
  Building2,
  Settings as SettingsIcon,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
import { useAuth } from "../../context/AuthContext";

import { motion, AnimatePresence } from "framer-motion";
import { Can } from "../auth/Can";
import type { UserRole } from "../../types";

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: Package, label: "Inventory", path: "/inventory" },
  { icon: Barcode, label: "Assets", path: "/assets" },
  { icon: ArrowRightLeft, label: "Transfers", path: "/transfers" },
  { icon: Warehouse, label: "Warehouses", path: "/warehouses" },
  { icon: QrCode, label: "Tracking", path: "/tracking" },
  {
    icon: ShoppingCart,
    label: "Purchase Requests",
    path: "/purchase-requests",
  },
  { icon: FileText, label: "Purchase Orders", path: "/purchase-orders" },
  { icon: ClipboardList, label: "Requisitions", path: "/requisitions" },
  { icon: PackageOpen, label: "Goods Receipts", path: "/goods-receipts" },
  { icon: Building2, label: "Suppliers", path: "/suppliers" },
  { icon: UsersIcon, label: "Users", path: "/users" },
  { icon: BarChart3, label: "Analytics", path: "/analytics" },
  { icon: FileText, label: "Reports", path: "/reports" },
  { icon: Building2, label: "Departments", path: "/departments" },
  { icon: History, label: "Audit Logs", path: "/audit-logs" },
  { icon: SettingsIcon, label: "Settings", path: "/settings" },
];

const ROUTE_LABEL_OVERRIDES: Record<string, string> = {
  "/": "Operational Overview",
  "/inventory": "Inventory Management",
  "/assets": "Asset Management",
  "/transfers": "Transfer Operations",
  "/warehouses": "Storage Facilities",
  "/tracking": "Live Tracking",
  "/purchase-requests": "Procurement Requests",
  "/purchase-orders": "Purchase Orders",
  "/requisitions": "Requisition Slips",
  "/goods-receipts": "Goods Receipt Notes",
  "/suppliers": "Supplier Registry",
  "/users": "Team Management",
  "/analytics": "Analytics",
  "/reports": "Reports",
  "/departments": "Departments",
  "/audit-logs": "Audit Logs",
  "/settings": "Settings",
};

const NAV_ITEM_ROLES: Record<string, UserRole[]> = {
  "/users": ["admin"],
  "/departments": ["admin"],
  "/settings": ["admin"],
  "/reports": [
    "admin",
    "superadmin",
    "auditor",
    "store_manager",
    "procurement_officer",
    "logistics_officer",
    "employee",
  ],
  "/audit-logs": ["admin", "auditor"],
  "/suppliers": [
    "admin",
    "procurement_officer",
    "store_manager",
    "logistics_officer",
    "auditor",
  ],
};

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

import { Logo } from "../ui/Logo";

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <>
      {/* Mobile Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      <div
        className={cn(
          "h-screen w-[280px] bg-white text-slate-600 flex flex-col border-r border-slate-200/60 shadow-2xl lg:shadow-none relative overflow-hidden transition-transform duration-300 ease-in-out z-50",
          "fixed lg:static inset-y-0 left-0",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        {/* Decorative gradient background */}
        <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-brand-primary/5 to-transparent pointer-events-none" />

        <div className="p-6 relative z-10">
          <Logo />
        </div>

        <div className="px-6 pb-2 relative z-10">
          <div className="flex items-center gap-2 bg-slate-50/80 border border-slate-100 px-3 py-2 rounded-xl text-xs font-semibold text-slate-500 shadow-inner">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            TrackIT System
          </div>
        </div>

        <nav
          className="flex-1 px-4 py-4 space-y-1.5 overflow-y-auto custom-scrollbar relative z-10"
          aria-label="Main Navigation"
        >
          <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 mt-2">
            Operations
          </p>

          {NAV_ITEMS.filter((i) =>
            [
              "/",
              "/inventory",
              "/assets",
              "/transfers",
              "/warehouses",
              "/tracking",
            ].includes(i.path),
          ).map((item) => {
            const displayLabel = ROUTE_LABEL_OVERRIDES[item.path] || item.label;
            const isActive = location.pathname === item.path;
            const allowedRoles = NAV_ITEM_ROLES[item.path];

            const NavLink = (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={cn(
                  "group flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-300 ease-out relative overflow-hidden",
                  isActive
                    ? "bg-brand-primary text-white font-semibold shadow-md shadow-brand-primary/20"
                    : "hover:bg-slate-50 hover:text-slate-900 text-slate-500 font-medium",
                )}
              >
                <div className="flex items-center gap-3.5 relative z-10">
                  <item.icon
                    className={cn(
                      "w-5 h-5 transition-transform duration-300",
                      isActive
                        ? "text-white"
                        : "text-slate-400 group-hover:text-brand-primary",
                    )}
                  />
                  <span className="tracking-tight text-sm">{displayLabel}</span>
                </div>
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-white relative z-10" />
                )}
              </Link>
            );

            return allowedRoles ? (
              <Can key={item.path} roles={allowedRoles}>
                {NavLink}
              </Can>
            ) : (
              NavLink
            );
          })}

          <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 mt-6">
            Supply Chain
          </p>

          {NAV_ITEMS.filter((i) =>
            [
              "/purchase-requests",
              "/purchase-orders",
              "/requisitions",
              "/goods-receipts",
              "/suppliers",
            ].includes(i.path),
          ).map((item) => {
            const displayLabel = ROUTE_LABEL_OVERRIDES[item.path] || item.label;
            const isActive = location.pathname === item.path;
            const allowedRoles = NAV_ITEM_ROLES[item.path];

            const NavLink = (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={cn(
                  "group flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-300 ease-out relative overflow-hidden",
                  isActive
                    ? "bg-brand-primary text-white font-semibold shadow-md shadow-brand-primary/20"
                    : "hover:bg-slate-50 hover:text-slate-900 text-slate-500 font-medium",
                )}
              >
                <div className="flex items-center gap-3.5 relative z-10">
                  <item.icon
                    className={cn(
                      "w-5 h-5 transition-transform duration-300",
                      isActive
                        ? "text-white"
                        : "text-slate-400 group-hover:text-brand-primary",
                    )}
                  />
                  <span className="tracking-tight text-sm">{displayLabel}</span>
                </div>
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-white relative z-10" />
                )}
              </Link>
            );

            return allowedRoles ? (
              <Can key={item.path} roles={allowedRoles}>
                {NavLink}
              </Can>
            ) : (
              NavLink
            );
          })}

          <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 mt-6">
            Management & Insights
          </p>

          {NAV_ITEMS.filter((i) =>
            [
              "/analytics",
              "/users",
              "/reports",
              "/departments",
              "/audit-logs",
              "/settings",
            ].includes(i.path),
          ).map((item) => {
            const displayLabel = ROUTE_LABEL_OVERRIDES[item.path] || item.label;
            const isActive = location.pathname === item.path;
            const allowedRoles = NAV_ITEM_ROLES[item.path];

            const NavLink = (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={cn(
                  "group flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-300 ease-out relative overflow-hidden",
                  isActive
                    ? "bg-brand-primary text-white font-semibold shadow-md shadow-brand-primary/20"
                    : "hover:bg-slate-50 hover:text-slate-900 text-slate-500 font-medium",
                )}
              >
                <div className="flex items-center gap-3.5 relative z-10">
                  <item.icon
                    className={cn(
                      "w-5 h-5 transition-transform duration-300",
                      isActive
                        ? "text-white"
                        : "text-slate-400 group-hover:text-brand-primary",
                    )}
                  />
                  <span className="tracking-tight text-sm">{displayLabel}</span>
                </div>
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-white relative z-10" />
                )}
              </Link>
            );

            return allowedRoles ? (
              <Can key={item.path} roles={allowedRoles}>
                {NavLink}
              </Can>
            ) : (
              NavLink
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-100/60 mt-auto bg-slate-50/50 relative z-10">
          <button
            onClick={() => {
              void logout();
            }}
            className="flex items-center gap-3.5 w-full px-4 py-3 rounded-xl text-slate-500 hover:text-rose-600 hover:bg-rose-50 hover:shadow-sm hover:border hover:border-rose-100 transition-all font-semibold text-sm group"
          >
            <LogOut className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </>
  );
};
