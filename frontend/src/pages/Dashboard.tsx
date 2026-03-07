import { Link } from "react-router-dom";
import { useState, useMemo } from "react";
import { BookOpen, Users, Building2, Zap, Eye, Download, BarChart3 } from "lucide-react";
import { MetricCard } from "@/components/common/MetricCard";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDashboard } from "@/hooks/useDashboard";
import { useDepartments } from "@/hooks/useDepartments";
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

export default function DashboardPage() {
  const { stats, facultyLoad, roomUtilisation, isLoading } = useDashboard();
  const { data: departments } = useDepartments();
  const user = useAuthStore((s) => s.user);
  const [selectedDept, setSelectedDept] = useState<string>("");

  if (isLoading) return <DashboardSkeleton />;

  const userName = user?.full_name ?? "Admin";

  // Derive workload chart data from faculty load
  const workloadData = useMemo(() => {
    const allData = facultyLoad.map((f) => ({
      name: f.name.split(" ").pop() ?? f.name,
      fullName: f.name,
      current: f.assigned_periods,
      max: f.max_weekly_load,
      percentage: f.utilisation_pct,
      deptCode: f.dept_code,
      deptId: f.dept_id,
    }));
    
    if (!selectedDept && departments.length > 0) {
      // Default to first department if none selected
      return allData.filter((f) => f.deptId === departments[0].dept_id);
    }
    return allData.filter((f) => f.deptId === selectedDept);
  }, [facultyLoad, selectedDept, departments]);

  // Derive room utilisation average
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
      <PageHeader title={`${greeting()}, ${userName} 👋`} description={new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}>
        <div className="flex gap-2">
          <Link to="/timetable/generate">
            <Button className="rounded-xl btn-press gap-2"><Zap className="h-4 w-4" />Generate</Button>
          </Link>
          <Link to="/export">
            <Button variant="outline" className="rounded-xl gap-2"><Download className="h-4 w-4" />Export</Button>
          </Link>
        </div>
      </PageHeader>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={BookOpen} value={stats.subject_count} label="Subjects" chipClass="chip-purple" />
        <MetricCard icon={Users} value={stats.faculty_count} label="Faculty" chipClass="chip-blue" />
        <MetricCard icon={BarChart3} value={stats.timetable_count} label="Timetables" chipClass="chip-green" />
        <MetricCard icon={Building2} value={stats.room_count} label="Rooms" chipClass="chip-orange" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-card rounded-lg shadow-sm p-5 overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-medium font-display">Faculty Workload</h3>
            <Select value={selectedDept || (departments[0]?.dept_id ?? "")} onValueChange={setSelectedDept}>
              <SelectTrigger className="w-[180px] h-9">
                <SelectValue placeholder="Select department" />
              </SelectTrigger>
              <SelectContent>
                {departments.map((dept) => (
                  <SelectItem key={dept.dept_id} value={dept.dept_id}>
                    {dept.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {workloadData.length > 0 ? (
            <div className="overflow-y-auto max-h-[600px] pr-2">
              <WorkloadChart data={workloadData} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No faculty data yet. Add faculty members to see workload.</p>
          )}
        </div>
        <div className="lg:col-span-2 bg-card rounded-lg shadow-sm p-5 overflow-hidden">
          <h3 className="text-base font-medium font-display mb-4">Room Utilization</h3>
          {roomUtilData.length > 0 ? (
            <RoomUtilizationChart data={roomUtilData} percentage={avgRoomUtil} />
          ) : (
            <p className="text-sm text-muted-foreground">No room data yet. Add rooms and generate a timetable.</p>
          )}
        </div>
      </div>
    </div>
  );
}
