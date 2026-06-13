import React, { useState, useEffect, useRef } from 'react';
import { Settings as SettingsIcon, Building, Shield, Bell, Database, Globe, Save, Upload, Lock, Clock, Mail, AlertTriangle, Download, Trash2, Key } from 'lucide-react';
import { Logo } from '../components/ui/Logo';
import { useOrganizationSettings, useUpdateOrganizationSettings, useUploadOrganizationLogo, useExportData, usePurgeData } from '../hooks/useSettings';
import { useToast } from '../context/ToastContext';
import { Can } from '../components/auth/Can';
import { cn } from '../lib/utils';
import { resolveStaticUrl } from '../lib/urls';
import { motion, AnimatePresence } from 'framer-motion';

const Settings = () => {
  const { data: org, isLoading, isError, error, refetch } = useOrganizationSettings();
  const updateOrg = useUpdateOrganizationSettings();
  const uploadLogo = useUploadOrganizationLogo();
  const { addToast } = useToast();
  const exportData = useExportData();
  const purgeData = usePurgeData();
  
  const [orgName, setOrgName] = useState('');
  const [activeTab, setActiveTab] = useState('general');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync state when data loads
  useEffect(() => {
    if (org?.name) setOrgName(org.name);
  }, [org]);

  const handleSave = () => {
    if (!orgName.trim() || orgName === org?.name) return;
    updateOrg.mutate({ name: orgName });
  };
  
  const handlePreferenceToggle = (key: string, value: any) => {
    updateOrg.mutate({ 
      preferences: { ...(org?.preferences || {}), [key]: value } 
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      addToast('error', 'File Too Large', 'Logo must be 2MB or smaller.');
      return;
    }
    uploadLogo.mutate(file);
  };

  const getPreference = (key: string, defaultValue: any = false) => {
    return org?.preferences?.[key] ?? defaultValue;
  };

  if (isError) {
    return (
      <div className="max-w-lg mx-auto py-20 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Could not load settings</h2>
        <p className="text-sm text-slate-500">
          {(error as any)?.response?.data?.message || 'Access denied or server error.'}
        </p>
        <button type="button" onClick={() => refetch()} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-20">
      <div>
        <h1 className="text-4xl font-black text-slate-900 tracking-tighter flex items-center gap-4" style={{ fontFamily: 'Outfit' }}>
          <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100 text-brand-primary">
            <SettingsIcon className="w-8 h-8" />
          </div>
          System Configuration
        </h1>
        <p className="text-slate-500 font-medium tracking-tight text-lg ml-1 mt-2">Configure institutional preferences, security policies, and data management.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        <div className="md:col-span-3 space-y-2">
          <nav className="flex flex-col gap-2 sticky top-24">
             {[
               { id: 'general', label: 'General', icon: Building },
               { id: 'security', label: 'Security & Access', icon: Shield },
               { id: 'notifications', label: 'Notifications', icon: Bell },
               { id: 'data', label: 'Data Management', icon: Database },
             ].map(item => (
               <button 
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={cn(
                  "flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-bold transition-all text-left group",
                  activeTab === item.id 
                    ? "bg-slate-900 text-white shadow-lg shadow-slate-900/10" 
                    : "text-slate-500 hover:text-slate-900 hover:bg-white"
                )}
               >
                 <item.icon className={cn(
                   "w-4 h-4 transition-transform", 
                   activeTab === item.id ? "scale-110" : "group-hover:scale-110"
                 )} /> 
                 {item.label}
               </button>
             ))}
          </nav>
        </div>

        <div className="md:col-span-9">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              
              {activeTab === 'general' && (
                <>
                  <section className="enterprise-card bg-white p-8 space-y-8">
                    <div className="border-b border-slate-100 pb-6">
                      <h2 className="text-xl font-bold text-slate-900">Institutional Profile</h2>
                      <p className="text-sm text-slate-500 mt-1">Update your organization's public identity.</p>
                    </div>

                    <div className="space-y-8">
                       <div className="flex items-center gap-8">
                          <input 
                            type="file" 
                            accept=".png,.jpg,.jpeg,.svg" 
                            className="hidden" 
                            ref={fileInputRef} 
                            onChange={handleFileChange}
                          />
                          <div className="relative group">
                            <div 
                              onClick={() => fileInputRef.current?.click()}
                              className="w-24 h-24 rounded-2xl bg-slate-50 flex items-center justify-center border-2 border-dashed border-slate-200 group-hover:border-brand-primary/50 transition-colors cursor-pointer overflow-hidden"
                            >
                               {org?.logo_url ? (
                                  <img src={resolveStaticUrl(org.logo_url)} alt="Organization Logo" className="w-full h-full object-contain" />
                               ) : (
                                  <Logo showText={false} />
                               )}
                               <div className={cn(
                                 "absolute inset-0 bg-slate-900/40 rounded-2xl flex items-center justify-center transition-opacity",
                                 org?.logo_url ? "opacity-0 group-hover:opacity-100" : "opacity-0 group-hover:opacity-100"
                               )}>
                                  {uploadLogo.isPending ? (
                                    <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                  ) : (
                                    <Upload className="w-6 h-6 text-white" />
                                  )}
                               </div>
                            </div>
                          </div>
                          <div>
                            <h3 className="font-bold text-slate-800">Organization Logo</h3>
                            <p className="text-xs text-slate-500 mt-1 mb-4">PNG, JPG or SVG. Max 2MB.</p>
                            <button 
                              onClick={() => fileInputRef.current?.click()}
                              disabled={uploadLogo.isPending}
                              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-black uppercase tracking-widest transition-colors disabled:opacity-50"
                            >
                              {uploadLogo.isPending ? 'Uploading...' : 'Update Logo'}
                            </button>
                          </div>
                       </div>

                       <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <label className="text-xs font-black uppercase tracking-widest text-slate-400 ml-1">Organization Name</label>
                            <input 
                              type="text" 
                              value={orgName}
                              disabled={isLoading || updateOrg.isPending}
                              onChange={(e) => setOrgName(e.target.value)}
                              className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 px-4 text-sm font-bold focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary/20 outline-none transition-all disabled:opacity-50"
                            />
                          </div>
                          <div className="space-y-2">
                            <label className="text-xs font-black uppercase tracking-widest text-slate-400 ml-1">Organization Code</label>
                            <div className="flex items-center gap-2">
                               <input 
                                type="text" 
                                disabled 
                                value={org?.code || 'LOADING...'}
                                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl py-3 px-4 text-sm font-bold text-slate-400"
                              />
                              <button className="p-3 bg-white border border-slate-200 rounded-xl text-slate-400 transition-colors">
                                <Globe className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                          <div className="space-y-2 md:col-span-2">
                            <label className="text-xs font-black uppercase tracking-widest text-slate-400 ml-1">Default Currency</label>
                            <select
                              value={getPreference('currency', 'KES')}
                              disabled={updateOrg.isPending}
                              onChange={(e) => handlePreferenceToggle('currency', e.target.value)}
                              className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 px-4 text-sm font-bold outline-none"
                            >
                              {['KES', 'USD', 'EUR', 'GBP', 'UGX', 'TZS'].map((c) => (
                                <option key={c} value={c}>{c}</option>
                              ))}
                            </select>
                            <p className="text-[10px] text-slate-400 ml-1">Used on dashboard, reports, and analytics.</p>
                          </div>
                       </div>
                    </div>

                    <Can roles={['admin']}>
                      <div className="pt-6 border-t border-slate-100 flex justify-end">
                         <button 
                          onClick={handleSave}
                          disabled={updateOrg.isPending || orgName === org?.name}
                          className="btn-primary flex items-center gap-2 disabled:opacity-50 px-8"
                         >
                           <Save className="w-4 h-4" /> {updateOrg.isPending ? 'Saving...' : 'Save Changes'}
                         </button>
                      </div>
                    </Can>
                  </section>

                  <section className="enterprise-card bg-rose-50/30 border-rose-100 p-8">
                     <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-rose-100 flex items-center justify-center text-rose-600 flex-shrink-0">
                           <Shield className="w-6 h-6" />
                        </div>
                        <div>
                           <h3 className="text-lg font-bold text-slate-900">Institutional Security Baseline</h3>
                           <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                              Your organization is operating under strict multi-tenant isolation. All actions are logged to the immutable audit ledger. Contact the system administrator to modify these baseline constraints.
                           </p>
                        </div>
                     </div>
                  </section>
                </>
              )}

              {activeTab === 'security' && (
                <>
                  <section className="enterprise-card bg-white p-8 space-y-8">
                    <div className="border-b border-slate-100 pb-6">
                      <h2 className="text-xl font-bold text-slate-900">Authentication & Security</h2>
                      <p className="text-sm text-slate-500 mt-1">Manage password policies, sessions, and access control.</p>
                    </div>

                    <div className="space-y-6">
                      <p className="text-xs text-slate-500 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3">
                        Policy toggles are saved to your organization profile. Currency and alert preferences are active immediately. Session timeout and 2FA flags are stored for compliance reporting and future enforcement.
                      </p>
                      <div className="flex items-center justify-between p-5 border border-slate-100 rounded-2xl bg-slate-50">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-white rounded-xl shadow-sm"><Lock className="w-5 h-5 text-indigo-500" /></div>
                          <div>
                            <h4 className="font-bold text-slate-800">Two-Factor Authentication (2FA)</h4>
                            <p className="text-xs text-slate-500 mt-0.5">Policy flag — enforcement planned in a future release.</p>
                          </div>
                        </div>
                        <button 
                          onClick={() => handlePreferenceToggle('require_2fa', !getPreference('require_2fa'))}
                          className={cn("w-12 h-6 rounded-full relative transition-colors", getPreference('require_2fa') ? "bg-brand-primary" : "bg-slate-200")}
                        >
                          <div className={cn("w-4 h-4 bg-white rounded-full absolute top-1 transition-all", getPreference('require_2fa') ? "right-1" : "left-1")} />
                        </button>
                      </div>

                      <div className="flex items-center justify-between p-5 border border-slate-100 rounded-2xl bg-slate-50">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-white rounded-xl shadow-sm"><Key className="w-5 h-5 text-emerald-500" /></div>
                          <div>
                            <h4 className="font-bold text-slate-800">Strict Password Policy</h4>
                            <p className="text-xs text-slate-500 mt-0.5">Enforce 12+ character passwords with symbol requirements.</p>
                          </div>
                        </div>
                        <button 
                          onClick={() => handlePreferenceToggle('strict_password', !getPreference('strict_password', true))}
                          className={cn("w-12 h-6 rounded-full relative transition-colors", getPreference('strict_password', true) ? "bg-brand-primary" : "bg-slate-200")}
                        >
                          <div className={cn("w-4 h-4 bg-white rounded-full absolute top-1 transition-all", getPreference('strict_password', true) ? "right-1" : "left-1")} />
                        </button>
                      </div>

                      <div className="flex items-center justify-between p-5 border border-slate-100 rounded-2xl bg-slate-50">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-white rounded-xl shadow-sm"><Clock className="w-5 h-5 text-amber-500" /></div>
                          <div>
                            <h4 className="font-bold text-slate-800">Session Timeout</h4>
                            <p className="text-xs text-slate-500 mt-0.5">Automatically log users out after inactivity.</p>
                          </div>
                        </div>
                        <select 
                          value={getPreference('session_timeout', 60)}
                          onChange={(e) => handlePreferenceToggle('session_timeout', parseInt(e.target.value))}
                          className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm font-bold text-slate-700 outline-none"
                        >
                          <option value={30}>30 Minutes</option>
                          <option value={60}>1 Hour</option>
                          <option value={240}>4 Hours</option>
                        </select>
                      </div>
                    </div>
                  </section>
                </>
              )}

              {activeTab === 'notifications' && (
                <>
                  <section className="enterprise-card bg-white p-8 space-y-8">
                    <div className="border-b border-slate-100 pb-6">
                      <h2 className="text-xl font-bold text-slate-900">Alert Routing</h2>
                      <p className="text-sm text-slate-500 mt-1">Configure where and how system notifications are delivered.</p>
                    </div>

                    <div className="space-y-6">
                      <div className="flex items-center justify-between p-5 border border-slate-100 rounded-2xl bg-slate-50">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-white rounded-xl shadow-sm"><Mail className="w-5 h-5 text-brand-primary" /></div>
                          <div>
                            <h4 className="font-bold text-slate-800">Daily Inventory Digest</h4>
                            <p className="text-xs text-slate-500 mt-0.5">Receive a summary email of all inventory movements and updates.</p>
                          </div>
                        </div>
                        <button 
                          onClick={() => handlePreferenceToggle('daily_digest', !getPreference('daily_digest'))}
                          className={cn("w-12 h-6 rounded-full relative transition-colors", getPreference('daily_digest') ? "bg-brand-primary" : "bg-slate-200")}
                        >
                          <div className={cn("w-4 h-4 bg-white rounded-full absolute top-1 transition-all", getPreference('daily_digest') ? "right-1" : "left-1")} />
                        </button>
                      </div>

                      <div className="flex items-center justify-between p-5 border border-slate-100 rounded-2xl bg-slate-50">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-white rounded-xl shadow-sm"><AlertTriangle className="w-5 h-5 text-rose-500" /></div>
                          <div>
                            <h4 className="font-bold text-slate-800">Critical Stock Alerts</h4>
                            <p className="text-xs text-slate-500 mt-0.5">Immediate notifications when items drop below minimum thresholds.</p>
                          </div>
                        </div>
                        <button 
                          onClick={() => handlePreferenceToggle('critical_alerts', !getPreference('critical_alerts', true))}
                          className={cn("w-12 h-6 rounded-full relative transition-colors", getPreference('critical_alerts', true) ? "bg-brand-primary" : "bg-slate-200")}
                        >
                          <div className={cn("w-4 h-4 bg-white rounded-full absolute top-1 transition-all", getPreference('critical_alerts', true) ? "right-1" : "left-1")} />
                        </button>
                      </div>
                    </div>
                  </section>
                </>
              )}

              {activeTab === 'data' && (
                <>
                  <section className="enterprise-card bg-white p-8 space-y-8">
                    <div className="border-b border-slate-100 pb-6">
                      <h2 className="text-xl font-bold text-slate-900">Data & Compliance</h2>
                      <p className="text-sm text-slate-500 mt-1">Manage data exports, compliance reporting, and ledger retention.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="p-6 border border-slate-100 rounded-2xl bg-slate-50 space-y-4">
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center">
                          <Download className="w-6 h-6 text-brand-primary" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-800 text-lg">System Export</h4>
                          <p className="text-sm text-slate-500 mt-1">Download a complete CSV backup of all current inventory and asset data.</p>
                        </div>
                        <button 
                          onClick={() => exportData.mutate()}
                          disabled={exportData.isPending}
                          className="px-5 py-2.5 bg-brand-primary text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-brand-600 transition-colors w-full disabled:opacity-50"
                        >
                          {exportData.isPending ? 'Generating...' : 'Generate Export'}
                        </button>
                      </div>

                      <div className="p-6 border border-rose-100 rounded-2xl bg-rose-50/50 space-y-4">
                        <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center">
                          <Trash2 className="w-6 h-6 text-rose-500" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-800 text-lg">Data Purge</h4>
                          <p className="text-sm text-slate-600 mt-1">Permanently remove historical movement logs older than 3 years.</p>
                        </div>
                        <button 
                          onClick={() => {
                            if (window.confirm("Are you sure you want to permanently delete all historical data older than 3 years? This action cannot be undone.")) {
                              purgeData.mutate();
                            }
                          }}
                          disabled={purgeData.isPending}
                          className="px-5 py-2.5 bg-rose-600 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-rose-700 transition-colors w-full disabled:opacity-50"
                        >
                          {purgeData.isPending ? 'Purging...' : 'Execute Purge'}
                        </button>
                      </div>
                    </div>
                  </section>
                </>
              )}

            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default Settings;
