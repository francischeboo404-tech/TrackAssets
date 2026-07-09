import React, { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Lock,
  Mail,
  ArrowRight,
  ShieldCheck,
  Activity,
  Eye,
  EyeOff,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import api from "../services/api";

import { Logo } from "../components/ui/Logo";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Forgot Password State
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [isForgotSubmitting, setIsForgotSubmitting] = useState(false);

  const { login } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const from =
    (location.state?.from?.pathname || "/") +
    (location.state?.from?.search || "");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await api.post("/auth/login", { email, password });
      const { user, access_token, refresh_token } = response.data;

      login(access_token ?? "", user, refresh_token ?? null);
      addToast("success", "Welcome back to TrackIT");
      navigate(from, { replace: true });
    } catch (err: any) {
      addToast(
        "error",
        err.response?.data?.message || "Invalid email or password",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail) return;
    
    setIsForgotSubmitting(true);
    try {
      await api.post("/auth/forgot-password", { email: forgotEmail });
      addToast("success", "If that email is registered, a reset link has been sent.");
      setShowForgotModal(false);
      setForgotEmail("");
    } catch (err: any) {
      // Endpoint always returns 200 to prevent enumeration, but catch network errors
      addToast("error", err.response?.data?.message || "Failed to request password reset");
    } finally {
      setIsForgotSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Decorative Elements */}
      <div className="absolute top-0 left-0 w-full h-full opacity-60 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-400 rounded-full blur-[120px] animate-pulse"></div>
        <div
          className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-400 rounded-full blur-[120px] animate-pulse"
          style={{ animationDelay: "2s" }}
        ></div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-[440px] relative z-10"
      >
        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/60 rounded-[2rem] p-10 shadow-2xl overflow-hidden group">
          {/* Header */}
          <div className="mb-10 flex flex-col items-center">
            <Logo className="mb-2" />
            <p className="text-slate-500 text-sm font-medium">
              Enterprise Asset Management
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-5 h-5" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email Address"
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-12 pr-4 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary/50 transition-all duration-300"
                  required
                />
              </div>

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-12 pr-12 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary/50 transition-all duration-300"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm font-medium text-slate-500 px-1">
              <label className="flex items-center gap-2 cursor-pointer hover:text-brand-primary transition-colors">
                <input
                  type="checkbox"
                  className="rounded-sm bg-white border-slate-300 text-brand-primary focus:ring-brand-primary/20"
                />
                <span>Remember me</span>
              </label>
              <button
                type="button"
                onClick={() => setShowForgotModal(true)}
                className="hover:text-brand-primary transition-colors"
              >
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-brand-primary hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-2xl shadow-lg shadow-brand-primary/20 flex items-center justify-center gap-3 transition-all duration-300 group/btn active:scale-[0.98]"
            >
              {isSubmitting ? (
                <Activity className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Footer Info */}
          <div className="mt-10 pt-8 border-t border-slate-100 text-center">
            <p className="mt-8 text-center text-xs font-bold text-slate-400 uppercase tracking-widest">
              New Institution?{" "}
              <Link
                to="/register"
                className="text-indigo-600 hover:text-indigo-700 underline decoration-indigo-200 underline-offset-4"
              >
                Register Workspace
              </Link>
            </p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="mt-8 flex justify-center gap-8">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-xs text-slate-500 font-medium">
              System Online
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-primary"></div>
            <span className="text-xs text-slate-500 font-medium">v4.0.0</span>
          </div>
        </div>
      </motion.div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative"
          >
            <button
              onClick={() => setShowForgotModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-xl font-bold text-slate-800 mb-2">Reset Password</h3>
            <p className="text-sm text-slate-500 mb-6">
              Enter your email address and we'll send you a link to reset your password.
            </p>
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-brand-primary transition-colors">
                    <Mail className="w-5 h-5" />
                  </div>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="name@institution.edu"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 pl-12 pr-4 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary/50 transition-all duration-300"
                    required
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={isForgotSubmitting || !forgotEmail}
                className="w-full bg-brand-primary hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-all duration-300"
              >
                {isForgotSubmitting ? (
                  <Activity className="w-5 h-5 animate-spin" />
                ) : (
                  "Send Reset Link"
                )}
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default LoginPage;
