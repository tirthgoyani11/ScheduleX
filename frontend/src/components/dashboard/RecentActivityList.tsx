import type { Activity, ActivityType } from "@/types";

const activityChip: Record<ActivityType, { class: string; label: string }> = {
  TIMETABLE_GENERATED: { class: "chip-green", label: "Generated" },
  CONFLICT_DETECTED: { class: "chip-orange", label: "Conflict" },
  FACULTY_ADDED: { class: "chip-blue", label: "Faculty" },
  EXPORT_DOWNLOADED: { class: "chip-purple", label: "Export" },
};

export function RecentActivityList({ activities }: { activities: Activity[] }) {
  return (
    <ul className="space-y-3">
      {activities.map((a) => {
        const chipInfo = activityChip[a.type];
        const timeAgo = getRelativeTime(a.timestamp);
        return (
          <li key={a.id} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
            <span className={`chip ${chipInfo.class}`}>{chipInfo.label}</span>
            <span className="text-sm flex-1">{a.description}</span>
            <span className="text-xs text-muted-foreground whitespace-nowrap">{timeAgo}</span>
          </li>
        );
      })}
    </ul>
  );
}

function getRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
