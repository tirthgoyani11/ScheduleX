import { FileText, Table2, User, Building2, Download, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useTimetable } from "@/hooks/useTimetable";
import { useFaculty } from "@/hooks/useFaculty";
import { useTimeSlots } from "@/hooks/useTimeSlots";
import { useState } from "react";
import { toast } from "sonner";
import {
  exportDepartmentPDF,
  exportExcelWorkbook,
  exportFacultyPDF,
  exportRoomPDF,
} from "@/lib/export-utils";

const exportOptions = [
  { icon: FileText, title: "Department PDF", description: "Full timetable grid, color coded, A4 landscape", format: "pdf" },
  { icon: Table2, title: "Excel Workbook", description: "4 sheets: Grid + Faculty + Room + Summary", format: "xlsx" },
  { icon: User, title: "Faculty Schedule", description: "Individual schedule PDF for a faculty member", format: "faculty-pdf", hasFacultySelect: true },
  { icon: Building2, title: "Room Allocation", description: "Room-wise timetable view PDF", format: "room-pdf" },
];

export default function ExportPage() {
  const { data: timetables, isLoading } = useTimetable();
  const { data: allFaculty } = useFaculty();
  const { data: slots } = useTimeSlots();
  const [selectedTimetableId, setSelectedTimetableId] = useState("");
  const [selectedFacultyName, setSelectedFacultyName] = useState("");
  const [exporting, setExporting] = useState<string | null>(null);

  // Fetch the full timetable (with entries) for the selected ID
  const { timetable: selectedTT, timetableLoading } = useTimetable(
    selectedTimetableId || undefined
  );

  const handleExport = async (format: string) => {
    if (!selectedTT) {
      toast.error("Please select a timetable first");
      return;
    }
    if (selectedTT.entries.length === 0) {
      toast.error("Selected timetable has no entries");
      return;
    }
    if (format === "faculty-pdf" && !selectedFacultyName) {
      toast.error("Please select a faculty member");
      return;
    }

    setExporting(format);
    try {
      switch (format) {
        case "pdf":
          exportDepartmentPDF(selectedTT, slots);
          break;
        case "xlsx":
          exportExcelWorkbook(selectedTT, slots);
          break;
        case "faculty-pdf":
          exportFacultyPDF(selectedTT, slots, selectedFacultyName);
          break;
        case "room-pdf":
          exportRoomPDF(selectedTT, slots);
          break;
      }
      toast.success("Export downloaded successfully");
    } catch {
      toast.error("Export failed — please try again");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Export Timetable" description="Download timetables in various formats" />

      <div className="max-w-xs space-y-2">
        <Label>Select Timetable</Label>
        <Select value={selectedTimetableId} onValueChange={setSelectedTimetableId}>
          <SelectTrigger className="rounded-xl"><SelectValue placeholder="Select a timetable" /></SelectTrigger>
          <SelectContent>
            {timetables.map((tt) => (
              <SelectItem key={tt.timetable_id} value={tt.timetable_id}>
                Sem {tt.semester} · {tt.academic_year} · {tt.status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {timetableLoading && selectedTimetableId && (
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" /> Loading entries…
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {exportOptions.map((opt) => {
          const isDisabled = !selectedTT || timetableLoading || exporting === opt.format;
          return (
            <div key={opt.title} className="bg-card rounded-lg shadow-sm p-6 card-hover space-y-4">
              <div className="flex items-start gap-3">
                <div className="chip chip-blue !rounded-xl !p-2.5"><opt.icon className="h-5 w-5" /></div>
                <div>
                  <h3 className="font-medium font-display">{opt.title}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">{opt.description}</p>
                </div>
              </div>
              {opt.hasFacultySelect && (
                <Select value={selectedFacultyName} onValueChange={setSelectedFacultyName}>
                  <SelectTrigger className="rounded-xl"><SelectValue placeholder="Select faculty member" /></SelectTrigger>
                  <SelectContent>
                    {allFaculty.map((f) => (
                      <SelectItem key={f.faculty_id} value={f.name}>{f.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <Button
                variant="outline"
                className="rounded-xl btn-press gap-2 w-full"
                onClick={() => handleExport(opt.format)}
                disabled={isDisabled}
              >
                {exporting === opt.format ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Download {opt.format.includes("pdf") ? "PDF" : "Excel"}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
