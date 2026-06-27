import React, { useState, useRef } from "react";
import { Modal } from "./Modal";
import { useBatchUpdateStock } from "../../hooks/useInventory";
import { useToast } from "../../context/ToastContext";
import * as XLSX from "xlsx";
import { Download, UploadCloud, FileText, X } from "lucide-react";

interface BatchStockModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BatchStockModal: React.FC<BatchStockModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [parsedData, setParsedData] = useState<any[] | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const mutation = useBatchUpdateStock();
  const { addToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDownloadTemplate = () => {
    // Create an array of arrays. No confusing sample records, just a hint row.
    const ws = XLSX.utils.aoa_to_sheet([
      ["item_id", "type", "quantity", "warehouse_id", "reference", "notes"],
      ["", "IN", "", "", "", ""] // Hint row that user can overwrite or delete
    ]);
    
    // Set column widths for a professional look
    ws["!cols"] = [
      { wch: 15 }, // item_id
      { wch: 20 }, // type (IN/OUT)
      { wch: 15 }, // quantity
      { wch: 15 }, // warehouse_id
      { wch: 20 }, // reference
      { wch: 35 }, // notes
    ];
    
    // Add auto-filters to the header row
    ws["!autofilter"] = { ref: "A1:F1" };

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Template");
    
    // Add a read-only instructions sheet to make things extremely clear
    const wsInstructions = XLSX.utils.aoa_to_sheet([
      ["Batch Stock Upload Instructions"],
      [],
      ["Column", "Description", "Required?"],
      ["item_id", "The numeric ID of the inventory item (e.g., 1, 2, 3).", "Yes"],
      ["type", "The direction of the stock movement. Must be 'IN' or 'OUT'.", "Yes"],
      ["quantity", "The amount to increase or decrease the stock by.", "Yes"],
      ["warehouse_id", "The numeric ID of the specific warehouse.", "No"],
      ["reference", "Any external reference string (e.g., PO-1234, Dispatch-567).", "No"],
      ["notes", "Any additional context or notes.", "No"]
    ]);
    wsInstructions["!cols"] = [{ wch: 15 }, { wch: 60 }, { wch: 15 }];
    XLSX.utils.book_append_sheet(wb, wsInstructions, "Instructions");

    XLSX.writeFile(wb, "batch_stock_template.xlsx");
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setParseError(null);
    setParsedData(null);

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const bstr = evt.target?.result;
        const wb = XLSX.read(bstr, { type: "binary" });
        const wsname = wb.SheetNames[0];
        const ws = wb.Sheets[wsname];
        const data = XLSX.utils.sheet_to_json(ws);

        if (!Array.isArray(data) || data.length === 0) {
          throw new Error("Spreadsheet is empty or invalid.");
        }

        const cleanedData = data.map((row: any, i: number) => {
          if (!row.item_id || !row.type || row.quantity === undefined) {
            throw new Error(
              `Row ${i + 2}: Missing required fields (item_id, type, quantity)`
            );
          }
          return {
            item_id: Number(row.item_id),
            type: String(row.type).toUpperCase(),
            quantity: Number(row.quantity),
            warehouse_id: row.warehouse_id ? Number(row.warehouse_id) : undefined,
            reference: row.reference ? String(row.reference) : undefined,
            notes: row.notes ? String(row.notes) : undefined,
          };
        });

        setParsedData(cleanedData);
      } catch (e: any) {
        setParseError(e.message || "Failed to parse file.");
        setParsedData(null);
      }
    };
    reader.onerror = () => {
      setParseError("Failed to read file.");
    };
    reader.readAsBinaryString(file);
    
    // Reset file input so the same file can be selected again if needed
    if (fileInputRef.current) {
        fileInputRef.current.value = "";
    }
  };

  const handleClearFile = () => {
    setParsedData(null);
    setFileName(null);
    setParseError(null);
  };

  const handleSubmit = async () => {
    if (!parsedData || parsedData.length === 0) {
      setParseError("No valid data to submit.");
      return;
    }
    setParseError(null);

    try {
      await mutation.mutateAsync(parsedData);
      addToast(
        "success",
        "Batch Applied",
        `Applied ${parsedData.length} stock movements`
      );
      handleClearFile();
      onClose();
    } catch (err: any) {
      addToast(
        "error",
        "Batch Failed",
        err?.response?.data?.message || "Could not apply batch"
      );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        handleClearFile();
        onClose();
      }}
      title="Batch Stock Movements (Excel/CSV)"
      size="lg"
      footer={
        <>
          <button
            onClick={() => {
              handleClearFile();
              onClose();
            }}
            className="px-4 py-2 text-slate-600 font-semibold hover:bg-slate-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending || !parsedData}
            className="btn-primary ml-2 disabled:opacity-50"
          >
            {mutation.isPending ? "Applying…" : "Apply Batch"}
          </button>
        </>
      }
    >
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex items-start gap-3">
          <div className="bg-blue-100 text-blue-600 p-2 rounded-lg">
            <Download className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-blue-900 font-medium mb-1">
              Download Template
            </h4>
            <p className="text-blue-700 text-sm mb-3">
              Start by downloading our Excel template. It includes the correct
              columns: <strong>item_id</strong>, <strong>type</strong> (IN/OUT),{" "}
              <strong>quantity</strong>, warehouse_id, reference, and notes.
            </p>
            <button
              onClick={handleDownloadTemplate}
              className="px-3 py-1.5 bg-white border border-blue-200 text-blue-700 rounded-lg shadow-sm hover:bg-blue-50 transition-colors text-sm font-medium flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download Template.xlsx
            </button>
          </div>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-700">
            Upload Completed File
          </label>
          {!fileName ? (
            <div
              className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:bg-slate-50 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-3" />
              <p className="text-slate-600 font-medium">
                Click to browse for a file
              </p>
              <p className="text-slate-400 text-sm mt-1">
                Supports .xlsx, .xls, and .csv
              </p>
            </div>
          ) : (
            <div className="border border-slate-200 rounded-xl p-4 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="bg-white p-2 rounded-lg shadow-sm border border-slate-100 text-brand-600">
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <p className="font-medium text-slate-700">{fileName}</p>
                  {parsedData && (
                    <p className="text-sm text-emerald-600 font-medium">
                      ✓ {parsedData.length} valid rows found
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={handleClearFile}
                className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                title="Remove file"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}
          
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
            onChange={handleFileUpload}
          />
          
          {parseError && (
            <div className="bg-rose-50 border border-rose-100 text-rose-600 rounded-lg p-3 text-sm flex items-start gap-2">
              <X className="w-4 h-4 mt-0.5 shrink-0" />
              <p>{parseError}</p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default BatchStockModal;
