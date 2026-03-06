import { BookOpen, CalendarDays, Clock, BarChart3 } from "lucide-react";
import { MetricCard } from "@/components/common/MetricCard";
import { PageHeader } from "@/components/common/PageHeader";
import { useAuthStore } from "@/store/useAuthStore";
import { useFaculty } from "@/hooks/useFaculty";
import { useDashboard } from "@/hooks/useDashboard";
import { DashboardSkeleton } from "@/components/skeletons/PageSkeletons";

const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
};

export default function FacultyDashboard() {
  const user = useAuthStore((s) => s.user);
  const { data: facultyList, isLoading: facLoading } = useFaculty();
  const { facultyLoad, isLoading: dashLoading } = useDashboard();

  const isLoading = facLoading || dashLoading;
  if (isLoading) return <DashboardSkeleton />;

  const userName = user?.full_name?.split(" ")[0] ?? "Faculty";

  // Find own faculty profile
  const myProfile = facultyList.length > 0 ? facultyList[0] : null;
  const myLoad = facultyLoad.find((f) => f.faculty_id === myProfile?.faculty_id);

  const assignedPeriods = myLoad?.assigned_periods ?? 0;
  const maxLoad = myProfile?.max_weekly_load ?? myLoad?.max_weekly_load ?? 18;
  const utilPct = maxLoad > 0 ? Math.round((assignedPeriods / maxLoad) * 100) : 0;
  const freeSlots = Math.max(0, maxLoad - assignedPeriods);

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${greeting()}, ${userName} 👋`}
        description="Your personal teaching dashboard"
      />

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={CalendarDays} value={assignedPeriods} label="Assigned Periods" chipClass="chip-blue" />
        <MetricCard icon={Clock} value={freeSlots} label="Free Slots" chipClass="chip-green" />
        <MetricCard icon={BarChart3} value={`${utilPct}%`} label="Workload Utilization" chipClass="chip-purple" />
        <MetricCard icon={BookOpen} value={myProfile?.expertise?.length ?? 0} label="Expertise Areas" chipClass="chip-orange" />
      </div>

      {/* Profile Info */}
      {myProfile && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Profile Card */}
          <div className="bg-card rounded-xl shadow-sm p-6">
            <h3 className="text-base font-medium font-display mb-4">My Profile</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center shrink-0">
                  <span className="text-primary-foreground text-sm font-semibold">
                    {myProfile.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                  </span>
                </div>
                <div>
                  <p className="font-medium text-lg">{myProfile.name}</p>
                  <p className="text-sm font-mono text-muted-foreground">{myProfile.employee_id}</p>
                </div>
              </div>
              <div className="border-t border-border pt-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Max Weekly Load</span>
                  <span className="font-medium">{myProfile.max_weekly_load} periods</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Preferred Time</span>
                  <span className="font-medium capitalize">{myProfile.preferred_time || "Any"}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Substitutions</span>
                  <span className="font-medium">{myProfile.substitution_count}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Expertise & Workload */}
          <div className="bg-card rounded-xl shadow-sm p-6">
            <h3 className="text-base font-medium font-display mb-4">Expertise & Workload</h3>
            {myProfile.expertise && myProfile.expertise.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-muted-foreground mb-2">Areas of Expertise</p>
                <div className="flex flex-wrap gap-2">
                  {myProfile.expertise.map((e) => (
                    <span key={e} className="chip chip-blue">{e}</span>
                  ))}
                </div>
              </div>
            )}
            <div className="border-t border-border pt-4">
              <p className="text-xs text-muted-foreground mb-3">Weekly Load</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Assigned</span>
                  <span className="font-medium">{assignedPeriods} / {maxLoad} periods</span>
                </div>
                <div className="w-full bg-muted rounded-full h-3">
                  <div
                    className="h-3 rounded-full transition-all"
                    style={{
                      width: `${Math.min(utilPct, 100)}%`,
                      backgroundColor: utilPct > 90 ? "hsl(0,72%,51%)" : utilPct > 70 ? "hsl(27,96%,48%)" : "hsl(142,64%,24%)",
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {utilPct > 90 ? "Near capacity — consider reducing load" :
                   utilPct > 70 ? "Healthy workload" :
                   "Capacity available for more assignments"}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {!myProfile && (
        <div className="bg-card rounded-xl shadow-sm p-8 text-center">
          <p className="text-muted-foreground">No faculty profile found. Please contact your department admin to set up your profile.</p>
        </div>
      )}
    </div>
  );
}
