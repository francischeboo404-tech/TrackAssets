import React, { useState, useRef, useCallback } from "react";
import * as XLSX from "xlsx";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Download,
  X,
} from "lucide-react";
import { Modal } from "./Modal";
import { useBulkImportAssets } from "../../hooks/useAssets";
import { useBulkImportInventory } from "../../hooks/useInventory";
import { cn } from "../../lib/utils";

type Entity = "assets" | "inventory";

interface BulkImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  entity: Entity;
}

type Step = "upload" | "preview" | "results";

interface RowResult {
  row: number;
  status: string;
  asset_id?: number;
  asset_code?: string;
  item_id?: number;
  sku?: string;
  errors?: Record<string, unknown>;
}

const ASSET_COLUMNS = [
  { key: "name", label: "Name", required: true },
  { key: "type", label: "Type", required: true },
  { key: "department_id", label: "Department ID", required: true },
  { key: "purchase_date", label: "Purchase Date (YYYY-MM-DD)", required: true },
  { key: "purchase_value", label: "Purchase Value", required: true },
  { key: "useful_life", label: "Useful Life (years)", required: true },
  { key: "asset_code", label: "Asset Code", required: false },
  { key: "serial_number", label: "Serial Number", required: false },
  { key: "location", label: "Location", required: false },
  { key: "warehouse_id", label: "Warehouse ID", required: false },
];

const INVENTORY_COLUMNS = [
  { key: "name", label: "Name", required: true },
  { key: "sku", label: "SKU", required: false },
  { key: "description", label: "Description", required: false },
  { key: "unit", label: "Unit", required: false },
  { key: "unit_price", label: "Unit Price", required: true },
  { key: "reorder_level", label: "Reorder Level", required: false },
  { key: "category_id", label: "Category ID", required: false },
  { key: "item_type", label: "Item Type", required: false },
  { key: "status", label: "Status", required: false },
  {
    key: "preferred_supplier_id",
    label: "Preferred Supplier ID",
    required: false,
  },
  {
    key: "supplier_item_reference",
    label: "Supplier Item Reference",
    required: false,
  },
  { key: "purchase_cost", label: "Purchase Cost", required: false },
  { key: "last_purchase_cost", label: "Last Purchase Cost", required: false },
  { key: "tax_category", label: "Tax Category", required: false },
  { key: "lead_time_days", label: "Lead Time Days", required: false },
  { key: "min_stock_level", label: "Min Stock Level", required: false },
  { key: "max_stock_level", label: "Max Stock Level", required: false },
  { key: "safety_stock", label: "Safety Stock", required: false },
  { key: "opening_stock", label: "Opening Stock", required: false },
  { key: "batch_tracking", label: "Batch Tracking", required: false },
  { key: "serial_tracking", label: "Serial Tracking", required: false },
  { key: "expiry_tracking", label: "Expiry Tracking", required: false },
];

function downloadTemplate(entity: Entity) {
  const cols = entity === "assets" ? ASSET_COLUMNS : INVENTORY_COLUMNS;
  const ws = XLSX.utils.aoa_to_sheet([cols.map((c) => c.key)]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(
    wb,
    ws,
    entity === "assets" ? "Assets" : "Inventory",
  );
  XLSX.writeFile(wb, `${entity}_import_template.xlsx`);
}

function coerceRow(
  raw: Record<string, unknown>,
  entity: Entity,
): Record<string, unknown> {
  const row = { ...raw };
  if (entity === "assets") {
    if (row.department_id !== undefined)
      row.department_id = Number(row.department_id);
    if (row.purchase_value !== undefined)
      row.purchase_value = Number(row.purchase_value);
    if (row.useful_life !== undefined)
      row.useful_life = Number(row.useful_life);
    if (row.warehouse_id !== undefined && row.warehouse_id !== "")
      row.warehouse_id = Number(row.warehouse_id);
    // Excel may parse dates as serial numbers — convert to ISO string
    if (typeof row.purchase_date === "number") {
      const date = XLSX.SSF.parse_date_code(row.purchase_date as number);
      row.purchase_date = `${date.y}-${String(date.m).padStart(2, "0")}-${String(date.d).padStart(2, "0")}`;
    }
    // Strip empty optional strings
    ["asset_code", "serial_number", "location"].forEach((k) => {
      if (row[k] === "" || row[k] === null) delete row[k];
    });
    if (!row.warehouse_id) delete row.warehouse_id;
  } else {
    if (row.unit_price !== undefined) row.unit_price = Number(row.unit_price);
    if (row.quantity !== undefined && row.quantity !== "")
      row.quantity = Number(row.quantity);
    if (row.reorder_level !== undefined && row.reorder_level !== "")
      row.reorder_level = Number(row.reorder_level);
    if (row.category_id !== undefined && row.category_id !== "")
      row.category_id = Number(row.category_id);
    if (
      row.preferred_supplier_id !== undefined &&
      row.preferred_supplier_id !== ""
    )
      row.preferred_supplier_id = Number(row.preferred_supplier_id);
    if (row.purchase_cost !== undefined && row.purchase_cost !== "")
      row.purchase_cost = Number(row.purchase_cost);
    if (row.last_purchase_cost !== undefined && row.last_purchase_cost !== "")
      row.last_purchase_cost = Number(row.last_purchase_cost);
    if (row.lead_time_days !== undefined && row.lead_time_days !== "")
      row.lead_time_days = Number(row.lead_time_days);
    if (row.min_stock_level !== undefined && row.min_stock_level !== "")
      row.min_stock_level = Number(row.min_stock_level);
    if (row.max_stock_level !== undefined && row.max_stock_level !== "")
      row.max_stock_level = Number(row.max_stock_level);
    if (row.safety_stock !== undefined && row.safety_stock !== "")
      row.safety_stock = Number(row.safety_stock);
    if (row.opening_stock !== undefined && row.opening_stock !== "")
      row.opening_stock = Number(row.opening_stock);
    const booleanFields = [
      "batch_tracking",
      "serial_tracking",
      "expiry_tracking",
    ];
    booleanFields.forEach((field) => {
      if (row[field] !== undefined) {
        const value = String(row[field]).trim().toLowerCase();
        row[field] = ["1", "true", "yes", "y"].includes(value);
      }
    });
    [
      "sku",
      "description",
      "unit",
      "item_type",
      "status",
      "supplier_item_reference",
      "tax_category",
    ].forEach((k) => {
      if (row[k] === "" || row[k] === null) delete row[k];
    });
    if (!row.quantity) delete row.quantity;
    if (!row.reorder_level) delete row.reorder_level;
    if (!row.category_id) delete row.category_id;
    if (!row.preferred_supplier_id) delete row.preferred_supplier_id;
    if (!row.purchase_cost) delete row.purchase_cost;
    if (!row.last_purchase_cost) delete row.last_purchase_cost;
    if (!row.lead_time_days) delete row.lead_time_days;
    if (!row.min_stock_level) delete row.min_stock_level;
    if (!row.max_stock_level) delete row.max_stock_level;
    if (!row.safety_stock) delete row.safety_stock;
    if (!row.opening_stock) delete row.opening_stock;
  }
  return row;
}

export const BulkImportModal: React.FC<BulkImportModalProps> = ({
  isOpen,
  onClose,
  entity,
}) => {
  const [step, setStep] = useState<Step>("upload");
  const [parsedRows, setParsedRows] = useState<Record<string, unknown>[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [importResults, setImportResults] = useState<{
    succeeded: number;
    failed: number;
    results: RowResult[];
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const bulkImportAssets = useBulkImportAssets();
  const bulkImportInventory = useBulkImportInventory();
  const mutation = entity === "assets" ? bulkImportAssets : bulkImportInventory;

  const columns = entity === "assets" ? ASSET_COLUMNS : INVENTORY_COLUMNS;
  const previewCols = columns.map((c) => c.key);

  const handleClose = () => {
    setStep("upload");
    setParsedRows([]);
    setParseError(null);
    setImportResults(null);
    onClose();
  };

  const parseFile = useCallback(
    (file: File) => {
      setParseError(null);
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target!.result as ArrayBuffer);
          const wb = XLSX.read(data, { type: "array", cellDates: false });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const raw = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws, {
            defval: "",
          });
          if (raw.length === 0) {
            setParseError("The file is empty or has no data rows.");
            return;
          }
          if (raw.length > 500) {
            setParseError(
              "File exceeds the 500-row limit. Split the file and import in batches.",
            );
            return;
          }
          const coerced = raw.map((r) => coerceRow(r, entity));
          setParsedRows(coerced);
          setStep("preview");
        } catch {
          setParseError(
            "Could not parse the file. Make sure it is a valid CSV or Excel (.xlsx) file.",
          );
        }
      };
      reader.readAsArrayBuffer(file);
    },
    [entity],
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) parseFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) parseFile(file);
  };

  const handleImport = async () => {
    try {
      const result = await mutation.mutateAsync(parsedRows);
      setImportResults(result);
      setStep("results");
    } catch (err: any) {
      setParseError(
        err?.response?.data?.message || "Import failed. Please try again.",
      );
    }
  };

  const failedRows =
    importResults?.results.filter((r) => r.status === "error") ?? [];
  const title =
    entity === "assets" ? "Bulk Import Assets" : "Bulk Import Inventory";

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={title}
      size="xl"
      footer={
        step === "preview" ? (
          <>
            <button onClick={() => setStep("upload")} className="btn-secondary">
              Back
            </button>
            <button
              onClick={handleImport}
              disabled={mutation.isPending}
              className="btn-primary"
            >
              {mutation.isPending
                ? "Importing..."
                : `Import ${parsedRows.length} rows`}
            </button>
          </>
        ) : step === "results" ? (
          <button onClick={handleClose} className="btn-primary">
            Done
          </button>
        ) : undefined
      }
    >
      {/* ── STEP 1: UPLOAD ── */}
      {step === "upload" && (
        <div className="space-y-6">
          <div className="flex items-start justify-between gap-4">
            <p className="text-sm text-slate-500 leading-relaxed">
              Upload a <strong>.csv</strong> or <strong>.xlsx</strong> file with
              your {entity} data. Column headers must match the template
              exactly. Required fields are marked{" "}
              <span className="text-rose-500 font-bold">*</span>.
            </p>
            <button
              type="button"
              onClick={() => downloadTemplate(entity)}
              className="shrink-0 flex items-center gap-2 text-xs font-bold text-brand-primary hover:underline"
            >
              <Download className="w-3.5 h-3.5" /> Download Template
            </button>
          </div>

          {/* Column reference */}
          <div className="bg-slate-50 rounded-xl p-4 space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
              Required columns
            </p>
            <div className="flex flex-wrap gap-2">
              {columns.map((c) => (
                <span
                  key={c.key}
                  className={cn(
                    "text-xs font-mono px-2 py-0.5 rounded-md border",
                    c.required
                      ? "bg-rose-50 border-rose-200 text-rose-700"
                      : "bg-slate-100 border-slate-200 text-slate-500",
                  )}
                >
                  {c.key}
                  {c.required && (
                    <span className="text-rose-500 ml-0.5">*</span>
                  )}
                </span>
              ))}
            </div>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "border-2 border-dashed rounded-2xl p-12 flex flex-col items-center gap-4 cursor-pointer transition-all duration-200",
              isDragging
                ? "border-brand-primary bg-brand-primary/5"
                : "border-slate-200 hover:border-brand-primary/50 hover:bg-slate-50",
            )}
          >
            <div className="p-4 bg-slate-100 rounded-2xl">
              <FileSpreadsheet className="w-8 h-8 text-slate-400" />
            </div>
            <div className="text-center">
              <p className="font-bold text-slate-700">Drop your file here</p>
              <p className="text-sm text-slate-400 mt-1">
                or click to browse — .csv or .xlsx, max 500 rows
              </p>
            </div>
            <div className="flex items-center gap-2 text-brand-primary font-bold text-sm">
              <Upload className="w-4 h-4" /> Choose File
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {parseError && (
            <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{parseError}</span>
            </div>
          )}
        </div>
      )}

      {/* ── STEP 2: PREVIEW ── */}
      {step === "preview" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">
              <strong className="text-slate-800">
                {parsedRows.length} rows
              </strong>{" "}
              parsed from your file. Review below then click{" "}
              <strong>Import</strong>.
            </p>
            <button
              type="button"
              onClick={() => {
                setParsedRows([]);
                setStep("upload");
              }}
              className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1"
            >
              <X className="w-3 h-3" /> Change file
            </button>
          </div>

          {parseError && (
            <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{parseError}</span>
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-3 py-2.5 text-left font-bold text-slate-400 uppercase tracking-wider w-10">
                    #
                  </th>
                  {previewCols.map((col) => (
                    <th
                      key={col}
                      className="px-3 py-2.5 text-left font-bold text-slate-600 uppercase tracking-wider whitespace-nowrap"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {parsedRows.slice(0, 20).map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-3 py-2 text-slate-400 font-mono">
                      {i + 1}
                    </td>
                    {previewCols.map((col) => (
                      <td
                        key={col}
                        className="px-3 py-2 text-slate-700 font-medium whitespace-nowrap max-w-[160px] truncate"
                      >
                        {String(row[col] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {parsedRows.length > 20 && (
              <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 text-xs text-slate-400 font-medium">
                Showing 20 of {parsedRows.length} rows — all rows will be
                imported.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── STEP 3: RESULTS ── */}
      {step === "results" && importResults && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
              <CheckCircle className="w-6 h-6 text-emerald-600 shrink-0" />
              <div>
                <p className="text-2xl font-black text-emerald-700">
                  {importResults.succeeded}
                </p>
                <p className="text-xs font-bold text-emerald-600 uppercase tracking-wider">
                  Imported
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-rose-50 border border-rose-200 rounded-xl">
              <XCircle className="w-6 h-6 text-rose-600 shrink-0" />
              <div>
                <p className="text-2xl font-black text-rose-700">
                  {importResults.failed}
                </p>
                <p className="text-xs font-bold text-rose-600 uppercase tracking-wider">
                  Failed
                </p>
              </div>
            </div>
          </div>

          {/* Failed row details */}
          {failedRows.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                Failed rows
              </p>
              <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                {failedRows.map((r) => (
                  <div
                    key={r.row}
                    className="flex items-start gap-3 p-3 bg-rose-50 border border-rose-200 rounded-xl text-sm"
                  >
                    <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="font-bold text-rose-700">Row {r.row + 1}</p>
                      <p className="text-rose-600 text-xs mt-0.5 break-words">
                        {Object.entries(r.errors ?? {})
                          .map(
                            ([field, msg]) =>
                              `${field}: ${Array.isArray(msg) ? msg.join(", ") : String(msg)}`,
                          )
                          .join(" · ")}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {importResults.failed === 0 && (
            <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-sm font-medium">
              <CheckCircle className="w-5 h-5 shrink-0" />
              All rows imported successfully.
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};
