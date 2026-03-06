import { Link, useParams } from "react-router-dom";
import { AlertTriangle, Download, Check, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip, getStatusChipVariant } from "@/components/common/StatusChip";
import { SubjectCell } from "@/components/timetable/SubjectCell";
import { useTimetable } from "@/hooks/useTimetable";
import { useTimeSlots } from "@/hooks/useTimeSlots";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

export default function TimetableViewPage() {
  const { id } = useParams<{ id: string }>();
  const { timetable: tt, timetableLoading, publish } = useTimetable(id);
  const { data: slots } = useTimeSlots();

  if (timetableLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!tt) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Timetable not found.</p>
      </div>
    );
  }

  const score = tt.optimization_score ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader title={`Sem ${tt.semester} · ${tt.academic_year}`}>
        <div className="flex items-center gap-3">
          <StatusChip variant={getStatusChipVariant(tt.status)} label={tt.status} />
          <span className={`text-sm font-medium ${score >= 90 ? "text-chip-green-txt" : score >= 70 ? "text-chip-orange-txt" : "text-chip-red-txt"}`}>
            Score: {score}/100
          </span>
          {tt.status.toLowerCase() === "draft" && (
            <Button variant="outline" className="rounded-xl gap-2" onClick={() => publish(tt.timetable_id)}>
              <Check className="h-4 w-4" />Publish
            </Button>
          )}
        </div>
      </PageHeader>

      {/* Timetable Grid */}
      <div className="bg-card rounded-lg shadow-sm overflow-x-auto">
        <table className="w-full border-collapse min-w-[800px]">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-card py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground border-b border-r border-border w-24">Time</th>
              {days.map((day) => (
                <th key={day} className="py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground border-b border-border text-center">{day}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {slots.map((slot) => (
              <tr key={slot.slot_order} className={slot.slot_type === "break" ? "bg-muted/30" : ""}>
                <td className="sticky left-0 z-10 bg-card py-2 px-3 border-r border-b border-border">
                  <div className="text-xs font-medium">{slot.start_time}</div>
                  <div className="text-xs text-muted-foreground">{slot.end_time}</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{slot.label}</div>
                </td>
                {days.map((day) => {
                  if (slot.slot_type === "break") {
                    return (
                      <td key={day} className="py-2 px-2 border-b border-border bg-muted/30">
                        <div className="min-h-[70px] flex items-center justify-center">
                          <span className="text-xs text-muted-foreground italic">{slot.label}</span>
                        </div>
                      </td>
                    );
                  }
                  const entry = tt.entries.find((e) => e.day === day && e.period === slot.slot_order);
                  if (!entry) {
                    return (
                      <td key={day} className="py-2 px-2 border-b border-border">
                        <div className="min-h-[70px] rounded-xl border border-dashed border-border/60" />
                      </td>
                    );
                  }
                  return (
                    <td key={day} className="py-2 px-2 border-b border-border">
                      <SubjectCell entry={entry} />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
