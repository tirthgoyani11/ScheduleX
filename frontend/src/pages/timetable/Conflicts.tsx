import { AlertTriangle, Check } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { useParams, Link } from "react-router-dom";
import { useTimetable } from "@/hooks/useTimetable";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ConflictsPage() {
  const { id } = useParams<{ id: string }>();
  const { timetable: tt, timetableLoading } = useTimetable(id);

  if (timetableLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!tt) {
    return (
      <div className="text-center py-12 text-muted-foreground">Timetable not found.</div>
    );
  }

  const score = tt.optimization_score ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Conflict Report" description={`Sem ${tt.semester} · ${tt.academic_year}`} />

      <div className="bg-card rounded-lg shadow-sm p-8 text-center max-w-lg mx-auto space-y-4">
        <div className={`h-16 w-16 rounded-full mx-auto flex items-center justify-center ${score >= 90 ? "bg-chip-green-bg" : score >= 70 ? "bg-chip-orange-bg" : "bg-chip-red-bg"}`}>
          {score >= 90 ? (
            <Check className="h-8 w-8 text-chip-green-txt" />
          ) : (
            <AlertTriangle className="h-8 w-8 text-chip-orange-txt" />
          )}
        </div>
        <h3 className="text-lg font-semibold font-display">
          {score >= 90 ? "No conflicts detected" : score >= 70 ? "Minor optimization gaps" : "Optimization issues found"}
        </h3>
        <p className="text-sm text-muted-foreground">
          Optimization score: <strong>{score}/100</strong>. The OR-Tools solver has resolved all hard constraints.
          {score < 100 && " Some soft constraints may not be fully satisfied."}
        </p>
        <p className="text-sm text-muted-foreground">
          {tt.entries.length} entries across {[...new Set(tt.entries.map(e => e.day))].length} days.
        </p>
        <Link to={`/timetable/view/${tt.timetable_id}`}>
          <Button className="rounded-xl btn-press">View Timetable</Button>
        </Link>
      </div>
    </div>
  );
}
