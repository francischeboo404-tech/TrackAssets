import React, { useState, useEffect, useRef } from 'react';
import { Bell, Search, Menu, Camera, Sparkles, Loader2, Package, Box, Users, Building2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useGlobalSearch } from '../../hooks/useSearch';
import { useAlerts } from '../../hooks/useDashboard';
import { useNavigate } from 'react-router-dom';
import { asArray } from '../../lib/apiResponse';

function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + ' years ago';
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + ' months ago';
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + ' days ago';
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + ' hours ago';
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + ' minutes ago';
  return Math.floor(seconds) + ' seconds ago';
}

export const TopBar: React.FC<{ onMenuClick: () => void; onScanClick: () => void }> = ({ onMenuClick, onScanClick }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  
  const { data: searchResults, isLoading: searchLoading } = useGlobalSearch(searchQuery);
  const { data: alerts } = useAlerts();
  const alertList = asArray<{
    id: number;
    item_name: string;
    message: string;
    created_at: string;
  }>(alerts);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotificationsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === 'Escape') {
        setIsSearchFocused(false);
        searchInputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleResultClick = (type: string, id: number, label?: string) => {
    setIsSearchFocused(false);
    setSearchQuery('');
    const q = label ? `?q=${encodeURIComponent(label)}` : '';
    switch (type) {
      case 'Asset':
        navigate(`/assets${q}`);
        break;
      case 'Inventory':
        navigate(`/inventory${q}`);
        break;
      case 'User':
        navigate('/users');
        break;
      case 'Department':
        navigate(`/departments${q}`);
        break;
      default:
        break;
    }
  };

  const hasResults = searchResults && (
    searchResults.assets.length > 0 || 
    searchResults.inventory.length > 0 || 
    searchResults.users.length > 0 || 
    searchResults.departments.length > 0
  );

  return (
    <header className="h-[64px] sm:h-[72px] bg-white/70 backdrop-blur-2xl border-b border-slate-200/50 flex items-center justify-between px-3 sm:px-8 sticky top-0 z-30 transition-all">
      <div className="flex items-center gap-2 sm:gap-4 flex-1 max-w-2xl">
        <button 
          onClick={onMenuClick}
          className="p-1.5 sm:p-2 hover:bg-slate-100/80 rounded-xl lg:hidden text-slate-600 transition-colors"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        
        <div className="relative group w-full hidden sm:block z-50">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors duration-300" />
          <input 
            ref={searchInputRef}
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
            placeholder="Command center: Search SKU, assets, users..."
            className="w-full bg-slate-100/50 border border-slate-200/50 rounded-2xl py-2.5 pl-10 pr-4 text-sm focus:ring-4 focus:ring-brand-primary/10 focus:bg-white focus:border-brand-primary/30 transition-all duration-300 outline-none font-medium placeholder:text-slate-400 shadow-inner shadow-slate-100/50"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 pointer-events-none">
            {searchLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-brand-primary" />
            ) : (
              <>
                <kbd className="hidden lg:inline-flex items-center justify-center px-2 py-0.5 text-[10px] font-bold text-slate-400 bg-white border border-slate-200 rounded-md shadow-sm">⌘</kbd>
                <kbd className="hidden lg:inline-flex items-center justify-center px-2 py-0.5 text-[10px] font-bold text-slate-400 bg-white border border-slate-200 rounded-md shadow-sm">K</kbd>
              </>
            )}
          </div>
          
          {/* Search Results Dropdown */}
          {isSearchFocused && searchQuery.length >= 2 && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden z-50 max-h-[70vh] sm:max-h-[400px] overflow-y-auto animate-in slide-in-from-top-2 duration-200">
              {!searchLoading && !hasResults ? (
                <div className="p-8 text-center">
                  <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Search className="w-6 h-6 text-slate-300" />
                  </div>
                  <p className="text-sm text-slate-500 font-medium">No results found for "{searchQuery}"</p>
                  <p className="text-xs text-slate-400 mt-1">Try searching for SKU, name, or department</p>
                </div>
              ) : (
                <div className="py-2 divide-y divide-slate-50">
                  {searchResults?.assets.length ? (
                    <div className="px-3 py-2">
                      <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 px-2 flex items-center gap-2">
                        <Package className="w-3 h-3" /> Assets
                      </h4>
                      {searchResults.assets.map(asset => (
                        <button key={`asset-${asset.id}`} onClick={() => handleResultClick('Asset', asset.id, asset.name || asset.code)} className="w-full text-left px-3 py-2.5 hover:bg-slate-50 rounded-xl flex items-center gap-3 group transition-colors">
                          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg group-hover:bg-indigo-100 transition-colors"><Package className="w-4 h-4" /></div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-bold text-slate-700 truncate">{asset.name}</div>
                            <div className="text-[10px] text-slate-400 font-bold font-mono tracking-tight">{asset.code}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : null}
                  
                  {searchResults?.inventory.length ? (
                    <div className="px-3 py-2">
                      <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 px-2 flex items-center gap-2">
                        <Box className="w-3 h-3" /> Inventory
                      </h4>
                      {searchResults.inventory.map(inv => (
                        <button key={`inv-${inv.id}`} onClick={() => handleResultClick('Inventory', inv.id, inv.name || inv.code)} className="w-full text-left px-3 py-2.5 hover:bg-slate-50 rounded-xl flex items-center gap-3 group transition-colors">
                          <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg group-hover:bg-emerald-100 transition-colors"><Box className="w-4 h-4" /></div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-bold text-slate-700 truncate">{inv.name}</div>
                            <div className="text-[10px] text-slate-400 font-bold font-mono tracking-tight">{inv.code}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : null}

                  {searchResults?.users.length ? (
                    <div className="px-3 py-2">
                      <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 px-2 flex items-center gap-2">
                        <Users className="w-3 h-3" /> Users
                      </h4>
                      {searchResults.users.map(u => (
                        <button key={`user-${u.id}`} onClick={() => handleResultClick('User', u.id)} className="w-full text-left px-3 py-2.5 hover:bg-slate-50 rounded-xl flex items-center gap-3 group transition-colors">
                          <div className="p-2 bg-rose-50 text-rose-600 rounded-lg group-hover:bg-rose-100 transition-colors"><Users className="w-4 h-4" /></div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-bold text-slate-700 truncate">{u.name}</div>
                            <div className="text-[10px] text-slate-400 font-medium truncate">{u.code}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : null}

                  {searchResults?.departments.length ? (
                    <div className="px-3 py-2">
                      <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 px-2 flex items-center gap-2">
                        <Building2 className="w-3 h-3" /> Departments
                      </h4>
                      {searchResults.departments.map(d => (
                        <button key={`dept-${d.id}`} onClick={() => handleResultClick('Department', d.id)} className="w-full text-left px-3 py-2.5 hover:bg-slate-50 rounded-xl flex items-center gap-3 group transition-colors">
                          <div className="p-2 bg-amber-50 text-amber-600 rounded-lg group-hover:bg-amber-100 transition-colors"><Building2 className="w-4 h-4" /></div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-bold text-slate-700 truncate">{d.name}</div>
                            <div className="text-[10px] text-slate-400 font-bold font-mono tracking-tight">{d.code}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-6">
        <button 
          onClick={onScanClick}
          className="flex items-center gap-2 bg-gradient-to-r from-brand-primary to-brand-400 hover:from-brand-700 hover:to-brand-500 text-white px-3 py-2 sm:px-5 sm:py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 shadow-lg shadow-brand-primary/20 hover:shadow-xl hover:shadow-brand-primary/30 hover:-translate-y-0.5 group border border-brand-primary/20"
        >
          <Camera className="w-4 h-4 sm:w-4 sm:h-4 group-hover:scale-110 transition-transform" />
          <span className="hidden sm:inline tracking-tight">Scan Entity</span>
        </button>

        <div ref={notifRef} className="relative">
          <div 
            onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
            className="relative cursor-pointer hover:bg-slate-100 p-2 rounded-full transition-colors group"
          >
            <Bell className="w-5 h-5 text-slate-500 group-hover:text-slate-800 transition-colors" />
            {alertList.length > 0 && (
              <span className="absolute top-1.5 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-white animate-pulse-slow"></span>
            )}
          </div>
          
          {isNotificationsOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden z-50">
              <div className="p-3 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-bold text-slate-800 text-sm">Notifications</h3>
                <span className="text-xs font-bold bg-brand-primary/10 text-brand-primary px-2 py-0.5 rounded-md">
                  {alertList.length} New
                </span>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {alertList.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    <Bell className="w-8 h-8 mx-auto mb-2 opacity-20" />
                    <p className="text-sm font-medium">You're all caught up!</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {alertList.map(alert => (
                      <div key={alert.id} className="p-3 hover:bg-slate-50 transition-colors flex gap-3 items-start">
                        <div className="p-1.5 rounded-lg bg-rose-50 shrink-0">
                          <Package className="w-4 h-4 text-rose-600" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-800 leading-tight mb-0.5">{alert.item_name}</p>
                          <p className="text-xs text-slate-500 mb-1">{alert.message}</p>
                          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                            {timeAgo(alert.created_at)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        <div className="h-8 w-px bg-slate-200 hidden sm:block" />

        <div className="flex items-center gap-3 pl-1 sm:pl-1 group cursor-pointer">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-bold text-slate-900 leading-none group-hover:text-brand-primary transition-colors tracking-tight">{user?.username || 'Executive User'}</p>
            <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mt-1 flex items-center justify-end gap-1">
              <Sparkles className="w-3 h-3 text-brand-primary" /> {user?.role || 'Administrator'}
            </p>
          </div>
          <div className="w-8 h-8 sm:w-11 sm:h-11 bg-gradient-to-tr from-brand-primary to-brand-300 rounded-lg sm:rounded-2xl flex items-center justify-center shadow-lg shadow-brand-primary/20 text-white font-bold p-0.5 group-hover:scale-105 transition-transform duration-300 ring-2 ring-white">
            <div className="w-full h-full bg-white/20 rounded-[6px] sm:rounded-[14px] backdrop-blur-sm flex items-center justify-center text-sm sm:text-lg shadow-inner">
              {user?.username?.[0].toUpperCase() || 'E'}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
