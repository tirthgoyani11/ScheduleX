import { useState, useRef, useCallback } from "react";
import {
  Upload, FileSpreadsheet, CheckCircle2, AlertCircle, Loader2, Info, X,
  Download,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { usePdfImport } from "@/hooks/usePdfImport";
import { apiClient } from "@/lib/api-client";

interface ImportLog {
  id: number;
  category: string;
  inserted: number;
  skipped: number;
  total: number;
  warnings: string[];
  timestamp: Date;
  status: "success" | "error";
  error?: string;
}

export default function PdfImportPage() {
  const { categories, uploadExcel, isUploadingExcel } = usePdfImport();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [importLogs, setImportLogs] = useState<ImportLog[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logCounter = useRef(0);

  const handleFileSelect = useCallback((file: File) => {
    const name = file.name.toLowerCase();
    if (!name.endsWith(".xlsx") && !name.endsWith(".xls")) {
      return;
    }
    setSelectedFile(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect]
  );

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      const result = await uploadExcel(selectedFile);
      const ts = new Date();
      for (const r of result.results) {
        const id = ++logCounter.current;
        setImportLogs((prev) => [
          {
            id,
            category: r.category,
            inserted: r.inserted,
            skipped: r.skipped,
            total: r.total,
            warnings: r.warnings || [],
            timestamp: ts,
            status: "success",
          },
          ...prev,
        ]);
      }
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || "Upload failed";
      const id = ++logCounter.current;
      setImportLogs((prev) => [
        {
          id,
          category: "all",
          inserted: 0,
          skipped: 0,
          total: 0,
          warnings: [],
          timestamp: new Date(),
          status: "error",
          error: detail,
        },
        ...prev,
      ]);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Import Data from Excel"
        description="Download the template, fill in your data across sheets, and upload the Excel file to bulk-import everything at once"
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* ── Upload Card ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload Excel File
            </CardTitle>
            <CardDescription>
              Upload a filled-in Excel template to import all categories at once
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
                dragOver
                  ? "border-primary bg-primary/5"
                  : selectedFile
                  ? "border-green-500 bg-green-50 dark:bg-green-950/20"
                  : "border-muted-foreground/25 hover:border-primary/50"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
              />
              {selectedFile ? (
                <div className="flex flex-col items-center gap-2">
                  <FileSpreadsheet className="h-10 w-10 text-green-600" />
                  <p className="text-sm font-medium">{selectedFile.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                  >
                    <X className="h-3 w-3 mr-1" /> Remove
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <FileSpreadsheet className="h-10 w-10 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Drag & drop an Excel file here, or click to browse
                  </p>
                  <p className="text-xs text-muted-foreground">Only .xlsx files accepted</p>
                </div>
              )}
            </div>

            {/* Upload button */}
            <Button
              className="w-full gap-2"
              disabled={!selectedFile || isUploadingExcel}
              onClick={handleUpload}
            >
              {isUploadingExcel ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Import All Data
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* ── Instructions Card ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Info className="h-5 w-5" />
              How It Works
            </CardTitle>
            <CardDescription>
              One Excel file with multiple sheets imports everything
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Download template button */}
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={async () => {
                const res = await apiClient.get("/pdf-import/template/excel", { responseType: "blob" });
                const url = URL.createObjectURL(new Blob([res.data]));
                const a = document.createElement("a");
                a.href = url;
                a.download = "import_template.xlsx";
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              <Download className="h-4 w-4" />
              Download Excel Template
            </Button>

            <div className="space-y-3 text-sm">
              <div>
                <p className="font-medium mb-1">Steps:</p>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground text-xs">
                  <li>Download the <strong>Excel template</strong> above</li>
                  <li>Fill in your data in each sheet (sample rows are included)</li>
                  <li>Upload the filled file using the form on the left</li>
                  <li>All sheets are processed automatically in the correct order</li>
                </ol>
              </div>

              <div>
                <p className="font-medium mb-1">Sheets in the template:</p>
                <div className="space-y-2">
                  {categories.map((cat) => (
                    <div key={cat.key} className="bg-muted/50 rounded p-2">
                      <p className="font-medium text-xs">{cat.label}</p>
                      <p className="text-xs text-muted-foreground">{cat.columns}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <p className="font-medium mb-1">Tips:</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground text-xs">
                  <li>You only need to fill in the sheets you want to import</li>
                  <li>Column names are flexible (e.g., "Employee ID" or "Emp ID")</li>
                  <li>Duplicate records are automatically skipped</li>
                  <li>Departments are imported first, so other sheets can reference them</li>
                  <li>For shared subjects, set Department to "Common"</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Import Logs ── */}
      {importLogs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Import Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {importLogs.map((log) => (
                <div
                  key={log.id}
                  className={`rounded-lg border p-4 ${
                    log.status === "success"
                      ? "border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-900"
                      : "border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-900"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      {log.status === "success" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                      <span className="font-medium text-sm capitalize">
                        {log.category}
                      </span>
                      {log.status === "success" && (
                        <div className="flex gap-1">
                          <Badge variant="secondary" className="text-xs">
                            {log.inserted} inserted
                          </Badge>
                          {log.skipped > 0 && (
                            <Badge variant="outline" className="text-xs">
                              {log.skipped} skipped
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {log.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  {log.error && (
                    <p className="text-sm text-red-600 mt-1">{log.error}</p>
                  )}
                  {log.warnings.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {log.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-amber-600">\u26a0 {w}</p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
