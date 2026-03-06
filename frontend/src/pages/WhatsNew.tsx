import { Sparkles, Zap, Shield, BarChart3, FileText, Bell } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";

interface ChangelogEntry {
  version: string;
  date: string;
  title: string;
  description: string;
  icon: React.ElementType;
  chipClass: string;
  chipLabel: string;
  items: string[];
}

const changelog: ChangelogEntry[] = [
  {
    version: "1.3.0",
    date: "March 2026",
    title: "AI-Powered Conflict Resolution",
    description: "Smart suggestions to automatically resolve scheduling conflicts with one click.",
    icon: Sparkles,
    chipClass: "chip-purple",
    chipLabel: "New",
    items: [
      "Auto-resolve button for all conflict types",
      "ML-based optimal slot suggestions",
      "Batch conflict resolution for multiple issues",
      "Conflict severity scoring improvements",
    ],
  },
  {
    version: "1.2.0",
    date: "February 2026",
    title: "Enhanced Export Options",
    description: "Export timetables in multiple formats with customizable layouts.",
    icon: FileText,
    chipClass: "chip-blue",
    chipLabel: "Improved",
    items: [
      "Faculty-wise individual PDF schedules",
      "Room allocation reports",
      "Excel workbook with 4 sheets",
      "Custom header/footer in PDFs",
    ],
  },
  {
    version: "1.1.0",
    date: "January 2026",
    title: "Multi-Department Support",
    description: "Manage timetables across departments with shared faculty tracking.",
    icon: Shield,
    chipClass: "chip-green",
    chipLabel: "Feature",
    items: [
      "Department switcher in topbar",
      "Shared faculty cross-department tracking",
      "Cross-department conflict detection",
      "Department-wise analytics dashboard",
    ],
  },
  {
    version: "1.0.2",
    date: "December 2025",
    title: "Performance & Analytics",
    description: "Dashboard analytics improvements and faster timetable generation.",
    icon: BarChart3,
    chipClass: "chip-orange",
    chipLabel: "Update",
    items: [
      "Faculty workload visualization",
      "Room utilization donut chart",
      "Recent activity timeline",
      "50% faster generation algorithm",
    ],
  },
  {
    version: "1.0.1",
    date: "November 2025",
    title: "Notification System",
    description: "Stay updated with real-time notifications for schedule changes.",
    icon: Bell,
    chipClass: "chip-yellow",
    chipLabel: "Update",
    items: [
      "In-app notifications for conflicts",
      "Email alerts for schedule approvals",
      "Activity feed on dashboard",
    ],
  },
  {
    version: "1.0.0",
    date: "October 2025",
    title: "Initial Release",
    description: "ScheduleX launches with core timetable generation and management.",
    icon: Zap,
    chipClass: "chip-green",
    chipLabel: "Launch",
    items: [
      "3-step timetable generation wizard",
      "Weekly grid view with color-coded cells",
      "Time slot, subject & faculty management",
      "Basic conflict detection",
      "PDF export",
    ],
  },
];

export default function WhatsNewPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader title="What's New" description="Latest updates and features in ScheduleX" />

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-5 top-8 bottom-8 w-px bg-border" />

        <div className="space-y-6">
          {changelog.map((entry) => (
            <div key={entry.version} className="relative pl-14">
              {/* Timeline dot */}
              <div className="absolute left-2.5 top-5 h-5 w-5 rounded-full bg-card border-2 border-border flex items-center justify-center z-10">
                <div className="h-2 w-2 rounded-full bg-primary" />
              </div>

              <div className="bg-card rounded-lg shadow-sm p-5 card-hover">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`chip ${entry.chipClass}`}>{entry.chipLabel}</div>
                  <span className="text-xs font-mono text-muted-foreground">v{entry.version}</span>
                  <span className="text-xs text-muted-foreground">·</span>
                  <span className="text-xs text-muted-foreground">{entry.date}</span>
                </div>

                <div className="flex items-start gap-3 mb-3">
                  <div className={`chip ${entry.chipClass} !rounded-xl !p-2`}>
                    <entry.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="font-medium font-display">{entry.title}</h3>
                    <p className="text-sm text-muted-foreground mt-0.5">{entry.description}</p>
                  </div>
                </div>

                <ul className="space-y-1.5 ml-1">
                  {entry.items.map((item, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span className="h-1 w-1 rounded-full bg-muted-foreground shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
