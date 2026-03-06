import { Link } from "react-router-dom";
import { BookOpen, Users, Building2, Zap, Eye, Download, BarChart3, CalendarDays, Clock, Settings2 } from "lucide-react";
import { MetricCard } from "@/components/common/MetricCard";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useDashboard } from "@/hooks/useDashboard";
import { useAuthStore } from "@/store/useAuthStore";
import { WorkloadChart } from "@/components/dashboard/WorkloadChart";
import { RoomUtilizationChart } from "@/components/dashboard/RoomUtilizationChart";
import { DashboardSkeleton } from "@/components/skeletons/PageSkeletons";

const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
};

export default function HodDashboard() {
  const { stats, facultyLoad, roomUtilisation, isLoading } = useDashboard();
  const user = useAuthStore((s) => s.user);

  if (isLoading) return <DashboardSkeleton />;

  const userName = user?.full_name?.split(" ")[0] ?? "HOD";

  const workloadData = facultyLoad.map((f) => ({
    name: f.name.split(" ").pop() ?? f.name,
    fullName: f.name,
    current: f.assigned_periods,
    max: f.max_weekly_load,
    percentage: f.utilisation_pct,
  }));

  const avgRoomUtil = roomUtilisation.length > 0
    ? Math.round(roomUtilisation.reduce((sum, r) => sum + r.utilisation_pct, 0) / roomUtilisation.length)
    : 0;

  const COLORS = [
    "hsl(142,64%,24%)", "hsl(27,96%,48%)", "hsl(221,83%,53%)",
    "hsl(280,67%,51%)", "hsl(0,72%,51%)", "hsl(190,80%,42%)",
    "hsl(45,93%,47%)", "hsl(330,65%,50%)", "hsl(160,60%,40%)",
    "hsl(260,50%,60%)", "hsl(15,80%,55%)", "hsl(200,70%,50%)",
  ];
  const roomUtilData = roomUtilisation.map((r, i) => ({
    name: r.name,
    value: r.utilisation_pct,
    fill: COLORS[i % COLORS.length],
    capacity: r.capacity,
    bookedSlots: r.booked_slots,
    totalSlots: r.total_slots,
  }));

  return (
    <div className="space-y-6">
      <PageHeader title={`${greeting()}, ${userName} 👋`} description="Department Overview — Head of Department Dashboard">
        <div className="flex gap-2">
          <Link to="/timetable/generate">
            <Button className="rounded-xl btn-press gap-2"><Zap className="h-4 w-4" />Generate Timetable</Button>
          </Link>
          <Link to="/export">
            <Button variant="outline" className="rounded-xl gap-2"><Download className="h-4 w-4" />Export</Button>
          </Link>
        </div>
      </PageHeader>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Users} value={stats.faculty_count} label="Faculty Members" chipClass="chip-blue" />
        <MetricCard icon={BookOpen} value={stats.subject_count} label="Subjects" chipClass="chip-purple" />
        <MetricCard icon={CalendarDays} value={stats.timetable_count} label="Timetables" chipClass="chip-green" />
        <MetricCard icon={Building2} value={stats.room_count} label="Rooms" chipClass="chip-orange" />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Link to="/setup/faculty" className="bg-card rounded-xl shadow-sm p-4 card-hover flex items-center gap-3">
          <div className="chip chip-blue !rounded-xl !p-2.5"><Users className="h-4 w-4" /></div>
          <div>
            <p className="text-sm font-medium">Manage Faculty</p>
            <p className="text-xs text-muted-foreground">Add, edit or remove faculty</p>
          </div>
        </Link>
        <Link to="/setup/subjects" className="bg-card rounded-xl shadow-sm p-4 card-hover flex items-center gap-3">
          <div className="chip chip-purple !rounded-xl !p-2.5"><BookOpen className="h-4 w-4" /></div>
          <div>
            <p className="text-sm font-medium">Manage Subjects</p>
            <p className="text-xs text-muted-foreground">Configure course subjects</p>
          </div>
        </Link>
        <Link to="/setup/time-slots" className="bg-card rounded-xl shadow-sm p-4 card-hover flex items-center gap-3">
          <div className="chip chip-green !rounded-xl !p-2.5"><Clock className="h-4 w-4" /></div>
          <div>
            <p className="text-sm font-medium">Time Slots</p>
            <p className="text-xs text-muted-foreground">Manage time slot config</p>
          </div>
        </Link>
        <Link to="/timetable/list" className="bg-card rounded-xl shadow-sm p-4 card-hover flex items-center gap-3">
          <div className="chip chip-orange !rounded-xl !p-2.5"><Eye className="h-4 w-4" /></div>
          <div>
            <p className="text-sm font-medium">View Timetables</p>
            <p className="text-xs text-muted-foreground">Browse all timetables</p>
          </div>
        </Link>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-card rounded-lg shadow-sm p-5 overflow-hidden">
          <h3 className="text-base font-medium font-display mb-4">Faculty Workload Distribution</h3>
          {workloadData.length > 0 ? (
            <WorkloadChart data={workloadData} />
          ) : (
            <p className="text-sm text-muted-foreground">No faculty data yet. Add faculty members to see workload.</p>
          )}
        </div>
        <div className="lg:col-span-2 bg-card rounded-lg shadow-sm p-5 overflow-hidden">
          <h3 className="text-base font-medium font-display mb-4">Room Utilization</h3>
          {roomUtilData.length > 0 ? (
            <RoomUtilizationChart data={roomUtilData} percentage={avgRoomUtil} />
          ) : (
            <p className="text-sm text-muted-foreground">No room data yet. Generate a timetable first.</p>
          )}
        </div>
      </div>
    </div>
  );
}
