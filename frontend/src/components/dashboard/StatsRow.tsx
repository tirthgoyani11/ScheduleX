import { BookOpen, Users, AlertTriangle, Building2 } from "lucide-react";
import { MetricCard } from "@/components/common/MetricCard";
import type { DashboardStats } from "@/types";

interface StatsRowProps {
  stats: DashboardStats;
}

export function StatsRow({ stats }: StatsRowProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        icon={BookOpen}
        value={stats.totalSubjects}
        label="Subjects this sem"
        chipClass="chip-purple"
        trend={{ value: "4", positive: true }}
      />
      <MetricCard
        icon={Users}
        value={stats.totalFaculty}
        label="Faculty in dept"
        chipClass="chip-blue"
      />
      <MetricCard
        icon={AlertTriangle}
        value={`${stats.highConflicts} HIGH`}
        label="Conflicts detected"
        chipClass="chip-red"
      />
      <MetricCard
        icon={Building2}
        value={`${stats.roomUtilization}%`}
        label="Room utilized"
        chipClass="chip-green"
        trend={{ value: "5%", positive: true }}
      />
    </div>
  );
}
