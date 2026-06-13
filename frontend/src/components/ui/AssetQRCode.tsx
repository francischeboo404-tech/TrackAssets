import { QRCodeSVG } from 'qrcode.react';
import { Download, Printer, Barcode, RefreshCw } from 'lucide-react';
import { useRef } from 'react';
import { useEntityQr } from '../../hooks/useTracking';

interface AssetQRCodeProps {
  entityType: 'asset' | 'inventory';
  entityId: number;
  organisationId: number;
  label?: string;
  code?: string;
}

export const AssetQRCode = ({
  entityType,
  entityId,
  label,
  code,
}: AssetQRCodeProps) => {
  const qrRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, refetch, isFetching } = useEntityQr(
    entityType,
    entityId,
  );

  const qrValue = data?.signed_token || data?.scan_url || '';

  const downloadQR = () => {
    const svg = qrRef.current?.querySelector('svg');
    if (!svg) return;

    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height + 40;
      if (ctx) {
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        ctx.fillStyle = 'black';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(
          code || data?.entity_code || `ID: ${entityId}`,
          canvas.width / 2,
          img.height + 20,
        );
      }
      const pngFile = canvas.toDataURL('image/png');
      const downloadLink = document.createElement('a');
      downloadLink.download = `${entityType}-${code || entityId}.png`;
      downloadLink.href = pngFile;
      downloadLink.click();
    };

    img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
  };

  return (
    <div className="flex flex-col items-center gap-4 p-4 bg-white rounded-2xl border border-slate-100 shadow-sm">
      <div className="flex items-center gap-2 w-full justify-between">
        <div className="flex items-center gap-2 text-slate-500">
          <Barcode className="w-4 h-4" />
          <span className="text-[10px] font-bold uppercase tracking-widest">
            Signed QR
          </span>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"
          title="Refresh QR"
        >
          <RefreshCw
            className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`}
          />
        </button>
      </div>

      <div ref={qrRef} className="p-3 bg-white rounded-xl ring-1 ring-slate-100 min-h-[176px] flex items-center justify-center">
        {isLoading || !qrValue ? (
          <div className="w-40 h-40 bg-slate-50 animate-pulse rounded-lg" />
        ) : (
          <QRCodeSVG value={qrValue} size={160} level="H" includeMargin={false} />
        )}
      </div>

      <div className="text-center">
        <p className="text-xs font-bold text-slate-900 uppercase tracking-tighter">
          {label || 'Trackable Item'}
        </p>
        <p className="text-[10px] font-mono text-slate-400 mt-0.5">
          {code || data?.entity_code || `ID-${entityId}`}
        </p>
        <p className="text-[9px] text-emerald-600 font-bold mt-2 uppercase tracking-wider">
          HMAC-signed · server verified
        </p>
      </div>

      <div className="flex gap-2 w-full mt-2">
        <button
          type="button"
          onClick={downloadQR}
          disabled={!qrValue}
          className="flex-1 flex items-center justify-center gap-2 py-2 px-3 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-lg text-[10px] font-bold transition-colors disabled:opacity-50"
        >
          <Download className="w-3.5 h-3.5" /> Download
        </button>
        <button
          type="button"
          className="flex-1 flex items-center justify-center gap-2 py-2 px-3 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-lg text-[10px] font-bold transition-colors"
          onClick={() => window.print()}
        >
          <Printer className="w-3.5 h-3.5" /> Print
        </button>
      </div>
    </div>
  );
};
