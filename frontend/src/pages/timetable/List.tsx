import { Link } from "react-router-dom";
import { Eye, Trash2, Send, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip, getStatusChipVariant } from "@/components/common/StatusChip";
import { useTimetable } from "@/hooks/useTimetable";

export default function TimetableListPage() {
  const { data: timetables, isLoading, publish, remove } = useTimetable();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Timetables" description="View and manage generated timetables">
        <Link to="/timetable/generate">
          <Button className="rounded-xl btn-press">Generate New</Button>
        </Link>
      </PageHeader>

      {timetables.length === 0 ? (
        <div className="bg-card rounded-lg shadow-sm p-12 text-center">
          <p className="text-muted-foreground">No timetables generated yet.</p>
          <Link to="/timetable/generate">
            <Button className="rounded-xl btn-press mt-4">Generate Your First Timetable</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {timetables.map((tt) => (
            <div key={tt.timetable_id} className="bg-card rounded-lg shadow-sm p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <p className="font-medium">Semester {tt.semester} · {tt.academic_year}</p>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {tt.entries.length} entries · Score: {tt.optimization_score ?? "N/A"}/100
                  </p>
                </div>
                <StatusChip variant={getStatusChipVariant(tt.status)} label={tt.status} />
              </div>
              <div className="flex items-center gap-2">
                <Link to={`/timetable/view/${tt.timetable_id}`}>
                  <Button variant="outline" size="sm" className="rounded-xl gap-1.5">
                    <Eye className="h-3.5 w-3.5" />View
                  </Button>
                </Link>
                {tt.status === "DRAFT" && (
                  <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={() => publish(tt.timetable_id)}>
                    <Send className="h-3.5 w-3.5" />Publish
                  </Button>
                )}
                <Button variant="ghost" size="sm" className="rounded-xl text-destructive" onClick={() => remove(tt.timetable_id)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
