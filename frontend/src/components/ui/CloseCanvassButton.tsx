import React from 'react';
import { useCloseCanvassQuote } from '../../hooks/usePurchaseOrders';

export default function CloseCanvassButton({ poId, quoteId }: { poId: number; quoteId: number }) {
  const closeMutation = useCloseCanvassQuote();

  return (
    <button
      className="text-sm font-medium text-rose-600 hover:text-rose-700 bg-rose-50 px-2 py-1 rounded-lg"
      onClick={async () => {
        try {
          await closeMutation.mutateAsync({ po_id: poId, quote_id: quoteId });
          // Optionally: show toast from parent via context
        } catch (err) {
          // noop: parent modal will show errors via global handler
        }
      }}
    >
      Close
    </button>
  );
}
