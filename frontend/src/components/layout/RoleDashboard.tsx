import { useAuthStore } from "@/store/useAuthStore";
import DashboardPage from "@/pages/Dashboard";
import HodDashboard from "@/pages/dashboards/HodDashboard";
import FacultyDashboard from "@/pages/dashboards/FacultyDashboard";

export function RoleDashboard() {
  const user = useAuthStore((s) => s.user);

  if (user?.role === "dept_admin") return <HodDashboard />;
  if (user?.role === "faculty") return <FacultyDashboard />;
  return <DashboardPage />;
}
