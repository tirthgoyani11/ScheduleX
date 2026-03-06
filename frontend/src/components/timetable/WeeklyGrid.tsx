import { DEFAULT_TIME_SLOTS } from "@/types";
import { SubjectCell } from "@/components/timetable/SubjectCell";
import type { TimetableEntry } from "@/types";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

interface WeeklyGridProps {
  entries: TimetableEntry[];
}

export function WeeklyGrid({ entries }: WeeklyGridProps) {
  return (
    <div className="bg-card rounded-lg shadow-sm overflow-x-auto">
      <table className="w-full border-collapse min-w-[800px]">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-card py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground border-b border-r border-border w-24">
              Time
            </th>
            {days.map((day) => (
              <th
                key={day}
                className="py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground border-b border-border text-center"
              >
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DEFAULT_TIME_SLOTS.map((slot) => (
            <tr key={slot.period}>
              <td className="sticky left-0 z-10 bg-card py-2 px-3 border-r border-b border-border">
                <div className="text-xs font-medium">{slot.startTime}</div>
                <div className="text-xs text-muted-foreground">{slot.endTime}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{slot.label}</div>
              </td>
              {days.map((day) => {
                const entry = entries.find((e) => e.day === day && e.period === slot.period);
                if (!entry) {
                  return (
                    <td key={day} className="py-2 px-2 border-b border-border">
                      <div className="min-h-[70px] rounded-xl border border-dashed border-border/60 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                        <span className="text-xs text-muted-foreground">+</span>
                      </div>
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
  );
}
