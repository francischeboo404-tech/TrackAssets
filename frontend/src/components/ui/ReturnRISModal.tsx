import React, { useEffect, useState, useRef, useCallback } from "react";
import { Modal } from "./Modal";
import {
  getRequisition,
  getRequisitionsPage,
  returnRequisition,
} from "../../services/requisition";
import type { ReturnItem } from "../../services/requisition";
import { useToast } from "../../context/ToastContext";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onReturned?: (risId: number) => void;
}

type RisItem = {
  id: number;
  item_id: number;
  sku?: string | null;
  name?: string | null;
  quantity_requested: number;
  quantity_issued: number;
  unit_cost?: number | null;
  return_qty?: number;
};

export const ReturnRISModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onReturned,
}) => {
  const [risIdInput, setRisIdInput] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [risNumber, setRisNumber] = useState<string | null>(null);
  const [items, setItems] = useState<RisItem[]>([]);
  const [recentRis, setRecentRis] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [debouncedTerm, setDebouncedTerm] = useState<string>("");
  const [offset, setOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (!isOpen) {
      setRisIdInput("");
      setRisNumber(null);
      setItems([]);
      setLoading(false);
      setSubmitting(false);
      setRecentRis([]);
      setSearchTerm("");
    }
    if (isOpen) {
      // preload recent RIS (first page)
      (async () => {
        try {
          const page = await getRequisitionsPage(undefined, 8, 0);
          const list = page.items || [];
          setRecentRis(list || []);
          setOffset(page.next_offset || list.length);
          setHasMore(Boolean(page.has_more));
        } catch (e) {
          // ignore preload errors
        }
      })();
    }
  }, [isOpen]);

  const loadRis = async (idParam?: number) => {
    const id = typeof idParam === "number" ? idParam : parseInt(risIdInput, 10);
    if (Number.isNaN(id)) {
      addToast("error", "Invalid ID", "Enter a numeric RIS id");
      return;
    }
    setLoading(true);
    try {
      const data = await getRequisition(id);
      setRisNumber(data.ris_number || null);
      const mapped: RisItem[] = (data.items || []).map((it: any) => ({
        ...it,
        return_qty: 0,
      }));
      setItems(mapped);
    } catch (err: any) {
      addToast(
        "error",
        "Load failed",
        err.response?.data?.message || err.message || "Failed to load RIS",
      );
      setRisNumber(null);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const searchRis = useCallback(
    async (q?: string, startOffset = 0) => {
      try {
        const page = await getRequisitionsPage(q, 20, startOffset);
        const list = page.items || [];
        if (startOffset === 0) {
          setRecentRis(list || []);
        } else {
          setRecentRis((prev) => [...prev, ...(list || [])]);
        }
        setOffset(page.next_offset || startOffset + list.length);
        setHasMore(Boolean(page.has_more));
      } catch (err: any) {
        addToast(
          "error",
          "Search failed",
          err.response?.data?.message || err.message || "Failed to search RIS",
        );
      }
    },
    [addToast],
  );

  // debounce search input
  useEffect(() => {
    const t = setTimeout(() => setDebouncedTerm(searchTerm), 300);
    return () => clearTimeout(t);
  }, [searchTerm]);

  // trigger search when debouncedTerm changes
  useEffect(() => {
    if (debouncedTerm === "") return;
    searchRis(debouncedTerm, 0);
  }, [debouncedTerm]);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      await searchRis(debouncedTerm || searchTerm || undefined, offset);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, debouncedTerm, searchTerm, offset, searchRis]);

  const listRef = useRef<HTMLDivElement | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // IntersectionObserver for efficient infinite-scroll
  useEffect(() => {
    const container = listRef.current;
    const sentinel = sentinelRef.current;
    if (!container || !sentinel) return;
    const options: IntersectionObserverInit = {
      root: container,
      rootMargin: "0px 0px 80px 0px",
      threshold: 0,
    };
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && hasMore && !loadingMore) {
          loadMore();
        }
      });
    }, options);
    obs.observe(sentinel);
    return () => obs.disconnect();
  }, [hasMore, loadingMore, loadMore]);

  const updateReturnQty = (idx: number, val: number) => {
    setItems((prev) => {
      const copy = [...prev];
      copy[idx].return_qty = Math.max(
        0,
        Math.min(copy[idx].quantity_issued || 0, val),
      );
      return copy;
    });
  };

  const submitReturn = async () => {
    const id = parseInt(risIdInput, 10);
    if (Number.isNaN(id)) {
      addToast("error", "Invalid ID", "Enter a numeric RIS id");
      return;
    }
    const payload: ReturnItem[] = items
      .filter((i) => (i.return_qty || 0) > 0)
      .map((i) => ({ item_id: i.item_id, quantity: i.return_qty || 0 }));
    if (payload.length === 0) {
      addToast("info", "Nothing selected", "Select items to return");
      return;
    }
    setSubmitting(true);
    try {
      const res = await returnRequisition(id, payload);
      addToast("success", "Returned", `RIS ${res.ris_id} returned`);
      onReturned && onReturned(id);
      onClose();
    } catch (err: any) {
      addToast(
        "error",
        "Return failed",
        err.response?.data?.message || err.message || "Return failed",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={risNumber ? `Return - ${risNumber}` : "Return Requisition"}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={submitting}>
            Close
          </button>
          <button
            className="btn-primary"
            onClick={submitReturn}
            disabled={submitting || items.length === 0}
          >
            {submitting ? "Returning..." : "Return Selected"}
          </button>
        </>
      }
      size="lg"
    >
      <div className="space-y-4">
        {!risNumber && (
          <div className="space-y-3">
            <div className="flex gap-2 items-center">
              <input
                className="input"
                placeholder="Enter RIS ID"
                value={risIdInput}
                onChange={(e) => setRisIdInput(e.target.value)}
              />
              <button
                className="btn-primary"
                onClick={() => loadRis()}
                disabled={loading}
              >
                {loading ? "Loading..." : "Load RIS"}
              </button>
            </div>

            <div className="flex gap-2 items-center">
              <input
                className="input flex-1"
                placeholder="Search RIS number"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") searchRis(searchTerm);
                }}
              />
              <button className="btn" onClick={() => searchRis(searchTerm)}>
                Search
              </button>
            </div>

            {recentRis.length > 0 && (
              <div>
                <div
                  ref={listRef}
                  className="max-h-40 overflow-y-auto border rounded-md p-2"
                >
                  {recentRis.map((r) => (
                    <div
                      key={r.id}
                      className="flex items-center justify-between p-2 hover:bg-slate-50 rounded"
                    >
                      <div>
                        <div className="font-medium">{r.ris_number}</div>
                        <div className="text-sm text-slate-500">{r.status}</div>
                      </div>
                      <div>
                        <button
                          className="btn"
                          onClick={async () => {
                            setRisIdInput(String(r.id));
                            await loadRis(r.id);
                          }}
                        >
                          Load
                        </button>
                      </div>
                    </div>
                  ))}
                  <div ref={sentinelRef} style={{ height: 1, width: "100%" }} />
                </div>
                {loadingMore && (
                  <div className="flex justify-center mt-2 text-sm text-slate-500">
                    Loading...
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {risNumber && (
          <div className="space-y-2">
            <div className="text-sm text-slate-500">RIS: {risNumber}</div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-sm text-slate-500 border-b">
                    <th className="py-2">Item</th>
                    <th className="py-2">SKU</th>
                    <th className="py-2">Requested</th>
                    <th className="py-2">Issued</th>
                    <th className="py-2">Return Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, idx) => (
                    <tr key={it.id} className="border-b border-slate-100">
                      <td className="py-2">{it.name || "—"}</td>
                      <td className="py-2">{it.sku || "—"}</td>
                      <td className="py-2">{it.quantity_requested}</td>
                      <td className="py-2">{it.quantity_issued}</td>
                      <td className="py-2">
                        <input
                          type="number"
                          min={0}
                          max={it.quantity_issued}
                          value={it.return_qty ?? 0}
                          onChange={(e) =>
                            updateReturnQty(
                              idx,
                              parseInt(e.target.value || "0", 10),
                            )
                          }
                          className="input w-28"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default ReturnRISModal;
