import { useState, useEffect } from "react";
import { Outlet, Navigate } from "react-router-dom";
import { AppSidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { useAuthStore } from "@/store/useAuthStore";
import { Loader2 } from "lucide-react";

export function DashboardLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { isAuthenticated, user, hydrate } = useAuthStore();
  const [hydrating, setHydrating] = useState(true);

  useEffect(() => {
    hydrate().finally(() => setHydrating(false));
  }, [hydrate]);

  if (hydrating) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex w-full">
      <AppSidebar onCollapseChange={setSidebarCollapsed} />
      <div
        className="flex-1 flex flex-col transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
        style={{ marginLeft: sidebarCollapsed ? 64 : 240 }}
      >
        <Topbar />
        <main className="flex-1 p-6 page-enter">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
