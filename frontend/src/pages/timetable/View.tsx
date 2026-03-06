import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { Check, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip, getStatusChipVariant } from "@/components/common/StatusChip";
import { SubjectCell } from "@/components/timetable/SubjectCell";
import { useTimetable } from "@/hooks/useTimetable";
import { useTimeSlots } from "@/hooks/useTimeSlots";
import type { TimetableEntry } from "@/types";

const ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// Batch color palette for visual distinction
const BATCH_COLORS = [
  "bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800",
  "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800",
  "bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800",
  "bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800",
  "bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800",
  "bg-cyan-50 dark:bg-cyan-950/40 border-cyan-200 dark:border-cyan-800",
];

export default function TimetableViewPage() {
  const { id } = useParams<{ id: string }>();
  const { timetable: tt, timetableLoading, publish } = useTimetable(id);
  const { data: slots } = useTimeSlots();

  // Derive which days actually have entries
  const days = useMemo(() => {
    if (!tt) return ALL_DAYS.slice(0, 5);
    const usedDays = new Set(tt.entries.map((e) => e.day));
    return ALL_DAYS.filter((d) => usedDays.has(d));
  }, [tt]);

  // Get sorted unique batch names from entries
  const batchNames = useMemo(() => {
    if (!tt) return [];
    const names = new Set<string>();
    tt.entries.forEach((e) => { if (e.batch) names.add(e.batch); });
    return Array.from(names).sort();
  }, [tt]);

  // Identify which slot_orders are lab periods (have batched entries)
  const labPeriods = useMemo(() => {
    if (!tt) return new Set<number>();
    const periods = new Set<number>();
    tt.entries.forEach((e) => { if (e.batch) periods.add(e.period); });
    return periods;
  }, [tt]);

  // Build lookup: (day, period) → entry[] for fast access
  const entryLookup = useMemo(() => {
    if (!tt) return new Map<string, TimetableEntry[]>();
    const map = new Map<string, TimetableEntry[]>();
    for (const e of tt.entries) {
      const key = `${e.day}|${e.period}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(e);
    }
    return map;
  }, [tt]);

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
  const hasBatches = batchNames.length > 0;

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

      {/* Batch legend */}
      {hasBatches && (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Lab Batches:</span>
          {batchNames.map((name, i) => (
            <span key={name} className={`text-xs font-medium px-2.5 py-1 rounded-lg border ${BATCH_COLORS[i % BATCH_COLORS.length]}`}>
              Batch {name}
            </span>
          ))}
        </div>
      )}

      {/* Timetable Grid */}
      <div className="bg-card rounded-lg shadow-sm overflow-x-auto">
        <table className="w-full border-collapse min-w-[900px]">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-card py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground border-b border-r border-border w-24">Time</th>
              {days.map((day) => (
                <th key={day} className="py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground border-b border-border text-center">{day}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {slots.map((slot) => {
              const isLab = labPeriods.has(slot.slot_order);

              return (
                <tr key={slot.slot_order} className={slot.slot_type === "break" ? "bg-muted/30" : ""}>
                  {/* Time column */}
                  <td className="sticky left-0 z-10 bg-card py-2 px-3 border-r border-b border-border align-top">
                    <div className="text-xs font-medium">{slot.start_time}</div>
                    <div className="text-xs text-muted-foreground">{slot.end_time}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">{slot.label}</div>
                    {isLab && <div className="text-[9px] font-medium text-primary mt-1 uppercase">Lab</div>}
                  </td>

                  {days.map((day) => {
                    // Break row
                    if (slot.slot_type === "break") {
                      return (
                        <td key={day} className="py-2 px-2 border-b border-border bg-muted/30">
                          <div className="min-h-[70px] flex items-center justify-center">
                            <span className="text-xs text-muted-foreground italic">{slot.label}</span>
                          </div>
                        </td>
                      );
                    }

                    const cellEntries = entryLookup.get(`${day}|${slot.slot_order}`) || [];

                    // No entries
                    if (cellEntries.length === 0) {
                      return (
                        <td key={day} className="py-2 px-2 border-b border-border">
                          <div className="min-h-[70px] rounded-xl border border-dashed border-border/60" />
                        </td>
                      );
                    }

                    // Single theory entry (no batch)
                    const theoryEntries = cellEntries.filter((e) => !e.batch);
                    const batchEntries = cellEntries.filter((e) => e.batch);

                    if (batchEntries.length === 0 && theoryEntries.length > 0) {
                      return (
                        <td key={day} className="py-2 px-2 border-b border-border">
                          <SubjectCell entry={theoryEntries[0]} />
                        </td>
                      );
                    }

                    // Lab entries with batches — show side-by-side sub-columns like GCET reference
                    return (
                      <td key={day} className="py-1 px-1 border-b border-border">
                        <div className="flex gap-0.5">
                          {batchNames.map((batchName, bIdx) => {
                            const batchEntry = batchEntries.find((e) => e.batch === batchName);
                            if (!batchEntry) {
                              return (
                                <div key={batchName} className="flex-1 min-w-0 rounded-lg border border-dashed border-border/40 min-h-[80px] flex items-center justify-center">
                                  <span className="text-[9px] text-muted-foreground">{batchName}</span>
                                </div>
                              );
                            }
                            return (
                              <div
                                key={batchName}
                                className={`flex-1 min-w-0 rounded-lg border p-1.5 min-h-[80px] flex flex-col ${BATCH_COLORS[bIdx % BATCH_COLORS.length]}`}
                              >
                                <span className="text-[9px] font-bold text-muted-foreground uppercase mb-0.5">{batchName}</span>
                                <p className="text-[11px] font-medium leading-tight truncate">{batchEntry.subject_name}</p>
                                <p className="text-[9px] text-muted-foreground mt-auto truncate">{batchEntry.faculty_name}</p>
                                <p className="text-[9px] text-muted-foreground truncate">{batchEntry.room_name}</p>
                              </div>
                            );
                          })}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
