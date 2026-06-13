import { useEffect, useRef, useState } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';
import { Modal } from './Modal';
import { useToast } from '../../context/ToastContext';
import { useRecordScan } from '../../hooks/useTracking';
import { canPerformScanAction } from '../../lib/permissions';
import { useAuth } from '../../context/AuthContext';
import { Loader2, Camera, CheckCircle } from 'lucide-react';

interface LogScanModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LogScanModal = ({ isOpen, onClose }: LogScanModalProps) => {
  const [scanning, setScanning] = useState(true);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();
  const { user } = useAuth();
  const recordScan = useRecordScan();
  const scannerRef = useRef<Html5QrcodeScanner | null>(null);

  useEffect(() => {
    if (isOpen && scanning) {
      scannerRef.current = new Html5QrcodeScanner(
        "qr-reader", 
        { fps: 10, qrbox: { width: 250, height: 250 } },
        false
      );
      
      scannerRef.current.render(async (decodedText) => {
        setScanning(false);
        await processScan(decodedText);
      }, () => {
        // Ignore continuous scan noise
      });
    }

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch(err => console.error("Failed to clear scanner", err));
      }
    };
  }, [isOpen, scanning]);

  const processScan = async (decodedText: string) => {
    setLoading(true);
    try {
      let qrData = decodedText;
      try {
        const parsed = JSON.parse(decodedText);
        qrData = parsed.qr_code_data || parsed.sku || parsed.asset_code || decodedText;
      } catch {
        // Plain SKU or asset code strings are valid scan payloads
      }

      const action = canPerformScanAction(user?.role, 'CHECK_IN')
        ? 'CHECK_IN'
        : 'VERIFY';

      const response = await recordScan.mutateAsync({
        qr_data: qrData,
        action_type: action,
        notes: 'Global scanner',
      });
      
      setResult(response);
      addToast('success', 'Scan Recorded', response?.message || 'Lifecycle event recorded.');
    } catch (err: any) {
      addToast('error', 'Scan Failed', err.response?.data?.message || 'Server error recording scan.');
      setScanning(true);
    } finally {
      setLoading(false);
    }
  };

  const resetScanner = () => {
    setResult(null);
    setScanning(true);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Physical Asset Scanner"
      size="md"
    >
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        {loading ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-brand-primary animate-spin" />
            <p className="font-bold text-slate-700">Verifying Asset Integrity...</p>
          </div>
        ) : result ? (
          <div className="text-center p-8 bg-emerald-50 rounded-3xl border border-emerald-100 flex flex-col items-center gap-4">
            <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center">
              <CheckCircle className="w-10 h-10" />
            </div>
            <div>
               <h3 className="text-lg font-bold text-slate-900">Scan Complete</h3>
               <p className="text-sm text-slate-600 mt-1">{result.message || 'The lifecycle event has been recorded.'}</p>
            </div>
            <button onClick={resetScanner} className="btn-primary mt-4 bg-emerald-600 border-none">Scan Another</button>
          </div>
        ) : (
          <div className="w-full flex flex-col items-center">
            <div id="qr-reader" className="w-full overflow-hidden rounded-2xl border-2 border-dashed border-slate-200" />
            <div className="mt-8 flex items-center gap-3 text-slate-400 bg-slate-50 px-6 py-3 rounded-full border border-slate-100">
               <Camera className="w-5 h-5" />
               <span className="text-xs font-bold uppercase tracking-widest">Position QR Code within the frame</span>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
