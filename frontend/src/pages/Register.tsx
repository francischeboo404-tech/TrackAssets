import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building2, User, Mail, Lock, CheckCircle2, ChevronRight, Loader2, Globe } from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { cn } from '../lib/utils';

const Register = () => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    org_name: '',
    org_code: '',
    org_description: '',
    admin_username: '',
    admin_email: '',
    admin_password: '',
    admin_first_name: '',
    admin_last_name: '',
    confirm_password: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    const next =
      name === 'org_code'
        ? value.toUpperCase().replace(/[^A-Z0-9]/g, '_').replace(/_+/g, '_')
        : value;
    setFormData({ ...formData, [name]: next });
  };

  const buildRegisterPayload = () => {
    const {
      confirm_password: _confirm,
      org_name,
      org_code,
      org_description,
      admin_username,
      admin_email,
      admin_password,
      admin_first_name,
      admin_last_name,
    } = formData;

    return {
      org_name: org_name.trim(),
      org_code: org_code.trim().toUpperCase().replace(/[^A-Z0-9]/g, '_').replace(/_+/g, '_'),
      ...(org_description.trim() ? { org_description: org_description.trim() } : {}),
      admin_username: admin_username.trim(),
      admin_email: admin_email.trim().toLowerCase(),
      admin_password,
      ...(admin_first_name.trim() ? { admin_first_name: admin_first_name.trim() } : {}),
      ...(admin_last_name.trim() ? { admin_last_name: admin_last_name.trim() } : {}),
    };
  };

  const formatRegisterError = (data: Record<string, unknown> | undefined): string => {
    if (!data) {
      return 'Check your details and try again.';
    }
    const fieldErrors = data.errors;
    if (fieldErrors && typeof fieldErrors === 'object' && !Array.isArray(fieldErrors)) {
      const parts = Object.entries(fieldErrors as Record<string, string[] | string>).map(
        ([field, msgs]) => {
          const text = Array.isArray(msgs) ? msgs.join(', ') : String(msgs);
          return `${field.replace(/_/g, ' ')}: ${text}`;
        },
      );
      if (parts.length) {
        return parts.join(' · ');
      }
    }
    return String(data.message ?? 'Check your details and try again.');
  };

  const handleNext = () => {
    if (step === 1) {
      if (!formData.org_name || !formData.org_code) {
        addToast('error', 'Missing Information', 'Please provide organization name and code.');
        return;
      }
      const code = formData.org_code.trim();
      if (code.length < 2) {
        addToast('error', 'Invalid Code', 'Institution code must be at least 2 characters.');
        return;
      }
      if (!/^[A-Z0-9_]+$/.test(code)) {
        addToast(
          'error',
          'Invalid Code',
          'Use only letters, numbers, and underscores (e.g. NOVA_LITE).',
        );
        return;
      }
      setStep(2);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.admin_password !== formData.confirm_password) {
      addToast('error', 'Password Mismatch', 'Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const payload = buildRegisterPayload();
      console.log('[Register] Submitting registration form', payload);
      const response = await api.post('/auth/register-org', payload, {
        skipAuthRedirect: true,
      } as const);
      console.log('[Register] Success response:', response.data);
      addToast('success', 'Registration Successful', 'Institution registered. You can now login.');
      navigate('/login');
    } catch (err: any) {
      console.error('[Register] Error during registration:', err);
      console.error('[Register] Error response:', err.response?.data);
      console.error('[Register] Full error:', err);
      addToast(
        'error',
        'Registration Failed',
        formatRegisterError(err.response?.data),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 text-white mb-6 shadow-xl shadow-indigo-200">
            <Building2 className="w-8 h-8" />
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight uppercase">Institution Onboarding</h1>
          <p className="text-slate-500 mt-2 font-medium">Set up your secure TrackIT workspace in minutes.</p>
        </div>

        <div className="bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden">
          <div className="flex bg-slate-50 border-b border-slate-100">
            <div className={cn(
              "flex-1 py-4 text-center text-xs font-bold uppercase tracking-widest transition-colors",
              step === 1 ? "text-indigo-600 bg-white" : "text-slate-400"
            )}>
              1. Institution Profile
            </div>
            <div className={cn(
              "flex-1 py-4 text-center text-xs font-bold uppercase tracking-widest transition-colors",
              step === 2 ? "text-indigo-600 bg-white" : "text-slate-400"
            )}>
              2. Administrator Account
            </div>
          </div>

          <form onSubmit={handleSubmit} className="p-8 md:p-10">
            {step === 1 ? (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Organization Name</label>
                  <div className="relative">
                    <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input 
                      name="org_name"
                      type="text" 
                      required
                      value={formData.org_name}
                      onChange={handleChange}
                      placeholder="e.g. Nova Lite Limited"
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Unique Institution Code</label>
                  <div className="relative">
                    <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input 
                      name="org_code"
                      type="text" 
                      required
                      value={formData.org_code}
                      onChange={handleChange}
                      placeholder="e.g. NOVA_LITE (Uppercase only)"
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 italic px-1">Used for login identification and data isolation.</p>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Description (Optional)</label>
                  <textarea 
                    name="org_description"
                    rows={3}
                    value={formData.org_description}
                    onChange={handleChange}
                    placeholder="Brief overview of the institution..."
                    className="w-full px-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all resize-none"
                  />
                </div>

                <button 
                  type="button"
                  onClick={handleNext}
                  className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center justify-center gap-2"
                >
                  Configure Admin <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">First Name</label>
                    <input 
                      name="admin_first_name"
                      type="text" 
                      value={formData.admin_first_name}
                      onChange={handleChange}
                      className="w-full px-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Last Name</label>
                    <input 
                      name="admin_last_name"
                      type="text" 
                      value={formData.admin_last_name}
                      onChange={handleChange}
                      className="w-full px-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Admin Username</label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input 
                      name="admin_username"
                      type="text" 
                      required
                      value={formData.admin_username}
                      onChange={handleChange}
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Official Email</label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input 
                      name="admin_email"
                      type="email" 
                      required
                      value={formData.admin_email}
                      onChange={handleChange}
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                      <input 
                        name="admin_password"
                        type="password" 
                        required
                        value={formData.admin_password}
                        onChange={handleChange}
                        className="w-full pl-12 pr-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Confirm</label>
                    <input 
                      name="confirm_password"
                      type="password" 
                      required
                      value={formData.confirm_password}
                      onChange={handleChange}
                      className="w-full px-4 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-slate-700 transition-all"
                    />
                  </div>
                </div>

                <div className="flex gap-4">
                  <button 
                    type="button"
                    onClick={() => setStep(1)}
                    className="px-6 py-4 bg-slate-100 text-slate-600 rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-slate-200 transition-all"
                  >
                    Back
                  </button>
                  <button 
                    type="submit"
                    disabled={loading}
                    className="flex-1 py-4 bg-indigo-600 text-white rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle2 className="w-4 h-4" /> Finalize Institution</>}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>

        <p className="text-center mt-8 text-slate-500 text-xs font-bold">
          Already have an institution workspace? <Link to="/login" className="text-indigo-600 hover:underline">Log in here</Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
