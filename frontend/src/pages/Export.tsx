import { FileText, Table2, User, Building2, Download } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useTimetable } from "@/hooks/useTimetable";
import { useFaculty } from "@/hooks/useFaculty";
import { useState } from "react";
import { toast } from "sonner";

const exportOptions = [
  { icon: FileText, title: "Department PDF", description: "Full timetable grid, color coded, A4 format", format: "pdf" },
  { icon: Table2, title: "Excel Workbook", description: "4 sheets: Grid + Faculty + Room + Summary", format: "xlsx" },
  { icon: User, title: "Faculty Schedules", description: "Individual PDFs for each faculty member", format: "faculty-pdf", hasFacultySelect: true },
  { icon: Building2, title: "Room Allocation", description: "Room-wise timetable view PDF", format: "room-pdf" },
];

export default function ExportPage() {
  const { data: timetables, isLoading } = useTimetable();
  const { data: allFaculty } = useFaculty();
  const [selectedTimetable, setSelectedTimetable] = useState("");
  const [selectedFaculty, setSelectedFaculty] = useState("");

  const handleExport = (format: string) => {
    toast.success(`${format.toUpperCase()} export started — downloading shortly`);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Export Timetable" description="Download timetables in various formats" />

      <div className="max-w-xs space-y-2">
        <Label>Select Timetable</Label>
        <Select value={selectedTimetable} onValueChange={setSelectedTimetable}>
          <SelectTrigger className="rounded-xl"><SelectValue placeholder="Select a timetable" /></SelectTrigger>
          <SelectContent>
            {timetables.map((tt) => (
              <SelectItem key={tt.timetable_id} value={tt.timetable_id}>
                Sem {tt.semester} · {tt.academic_year} · {tt.status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {exportOptions.map((opt) => (
          <div key={opt.title} className="bg-card rounded-lg shadow-sm p-6 card-hover space-y-4">
            <div className="flex items-start gap-3">
              <div className="chip chip-blue !rounded-xl !p-2.5"><opt.icon className="h-5 w-5" /></div>
              <div>
                <h3 className="font-medium font-display">{opt.title}</h3>
                <p className="text-sm text-muted-foreground mt-0.5">{opt.description}</p>
              </div>
            </div>
            {opt.hasFacultySelect && (
              <Select value={selectedFaculty} onValueChange={setSelectedFaculty}>
                <SelectTrigger className="rounded-xl"><SelectValue placeholder="Select faculty member" /></SelectTrigger>
                <SelectContent>
                  {allFaculty.map((f) => <SelectItem key={f.faculty_id} value={f.faculty_id}>{f.name}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
            <Button variant="outline" className="rounded-xl btn-press gap-2 w-full" onClick={() => handleExport(opt.format)}>
              <Download className="h-4 w-4" />Download {opt.format.includes("pdf") ? "PDF" : "Excel"}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
