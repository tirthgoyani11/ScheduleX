import { useLocation, Link } from "react-router-dom";
import { Search, Bell, MessageSquare, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/useAuthStore";

const routeLabels: Record<string, string> = {
  "/": "Dashboard",
  "/setup/time-slots": "Time Slots",
  "/setup/subjects": "Subjects",
  "/setup/faculty": "Faculty",
  "/timetable/generate": "Generate",
  "/export": "Export",
};

export function Topbar() {
  const location = useLocation();
  const { user } = useAuthStore();

  const getLabel = () => {
    if (location.pathname.startsWith("/timetable/view")) return "View Timetable";
    if (location.pathname.startsWith("/timetable/conflicts")) return "Conflicts";
    return routeLabels[location.pathname] || "Page";
  };

  const segments = location.pathname.split("/").filter(Boolean);
  const breadcrumbs = [
    { label: "ScheduleX", path: "/" },
    { label: "CE", path: "/" },
    ...segments.map((seg, i) => ({
      label: seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, " "),
      path: "/" + segments.slice(0, i + 1).join("/"),
    })),
  ];

  return (
    <header className="h-14 bg-card border-b border-border flex items-center justify-between px-6 shrink-0">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <span key={`${i}-${crumb.path}`} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-muted-foreground">›</span>}
            {i === breadcrumbs.length - 1 ? (
              <span className="font-medium text-foreground">{crumb.label}</span>
            ) : (
              <Link to={crumb.path} className="text-muted-foreground hover:text-foreground transition-colors">
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>

      {/* Right actions */}
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="rounded-xl">
          <Search className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="rounded-xl relative">
          <MessageSquare className="h-4 w-4" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
        </Button>
        <Button variant="ghost" size="icon" className="rounded-xl relative">
          <Bell className="h-4 w-4" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
        </Button>
        {user?.role === "super_admin" && (
          <Button variant="ghost" className="rounded-xl text-sm gap-1.5 ml-2">
            CE
            <ChevronDown className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </header>
  );
}
