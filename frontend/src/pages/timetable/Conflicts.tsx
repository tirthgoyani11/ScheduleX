import { useMemo, useState } from "react";
import { AlertTriangle, Check, ShieldCheck, Users, DoorOpen, Clock, BookOpen, Loader2, ChevronDown } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { useParams, Link } from "react-router-dom";
import { useTimetable } from "@/hooks/useTimetable";
import { Button } from "@/components/ui/button";
import type { Timetable, TimetableEntry } from "@/types";

// ── Conflict detection types ─────────────────────────────

interface Conflict {
  id: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  type: string;
  description: string;
  suggestion: string;
  day: string;
  period: number;
}

// ── Client-side conflict detection ───────────────────────

function detectConflicts(entries: TimetableEntry[]): Conflict[] {
  const conflicts: Conflict[] = [];
  let cid = 0;

  // Index entries by (day, period)
  const bySlot = new Map<string, TimetableEntry[]>();
  for (const e of entries) {
    const key = `${e.day}|${e.period}`;
    if (!bySlot.has(key)) bySlot.set(key, []);
    bySlot.get(key)!.push(e);
  }

  // HC1: Faculty double-booking — same faculty, same day+period, different subjects
  const facultySlots = new Map<string, TimetableEntry[]>();
  for (const e of entries) {
    const key = `${e.faculty_name}|${e.day}|${e.period}`;
    if (!facultySlots.has(key)) facultySlots.set(key, []);
    facultySlots.get(key)!.push(e);
  }
  for (const [key, group] of facultySlots) {
    // Only flag if different subjects (same faculty teaching multiple things at same slot)
    const uniqueSubjects = new Set(group.map(e => e.subject_name));
    if (uniqueSubjects.size > 1) {
      const [faculty, day, period] = key.split("|");
      conflicts.push({
        id: `hc1-${cid++}`,
        severity: "HIGH",
        type: "FACULTY_CLASH",
        description: `${faculty} is double-booked on ${day} period ${period}: ${[...uniqueSubjects].join(", ")}`,
        suggestion: "Reassign one of the classes to a different faculty or time slot.",
        day,
        period: Number(period),
      });
    }
  }

  // HC2: Room double-booking — same room, same day+period, different classes
  const roomSlots = new Map<string, TimetableEntry[]>();
  for (const e of entries) {
    const key = `${e.room_name}|${e.day}|${e.period}`;
    if (!roomSlots.has(key)) roomSlots.set(key, []);
    roomSlots.get(key)!.push(e);
  }
  for (const [key, group] of roomSlots) {
    // Exclude same-batch lab entries (batches A/B/C in same room at same time is fine)
    const uniqueSubjects = new Set(group.map(e => `${e.subject_name}|${e.batch ?? ""}`));
    if (uniqueSubjects.size > 1) {
      const [room, day, period] = key.split("|");
      conflicts.push({
        id: `hc2-${cid++}`,
        severity: "HIGH",
        type: "ROOM_CLASH",
        description: `Room ${room} has overlapping classes on ${day} period ${period}: ${group.map(e => e.subject_name).join(", ")}`,
        suggestion: "Move one class to a different room or time slot.",
        day,
        period: Number(period),
      });
    }
  }

  // HC11: Duplicate subject per day — same subject (theory only) appears more than once on a day
  const theoryEntries = entries.filter(e => !e.batch);
  const subjectDay = new Map<string, TimetableEntry[]>();
  for (const e of theoryEntries) {
    const key = `${e.subject_name}|${e.day}`;
    if (!subjectDay.has(key)) subjectDay.set(key, []);
    subjectDay.get(key)!.push(e);
  }
  for (const [key, group] of subjectDay) {
    if (group.length > 1) {
      const [subject, day] = key.split("|");
      conflicts.push({
        id: `hc11-${cid++}`,
        severity: "MEDIUM",
        type: "DUPLICATE_SUBJECT",
        description: `${subject} has ${group.length} theory lectures on ${day} (periods ${group.map(e => e.period).join(", ")})`,
        suggestion: "Spread theory lectures across different days for better learning retention.",
        day,
        period: group[0].period,
      });
    }
  }

  // SC: Consecutive same-subject theory — same subject in adjacent periods (same day)
  const sortedTheory = [...theoryEntries].sort((a, b) => {
    if (a.day !== b.day) return a.day.localeCompare(b.day);
    return a.period - b.period;
  });
  for (let i = 0; i < sortedTheory.length - 1; i++) {
    const a = sortedTheory[i];
    const b = sortedTheory[i + 1];
    if (a.day === b.day && a.subject_name === b.subject_name && b.period - a.period <= 2) {
      conflicts.push({
        id: `sc-consec-${cid++}`,
        severity: "LOW",
        type: "CONSECUTIVE_LECTURE",
        description: `${a.subject_name} has back-to-back theory lectures on ${a.day} (periods ${a.period}, ${b.period})`,
        suggestion: "Add a gap between lectures of the same subject for student attention span.",
        day: a.day,
        period: a.period,
      });
    }
  }

  // SC: Empty days — a working day with no entries
  const allDays = [...new Set(entries.map(e => e.day))];
  const daysWithTheory = new Set(theoryEntries.map(e => e.day));
  for (const day of allDays) {
    if (!daysWithTheory.has(day)) {
      const dayEntries = entries.filter(e => e.day === day);
      if (dayEntries.length === 0) {
        conflicts.push({
          id: `sc-empty-${cid++}`,
          severity: "LOW",
          type: "EMPTY_DAY",
          description: `${day} has no classes scheduled`,
          suggestion: "Distribute classes more evenly across the week.",
          day,
          period: 0,
        });
      }
    }
  }

  return conflicts;
}

// ── Severity styling helpers ─────────────────────────────

const severityBg: Record<string, string> = {
  HIGH: "bg-red-50 border-l-4 border-l-red-500 dark:bg-red-950/30",
  MEDIUM: "bg-orange-50 border-l-4 border-l-orange-500 dark:bg-orange-950/30",
  LOW: "bg-yellow-50 border-l-4 border-l-yellow-400 dark:bg-yellow-950/30",
};

const severityIcon: Record<string, string> = {
  HIGH: "text-red-500",
  MEDIUM: "text-orange-500",
  LOW: "text-yellow-500",
};

const severityBadge: Record<string, string> = {
  HIGH: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
  MEDIUM: "bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300",
  LOW: "bg-yellow-100 text-yellow-600 dark:bg-yellow-900/50 dark:text-yellow-300",
};

const typeLabels: Record<string, { icon: React.ReactNode; label: string }> = {
  FACULTY_CLASH: { icon: <Users className="h-3.5 w-3.5" />, label: "Faculty Clash" },
  ROOM_CLASH: { icon: <DoorOpen className="h-3.5 w-3.5" />, label: "Room Clash" },
  DUPLICATE_SUBJECT: { icon: <BookOpen className="h-3.5 w-3.5" />, label: "Duplicate Subject" },
  CONSECUTIVE_LECTURE: { icon: <Clock className="h-3.5 w-3.5" />, label: "Consecutive Lecture" },
  EMPTY_DAY: { icon: <Clock className="h-3.5 w-3.5" />, label: "Empty Day" },
};

// ── Component ────────────────────────────────────────────

export default function ConflictsPage() {
  const { id } = useParams<{ id: string }>();
  const { data: timetables, isLoading: listLoading, timetable: directTt, timetableLoading } = useTimetable(id);

  // When no ID param, let user pick; default to latest
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Determine which timetable to show
  const activeTimetables = useMemo(
    () => timetables.filter((t: Timetable) => t.status !== "deleted" && t.status !== "DELETED"),
    [timetables],
  );

  const tt = id
    ? directTt
    : activeTimetables.find((t: Timetable) => t.timetable_id === selectedId) ?? activeTimetables[0] ?? null;

  const loading = id ? timetableLoading : listLoading;

  // Detect conflicts
  const conflicts = useMemo(() => (tt?.entries ? detectConflicts(tt.entries) : []), [tt]);
  const highCount = conflicts.filter(c => c.severity === "HIGH").length;
  const mediumCount = conflicts.filter(c => c.severity === "MEDIUM").length;
  const lowCount = conflicts.filter(c => c.severity === "LOW").length;

  const score = tt?.optimization_score ?? 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!tt) {
    return (
      <div className="text-center py-12 space-y-3">
        <AlertTriangle className="h-10 w-10 mx-auto text-muted-foreground/50" />
        <p className="text-muted-foreground">No timetable found. Generate a timetable first.</p>
        <Link to="/timetable/generate">
          <Button className="rounded-xl btn-press mt-2">Generate Timetable</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Conflict Report" description={`Sem ${tt.semester} · ${tt.academic_year}`}>
        {!id && activeTimetables.length > 1 && (
          <div className="relative">
            <select
              value={tt.timetable_id}
              onChange={e => setSelectedId(e.target.value)}
              className="appearance-none bg-card border rounded-xl px-4 py-2 pr-8 text-sm font-medium cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {activeTimetables.map((t: Timetable) => (
                <option key={t.timetable_id} value={t.timetable_id}>
                  Sem {t.semester} · {t.academic_year} · {t.status.toUpperCase()}
                </option>
              ))}
            </select>
            <ChevronDown className="h-4 w-4 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground" />
          </div>
        )}
      </PageHeader>

      {/* ── Score + Summary ──────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl shadow-sm p-5 flex items-center gap-4 md:col-span-1">
          <div className={`h-14 w-14 rounded-full flex items-center justify-center shrink-0 ${
            score >= 90 ? "bg-green-100 dark:bg-green-900/30" : score >= 70 ? "bg-orange-100 dark:bg-orange-900/30" : "bg-red-100 dark:bg-red-900/30"
          }`}>
            {conflicts.length === 0 ? (
              <ShieldCheck className={`h-7 w-7 ${score >= 90 ? "text-green-600" : "text-orange-500"}`} />
            ) : (
              <AlertTriangle className={`h-7 w-7 ${highCount > 0 ? "text-red-500" : "text-orange-500"}`} />
            )}
          </div>
          <div>
            <p className="text-2xl font-bold font-display">{score}<span className="text-sm font-normal text-muted-foreground">/100</span></p>
            <p className="text-xs text-muted-foreground">Optimization Score</p>
          </div>
        </div>

        <SummaryCard label="Hard Conflicts" count={highCount} color="red" icon={<AlertTriangle className="h-4 w-4" />} />
        <SummaryCard label="Soft Conflicts" count={mediumCount} color="orange" icon={<AlertTriangle className="h-4 w-4" />} />
        <SummaryCard label="Suggestions" count={lowCount} color="yellow" icon={<Clock className="h-4 w-4" />} />
      </div>

      {/* ── Stats ────────────────────────────────────────── */}
      <div className="flex items-center gap-6 text-sm text-muted-foreground">
        <span>{tt.entries.length} entries</span>
        <span>{[...new Set(tt.entries.map(e => e.day))].length} days</span>
        <span>{[...new Set(tt.entries.filter(e => !e.batch).map(e => e.subject_name))].length} subjects</span>
        <span>{[...new Set(tt.entries.map(e => e.faculty_name))].length} faculty</span>
        <Link to={`/timetable/view/${tt.timetable_id}`} className="ml-auto">
          <Button variant="outline" size="sm" className="rounded-xl">View Timetable</Button>
        </Link>
      </div>

      {/* ── Conflicts list ───────────────────────────────── */}
      {conflicts.length === 0 ? (
        <div className="bg-card rounded-xl shadow-sm p-10 text-center space-y-3">
          <div className="h-16 w-16 rounded-full mx-auto flex items-center justify-center bg-green-100 dark:bg-green-900/30">
            <Check className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold font-display">All Clear</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            No scheduling conflicts detected. All hard constraints are satisfied
            {score < 100 && ", though some soft constraints have minor trade-offs"}.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {conflicts.map(c => {
            const typeInfo = typeLabels[c.type] ?? { icon: <AlertTriangle className="h-3.5 w-3.5" />, label: c.type };
            return (
              <div key={c.id} className={`rounded-xl p-4 ${severityBg[c.severity]}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <AlertTriangle className={`h-5 w-5 shrink-0 mt-0.5 ${severityIcon[c.severity]}`} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${severityBadge[c.severity]}`}>
                          {c.severity}
                        </span>
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          {typeInfo.icon} {typeInfo.label}
                        </span>
                      </div>
                      <p className="text-sm font-medium">{c.description}</p>
                      <div className="mt-2 bg-background/60 rounded-lg p-2.5 flex items-start gap-2">
                        <span className="text-sm">💡</span>
                        <p className="text-xs text-muted-foreground">{c.suggestion}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Small summary card ───────────────────────────────────

function SummaryCard({ label, count, color, icon }: { label: string; count: number; color: string; icon: React.ReactNode }) {
  const colors: Record<string, string> = {
    red: count > 0 ? "bg-red-50 dark:bg-red-950/20" : "bg-card",
    orange: count > 0 ? "bg-orange-50 dark:bg-orange-950/20" : "bg-card",
    yellow: count > 0 ? "bg-yellow-50 dark:bg-yellow-950/20" : "bg-card",
  };
  const textColors: Record<string, string> = {
    red: count > 0 ? "text-red-600" : "text-muted-foreground",
    orange: count > 0 ? "text-orange-600" : "text-muted-foreground",
    yellow: count > 0 ? "text-yellow-600" : "text-muted-foreground",
  };
  return (
    <div className={`rounded-xl shadow-sm p-5 ${colors[color]}`}>
      <div className={`flex items-center gap-2 mb-1 ${textColors[color]}`}>
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className={`text-2xl font-bold font-display ${textColors[color]}`}>{count}</p>
    </div>
  );
}
