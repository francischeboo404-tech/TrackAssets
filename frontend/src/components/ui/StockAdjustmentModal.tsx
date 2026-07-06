import React, { useState } from "react";
import {
  Package,
  Hash,
  FileText,
  ChevronUp,
  ChevronDown,
  Warehouse,
  AlertTriangle,
} from "lucide-react";
import { Modal } from "./Modal";
import {
  useUpdateStock,
  useItemWarehouseStock,
} from "../../hooks/useInventory";
import { useWarehouses } from "../../hooks/useWarehouses";

interface StockAdjustmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: any;
  initialType?: "IN" | "OUT";
}

export const StockAdjustmentModal: React.FC<StockAdjustmentModalProps> = ({
  isOpen,
  onClose,
  item,
  initialType = "IN",
}) => {
  const [quantity, setQuantity] = useState(1);
  const [type, setType] = useState<"IN" | "OUT">(initialType);
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [destinationWarehouseId, setDestinationWarehouseId] = useState<number | undefined>(undefined);
  const [isTransfer, setIsTransfer] = useState(false);
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const updateStock = useUpdateStock();
  // All active warehouses — for IN movements
  const { data: allWarehouses } = useWarehouses();
  // Per-item warehouse stock levels — for OUT movements
  const { data: itemWarehouseStock, isLoading: stockLoading } =
    useItemWarehouseStock(isOpen ? item?.id : undefined);

  // Reset state each time the modal opens
  React.useEffect(() => {
    if (isOpen) {
      setType(initialType);
      setWarehouseId(undefined);
      setDestinationWarehouseId(undefined);
      setIsTransfer(false);
      setQuantity(1);
      setReference("");
      setNotes("");
      setSubmitError(null);
    }
  }, [isOpen, initialType]);

  // When switching type, clear warehouse selection so user consciously chooses
  const handleTypeChange = (newType: "IN" | "OUT") => {
    setType(newType);
    setWarehouseId(undefined);
    setDestinationWarehouseId(undefined);
    setIsTransfer(false);
    setSubmitError(null);
  };

  // Warehouses to show depend on movement type:
  // OUT  → only warehouses that hold stock for this item (prevents "wrong warehouse" errors)
  // IN   → all active warehouses (receive stock anywhere)
  const warehouseOptions =
    type === "OUT"
      ? (itemWarehouseStock || []).filter((ws) => ws.quantity_available > 0)
      : allWarehouses || [];

  const receivingWarehouseOptions =
    type === "OUT"
      ? (allWarehouses || []).filter((wh: { id: number }) => wh.id !== warehouseId)
      : allWarehouses || [];

  // Selected warehouse stock info (for OUT — show available qty in helper text)
  const selectedWS =
    type === "OUT"
      ? itemWarehouseStock?.find((ws) => ws.warehouse_id === warehouseId)
      : null;

  const maxQuantity =
    type === "OUT" && selectedWS ? selectedWS.quantity_available : undefined;

  const handleAdjust = () => {
    setSubmitError(null);

    // Client-side guard: prevent dispatching more than available
    if (type === "OUT" && maxQuantity !== undefined && quantity > maxQuantity) {
      setSubmitError(
        `Cannot dispatch ${quantity} units — only ${maxQuantity} available in this warehouse.`,
      );
      return;
    }

    if (type === "OUT" && isTransfer && !destinationWarehouseId) {
      setSubmitError("Select a receiving warehouse to complete this transfer.");
      return;
    }

    if (type === "OUT" && warehouseId && destinationWarehouseId && warehouseId === destinationWarehouseId) {
      setSubmitError("The source and receiving warehouse must be different.");
      return;
    }

    updateStock.mutate(
      {
        id: item.id,
        quantity,
        type,
        reference,
        notes,
        warehouse_id: warehouseId,
        destination_warehouse_id: type === "OUT" && isTransfer ? destinationWarehouseId : undefined,
      },
      {
        onSuccess: () => {
          onClose();
          setQuantity(1);
          setWarehouseId(undefined);
          setDestinationWarehouseId(undefined);
          setIsTransfer(false);
          setReference("");
          setNotes("");
          setSubmitError(null);
        },
        onError: (err: any) => {
          const msg =
            err?.response?.data?.message ||
            err?.message ||
            "Stock update failed.";
          setSubmitError(msg);
        },
      },
    );
  };

  const isSubmitDisabled =
    updateStock.isPending ||
    !reference ||
    !warehouseId ||
    (type === "OUT" && stockLoading) ||
    (type === "OUT" && isTransfer && !destinationWarehouseId);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${type === "IN" ? "Restock" : "Dispatch / Remove Stock"}: ${item?.name}`}
      footer={
        <>
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 font-semibold hover:bg-slate-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleAdjust}
            disabled={isSubmitDisabled}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {updateStock.isPending ? "Processing..." : "Confirm Adjustment"}
          </button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Movement type toggle */}
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => handleTypeChange("IN")}
            className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${type === "IN" ? "border-indigo-600 bg-indigo-50 text-indigo-700" : "border-slate-100 bg-slate-50 text-slate-400 hover:border-slate-200"}`}
          >
            <ChevronUp className="w-6 h-6" />
            <span className="font-bold">Stock In</span>
          </button>
          <button
            onClick={() => handleTypeChange("OUT")}
            className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${type === "OUT" ? "border-rose-600 bg-rose-50 text-rose-700" : "border-slate-100 bg-slate-50 text-slate-400 hover:border-slate-200"}`}
          >
            <ChevronDown className="w-6 h-6" />
            <span className="font-bold">Stock Out</span>
          </button>
        </div>

        {/* Warehouse selector */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <Warehouse className="w-4 h-4 text-brand-primary" />
            {type === "OUT"
              ? "Dispatch From Warehouse (Required)"
              : "Receive Into Warehouse (Required)"}
          </label>

          {type === "OUT" && stockLoading && (
            <p className="text-xs text-slate-400 italic">
              Loading available stock locations…
            </p>
          )}

          {type === "OUT" && !stockLoading && warehouseOptions.length === 0 && (
            <div className="flex items-center gap-2 text-amber-600 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>
                No warehouse holds stock for this item. Please restock (Stock
                In) first.
              </span>
            </div>
          )}

          {(!stockLoading || type === "IN") && (
            <select
              value={warehouseId || ""}
              onChange={(e) =>
                setWarehouseId(
                  e.target.value ? Number(e.target.value) : undefined,
                )
              }
              className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none cursor-pointer"
              style={{ fontFamily: "Outfit" }}
              disabled={type === "OUT" && warehouseOptions.length === 0}
            >
              <option value="">Select a warehouse…</option>
              {type === "OUT"
                ? (
                    warehouseOptions as Array<{
                      warehouse_id: number;
                      warehouse_name: string;
                      quantity_available: number;
                    }>
                  ).map((ws) => (
                    <option key={ws.warehouse_id} value={ws.warehouse_id}>
                      {ws.warehouse_name} — {ws.quantity_available} available
                    </option>
                  ))
                : (
                    warehouseOptions as
                      | Array<{ id: number; name: string }>
                      | undefined
                  )?.map((wh) => (
                    <option key={wh.id} value={wh.id}>
                      {wh.name}
                    </option>
                  ))}
            </select>
          )}

          {/* Show available stock for selected OUT warehouse */}
          {type === "OUT" && selectedWS && (
            <p className="text-xs text-slate-500">
              Available in <strong>{selectedWS.warehouse_name}</strong>:{" "}
              <span
                className={`font-bold ${selectedWS.quantity_available < quantity ? "text-rose-600" : "text-emerald-600"}`}
              >
                {selectedWS.quantity_available} units
              </span>
            </p>
          )}
        </div>

        {type === "OUT" && (
          <div className="space-y-3">
            <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={isTransfer}
                onChange={(e) => {
                  setIsTransfer(e.target.checked);
                  if (!e.target.checked) {
                    setDestinationWarehouseId(undefined);
                  }
                }}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Transfer to another warehouse
            </label>

            {isTransfer && (
              <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
                  <Warehouse className="w-4 h-4 text-brand-primary" />
                  Receiving Warehouse (Required for transfer)
                </label>
                <select
                  value={destinationWarehouseId || ""}
                  onChange={(e) =>
                    setDestinationWarehouseId(
                      e.target.value ? Number(e.target.value) : undefined,
                    )
                  }
                  className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none cursor-pointer"
                  style={{ fontFamily: "Outfit" }}
                >
                  <option value="">Select receiving warehouse…</option>
                  {(receivingWarehouseOptions as Array<{ id: number; name: string }> | undefined)?.map((wh) => (
                    <option key={wh.id} value={wh.id}>
                      {wh.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}

        {/* Quantity input */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <Package className="w-4 h-4 text-brand-primary" /> Adjustment
            Quantity
          </label>
          <div className="flex items-center gap-4 bg-slate-100 p-2 rounded-xl border border-slate-200">
            <button
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              className="w-10 h-10 flex items-center justify-center bg-white rounded-lg shadow-sm font-bold text-slate-600 hover:text-indigo-600 transition-colors"
            >
              -
            </button>
            <input
              type="number"
              value={quantity}
              min={1}
              max={maxQuantity}
              onChange={(e) =>
                setQuantity(Math.max(1, parseInt(e.target.value) || 1))
              }
              className="flex-1 bg-transparent border-none text-center font-bold text-xl outline-none"
            />
            <button
              onClick={() =>
                setQuantity((q) =>
                  maxQuantity !== undefined
                    ? Math.min(maxQuantity, q + 1)
                    : q + 1,
                )
              }
              className="w-10 h-10 flex items-center justify-center bg-white rounded-lg shadow-sm font-bold text-slate-600 hover:text-indigo-600 transition-colors"
            >
              +
            </button>
          </div>
          {type === "OUT" &&
            maxQuantity !== undefined &&
            quantity > maxQuantity && (
              <p className="text-xs text-rose-500 font-semibold flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Exceeds available stock (
                {maxQuantity} units)
              </p>
            )}
        </div>

        {/* Reference */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <Hash className="w-4 h-4 text-brand-primary" /> Reference #
            (Required)
          </label>
          <input
            type="text"
            placeholder="e.g. PO-12345, DISPATCH-001, or Invoice ID"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none"
          />
        </div>

        {/* Notes */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-slate-700 flex items-center gap-2 italic">
            <FileText className="w-4 h-4 text-brand-primary" /> Transaction
            Notes
          </label>
          <textarea
            placeholder="Reason for adjustment, dispatch destination, etc."
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none resize-none"
          />
        </div>

        {/* Server-side error */}
        {submitError && (
          <div className="flex items-start gap-2 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3 text-sm text-rose-700">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{submitError}</span>
          </div>
        )}
      </div>
    </Modal>
  );
};
