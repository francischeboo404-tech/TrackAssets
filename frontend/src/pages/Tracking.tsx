import React, { useState, useEffect, useRef } from 'react';
import { 
  QrCode, Search, History, AlertTriangle, CheckCircle2, Package, 
  MapPin, Navigation, Camera, Smartphone, Globe, List, Layers,
  ChevronRight, ArrowUpRight, ShieldCheck
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import {
  useAllowedScanActions,
  useRecordScan,
  useTrackingHistory,
} from '../hooks/useTracking';
import { TrackingTimeline } from '../components/ui/TrackingTimeline';
import { canPerformScanAction, isReadOnlyScanner } from '../lib/permissions';
import { cn } from '../lib/utils';
import { Html5QrcodeScanner } from 'html5-qrcode';
import { MapContainer, TileLayer, Marker, Popup, useMap, Polyline } from 'react-leaflet';
import L from 'leaflet';
import { useSearchParams } from 'react-router-dom';

// Fix for default marker icons in Leaflet + React
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

// Component to refocus map on new coordinates
function ChangeView({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 13);
  }, [center, map]);
  return null;
}

const Tracking = () => {
  const [searchParams] = useSearchParams();
  const [qrInput, setQrInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [scanResult, setScanResult] = useState<any>(null);
  const [actionType, setActionType] = useState('VERIFY');
  const [notes, setNotes] = useState('');
  const [viewMode, setViewMode] = useState<'MAP' | 'DETAILS'>('DETAILS');
  const [showScanner, setShowScanner] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [mapCenter, setMapCenter] = useState<[number, number]>([-1.286389, 36.817223]); // Default to Nairobi
  
  const { addToast } = useToast();
  const { user } = useAuth();
  const recordScan = useRecordScan();
  const { data: allowedActions } = useAllowedScanActions();
  const scannerRef = useRef<any>(null);

  const actionOptions =
    allowedActions?.actions?.filter((a) =>
      canPerformScanAction(user?.role, a),
    ) || ['VERIFY', 'AUDIT'];

  const { data: timelineHistory, isLoading: historyLoading } = useTrackingHistory(
    scanResult?.item?.type,
    scanResult?.item?.id,
  );

  useEffect(() => {
    if (actionOptions.length && !actionOptions.includes(actionType)) {
      setActionType(actionOptions[0]);
    }
  }, [actionOptions.join(','), user?.role]);

  // Auto-scan if data parameter is present in URL
  useEffect(() => {
    const dataParam = searchParams.get('data');
    if (dataParam) {
      processScan(dataParam);
    }
  }, [searchParams]);

  // Initialize camera scanner
  useEffect(() => {
    if (showScanner) {
      const scanner = new Html5QrcodeScanner(
        "reader", 
        { fps: 10, qrbox: { width: 250, height: 250 } },
        /* verbose= */ false
      );
      
      scanner.render((decodedText) => {
        // If the decoded text is a URL, extract the data parameter
        let scanData = decodedText;
        if (decodedText.includes('?data=')) {
          const url = new URL(decodedText);
          scanData = url.searchParams.get('data') || decodedText;
        }

        setQrInput(scanData);
        setShowScanner(false);
        scanner.clear();
        processScan(scanData);
      }, (error) => {
        // console.warn(error);
      });
      
      scannerRef.current = scanner;
    }
    
    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch((e: any) => console.error(e));
      }
    };
  }, [showScanner]);

  const processScan = async (data: string) => {
    setIsProcessing(true);
    try {
      // Get precise current location asynchronously with high accuracy
      let lat = mapCenter[0];
      let lon = mapCenter[1];
      
      const getPreciseLocation = () => {
        return new Promise<{lat: number, lon: number} | null>((resolve) => {
          if (!navigator.geolocation) {
            resolve(null);
            return;
          }
          navigator.geolocation.getCurrentPosition(
            (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
            (err) => {
              console.warn("Geolocation error:", err);
              resolve(null);
            },
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
          );
        });
      };

      const preciseLoc = await getPreciseLocation();
      if (preciseLoc) {
        lat = preciseLoc.lat;
        lon = preciseLoc.lon;
      }

      const response = await recordScan.mutateAsync({
        qr_data: data,
        action_type: actionType,
        notes: notes,
        lat: lat,
        lon: lon,
      });

      setScanResult(response);
      if (response.history) {
        setHistory(response.history);
      }
      
      if (lat && lon) {
        setMapCenter([lat, lon]);
      }

      addToast('success', 'Scan Recorded', `Movement logged successfully.`);
      setQrInput('');
      setViewMode('MAP');
    } catch (err: any) {
      addToast('error', 'Scan Failed', err.response?.data?.message || 'Invalid QR code or system error.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (qrInput) processScan(qrInput);
  };

  // Convert history to coordinates for the polyline
  const polylineCoords = history
    .filter(h => h.latitude && h.longitude)
    .map(h => [h.latitude, h.longitude] as [number, number]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header with Glassmorphism */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-white/50 backdrop-blur-xl p-8 rounded-[2.5rem] border border-white/20 shadow-2xl shadow-slate-200/50">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-brand-primary p-2 rounded-xl shadow-lg shadow-brand-primary/20">
              <QrCode className="text-white w-6 h-6" />
            </div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">Live Tracking</h1>
          </div>
          <p className="text-slate-500 font-medium">Real-time geospatial monitoring of institutional assets.</p>
        </div>

        <div className="flex bg-slate-100 p-1.5 rounded-2xl border border-slate-200">
           <button 
             onClick={() => setViewMode('DETAILS')}
             className={cn(
               "flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all",
               viewMode === 'DETAILS' ? "bg-white text-slate-900 shadow-md" : "text-slate-500 hover:text-slate-700"
             )}
           >
             <List className="w-4 h-4" /> Operations
           </button>
           <button 
             onClick={() => setViewMode('MAP')}
             className={cn(
               "flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all",
               viewMode === 'MAP' ? "bg-white text-slate-900 shadow-md" : "text-slate-500 hover:text-slate-700"
             )}
           >
             <Globe className="w-4 h-4" /> Map View
           </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Control Panel */}
        <div className="lg:col-span-4 space-y-6">
          {/* Security Banner */}
          <div className="p-4 bg-indigo-900 text-white rounded-2xl shadow-lg flex gap-3">
             <ShieldCheck className="w-5 h-5 text-indigo-400 flex-shrink-0" />
             <p className="text-[10px] font-bold leading-relaxed">
               <strong>Authenticated Access Only:</strong> This item is secured by TrackIT. Scans from outside this application require institutional login to reveal tracking data.
             </p>
          </div>

          {/* Main Scanner Card */}
          <div className="enterprise-card p-6 bg-white shadow-xl border-none">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Scanner Engine</h2>
              <div className="flex gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-emerald-600 uppercase">Live System</span>
              </div>
            </div>
            
            <div className="space-y-6">
              {/* Action Selection */}
              <div className="space-y-3">
                <label className="text-[10px] font-black text-slate-500 uppercase ml-1 flex items-center gap-2">
                  <Navigation className="w-3 h-3" /> Select Operation Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {actionOptions.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setActionType(type)}
                      className={cn(
                        "py-3 rounded-xl text-[10px] font-black transition-all border-2",
                        actionType === type 
                          ? "bg-slate-900 text-white border-slate-900 shadow-lg shadow-slate-900/10" 
                          : "bg-white text-slate-400 border-slate-100 hover:border-slate-200"
                      )}
                    >
                      {type.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* QR Input */}
              <div className="space-y-3">
                <label className="text-[10px] font-black text-slate-500 uppercase ml-1">Asset QR / ID</label>
                <div className="flex gap-2">
                  <div className="relative flex-1 group">
                    <QrCode className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-brand-primary transition-colors" />
                    <input 
                      type="text" 
                      placeholder="Manual entry..."
                      value={qrInput}
                      onChange={(e) => setQrInput(e.target.value)}
                      className="input-field pl-12 h-14 text-sm font-bold bg-slate-50"
                    />
                  </div>
                  <button 
                    onClick={() => setShowScanner(true)}
                    className="p-4 bg-slate-900 text-white rounded-2xl hover:bg-slate-800 transition-colors shadow-lg shadow-slate-900/10"
                  >
                    <Camera className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {isReadOnlyScanner(user?.role) && (
                <p className="text-[10px] text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2 font-bold">
                  Read-only role: VERIFY and AUDIT scans only. State changes are blocked server-side.
                </p>
              )}

              <button 
                onClick={handleManualSubmit}
                disabled={isProcessing || !qrInput || recordScan.isPending}
                className="btn-primary w-full h-14 shadow-xl shadow-brand-primary/20 flex items-center justify-center gap-3 text-sm font-black uppercase tracking-widest disabled:opacity-50"
              >
                {isProcessing || recordScan.isPending ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <><Smartphone className="w-5 h-5" /> Execute Tracking</>
                )}
              </button>
            </div>
          </div>

          {/* Camera Overlay */}
          <AnimatePresence>
            {showScanner && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-slate-900/90 backdrop-blur-xl z-[100] flex items-center justify-center p-6"
              >
                <div className="bg-white rounded-[2.5rem] p-8 w-full max-w-lg relative overflow-hidden shadow-2xl">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="text-xl font-black text-slate-900 tracking-tight">Camera Feed</h3>
                    <button 
                      onClick={() => setShowScanner(false)}
                      className="p-2 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
                    >
                      <AlertTriangle className="w-5 h-5" />
                    </button>
                  </div>
                  <div id="reader" className="w-full overflow-hidden rounded-2xl border-2 border-slate-100" />
                  <p className="text-center text-slate-400 text-xs mt-6 font-bold uppercase tracking-widest">
                    Center the QR code in the frame
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right Column: Visualizer */}
        <div className="lg:col-span-8">
          <AnimatePresence mode="wait">
            {viewMode === 'MAP' ? (
              <motion.div 
                key="map-view"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.02 }}
                className="h-[600px] rounded-[2.5rem] overflow-hidden shadow-2xl border border-white relative"
              >
                <MapContainer 
                  center={mapCenter} 
                  zoom={13} 
                  style={{ height: '100%', width: '100%' }}
                  className="z-10"
                >
                  <ChangeView center={mapCenter} />
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  />
                  
                  {/* Current Position Marker */}
                  <Marker position={mapCenter}>
                    <Popup>
                      <div className="p-2">
                        <p className="font-black text-slate-900 text-xs uppercase tracking-widest">Current Location</p>
                        <p className="text-slate-500 text-[10px]">Real-time scan coordinate</p>
                      </div>
                    </Popup>
                  </Marker>

                  {/* History Trace */}
                  {polylineCoords.length > 1 && (
                    <>
                      <Polyline positions={polylineCoords} color="#4f46e5" weight={4} opacity={0.6} dashArray="10, 10" />
                      {polylineCoords.map((coord, idx) => (
                        <Marker key={idx} position={coord}>
                           <Popup>Movement #{idx + 1}</Popup>
                        </Marker>
                      ))}
                    </>
                  )}
                </MapContainer>

                {/* Floating Map Legend */}
                <div className="absolute bottom-8 left-8 z-[20] bg-slate-900/90 backdrop-blur-md p-4 rounded-2xl border border-white/10 text-white shadow-2xl">
                   <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-brand-primary rounded-xl flex items-center justify-center">
                        <MapPin className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Active Tracking</p>
                        <p className="text-xs font-bold">{mapCenter[0].toFixed(4)}, {mapCenter[1].toFixed(4)}</p>
                      </div>
                   </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="details-view"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {!scanResult ? (
                  <div className="h-[600px] border-4 border-dashed border-slate-100 rounded-[2.5rem] flex flex-col items-center justify-center text-center p-12 bg-white/50">
                    <div className="w-24 h-24 bg-slate-100 rounded-3xl flex items-center justify-center mb-6 shadow-inner">
                      <Search className="w-10 h-10 text-slate-300" />
                    </div>
                    <h3 className="text-2xl font-black text-slate-300 uppercase tracking-widest">Ready for Ingestion</h3>
                    <p className="text-slate-400 max-w-sm mt-4 font-medium">
                      Start a scan or enter an ID to view live telemetry and geospatial movement patterns.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Item Card */}
                    <div className="enterprise-card p-8 bg-white border-none shadow-2xl relative overflow-hidden group">
                       <div className="absolute top-0 right-0 p-8">
                          <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center -mr-10 -mt-10 group-hover:scale-110 transition-transform">
                             <CheckCircle2 className="w-8 h-8 text-emerald-500/20" />
                          </div>
                       </div>

                       <div className="flex items-center gap-4 mb-8">
                          <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center shadow-lg shadow-slate-900/20">
                             <Package className="text-white w-8 h-8" />
                          </div>
                          <div>
                             <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-[10px] font-black uppercase rounded-lg mb-1 inline-block tracking-widest">
                               {scanResult.item.type.replace('_', ' ')}
                             </span>
                             <h3 className="text-2xl font-black text-slate-900 tracking-tight">Unit ID #{scanResult.item.id}</h3>
                          </div>
                       </div>

                       <div className="space-y-6">
                          <div className="p-4 bg-slate-50 rounded-2xl flex items-center justify-between border border-slate-100">
                             <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">System Status</span>
                             <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full flex items-center gap-1.5">
                                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                                {scanResult.item.status.replace('_', ' ')}
                             </span>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                             <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Latitude</p>
                                <p className="text-sm font-bold text-slate-900">{mapCenter[0].toFixed(6)}</p>
                             </div>
                             <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Longitude</p>
                                <p className="text-sm font-bold text-slate-900">{mapCenter[1].toFixed(6)}</p>
                             </div>
                          </div>
                       </div>
                    </div>

                    {/* AI & History */}
                    <div className="space-y-6">
                       {/* AI Anomalies */}
                       {scanResult.anomalies && scanResult.anomalies.length > 0 && (
                         <div className="enterprise-card p-6 bg-rose-600 text-white border-none shadow-xl shadow-rose-200">
                            <h4 className="text-[10px] font-black uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                               <AlertTriangle className="w-4 h-4" /> Security Alert
                            </h4>
                            <div className="space-y-4">
                               {scanResult.anomalies.map((a: any, i: number) => (
                                 <div key={i} className="bg-white/10 p-4 rounded-xl border border-white/20">
                                    <p className="text-xs font-bold leading-relaxed">{a.message}</p>
                                 </div>
                               ))}
                            </div>
                         </div>
                       )}

                       <div className="enterprise-card p-6 bg-white border border-slate-100 shadow-xl md:col-span-2">
                          <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-4 flex items-center gap-2">
                             <History className="w-4 h-4" /> Tracking Timeline
                          </h4>
                          <TrackingTimeline
                            events={timelineHistory || scanResult.history || []}
                            loading={historyLoading}
                          />
                       </div>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default Tracking;
