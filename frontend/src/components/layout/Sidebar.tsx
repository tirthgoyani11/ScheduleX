import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Settings2, CalendarDays, Download, Building2, Sparkles,
  ChevronLeft, ChevronRight, ChevronDown, Clock, BookOpen, Users, DoorOpen,
  Zap, Eye, AlertTriangle, LogOut, Shield, UserCog, CalendarClock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";
import { StatusChip } from "@/components/common/StatusChip";
import type { UserRole } from "@/types";

interface NavItem {
  label: string;
  path: string;
  icon: React.ElementType;
  roles?: UserRole[];
  children?: { label: string; path: string; icon: React.ElementType; roles?: UserRole[] }[];
}

const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  {
    label: "Admin", path: "/admin", icon: Shield,
    roles: ["super_admin"],
    children: [
      { label: "User Management", path: "/admin/users", icon: UserCog, roles: ["super_admin"] },
    ],
  },
  {
    label: "Setup", path: "/setup", icon: Settings2,
    roles: ["super_admin", "dept_admin"],
    children: [
      { label: "Time Slots", path: "/setup/time-slots", icon: Clock, roles: ["super_admin", "dept_admin"] },
      { label: "Subjects", path: "/setup/subjects", icon: BookOpen, roles: ["super_admin", "dept_admin"] },
      { label: "Faculty", path: "/setup/faculty", icon: Users, roles: ["super_admin", "dept_admin"] },
      { label: "Rooms", path: "/setup/rooms", icon: DoorOpen, roles: ["super_admin", "dept_admin"] },
    ],
  },
  {
    label: "Timetable", path: "/timetable", icon: CalendarDays,
    children: [
      { label: "Generate", path: "/timetable/generate", icon: Zap, roles: ["super_admin", "dept_admin"] },
      { label: "View", path: "/timetable/list", icon: Eye },
      { label: "Conflicts", path: "/timetable/conflicts", icon: AlertTriangle, roles: ["super_admin", "dept_admin"] },
    ],
  },
  { label: "Export", path: "/export", icon: Download },
  { label: "Scheduling", path: "/scheduling", icon: CalendarClock, roles: ["super_admin", "dept_admin", "faculty"] },

];

const settingsItems: NavItem[] = [
  { label: "School Settings", path: "/settings", icon: Building2, roles: ["super_admin"] },
  { label: "What's New", path: "/whats-new", icon: Sparkles },
];

export function AppSidebar({ onCollapseChange }: { onCollapseChange?: (collapsed: boolean) => void }) {
  const [collapsed, setCollapsed] = useState(false);

  const handleCollapse = (val: boolean) => {
    setCollapsed(val);
    onCollapseChange?.(val);
  };
  const [expandedGroups, setExpandedGroups] = useState<string[]>(["Setup", "Timetable", "Admin"]);
  const location = useLocation();

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) =>
      prev.includes(label) ? prev.filter((g) => g !== label) : [...prev, label]
    );
  };

  const isActive = (path: string) => location.pathname === path;
  const isGroupActive = (item: NavItem) =>
    item.children?.some((c) => location.pathname.startsWith(c.path)) || location.pathname === item.path;

  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const hasRole = (roles?: UserRole[]) => !roles || !user?.role || roles.includes(user.role as UserRole);

  const filteredNavItems = navItems
    .filter((item) => hasRole(item.roles))
    .map((item) => ({
      ...item,
      children: item.children?.filter((child) => hasRole(child.roles)),
    }));

  const filteredSettingsItems = settingsItems.filter((item) => hasRole(item.roles));

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-screen bg-card border-r border-border flex flex-col z-30 transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <span className="text-primary-foreground font-display font-bold text-sm">X</span>
          </div>
          {!collapsed && <span className="font-display font-semibold text-base truncate">ScheduleX</span>}
        </div>
      </div>

      {/* Collapse button */}
      <button
        onClick={() => handleCollapse(!collapsed)}
        className="absolute -right-3 top-6 h-6 w-6 rounded-full bg-card border border-border flex items-center justify-center shadow-sm hover:bg-accent transition-colors"
      >
        {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
      </button>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {!collapsed && (
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground px-3 mb-2">Main Menu</p>
        )}
        <ul className="space-y-0.5">
          {filteredNavItems.map((item) => (
            <li key={item.label}>
              {item.children ? (
                <>
                  <button
                    onClick={() => toggleGroup(item.label)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-colors",
                      isGroupActive(item) ? "text-foreground font-medium" : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )}
                  >
                    <item.icon className="h-4.5 w-4.5 shrink-0" />
                    {!collapsed && (
                      <>
                        <span className="flex-1 text-left">{item.label}</span>
                        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expandedGroups.includes(item.label) && "rotate-180")} />
                      </>
                    )}
                  </button>
                  {!collapsed && expandedGroups.includes(item.label) && (
                    <ul className="ml-4 mt-0.5 space-y-0.5">
                      {item.children.map((child) => (
                        <li key={child.path}>
                          <Link
                            to={child.path}
                            className={cn(
                              "flex items-center gap-3 px-3 py-1.5 rounded-xl text-sm transition-colors",
                              isActive(child.path)
                                ? "bg-accent text-foreground font-medium border-l-2 border-primary"
                                : "text-muted-foreground hover:bg-accent hover:text-foreground"
                            )}
                          >
                            <child.icon className="h-4 w-4 shrink-0" />
                            <span>{child.label}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              ) : (
                <Link
                  to={item.path}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-colors",
                    isActive(item.path)
                      ? "bg-accent text-foreground font-medium border-l-2 border-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  <item.icon className="h-4.5 w-4.5 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              )}
            </li>
          ))}
        </ul>

        {!collapsed && filteredSettingsItems.length > 0 && (
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground px-3 mt-6 mb-2">Settings</p>
        )}
        <ul className="space-y-0.5">
          {filteredSettingsItems.map((item) => (
            <li key={item.label}>
              <Link
                to={item.path}
                className="flex items-center gap-3 px-3 py-2 rounded-xl text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <item.icon className="h-4.5 w-4.5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* User section */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
            <span className="text-primary-foreground text-xs font-semibold">
              {(user?.full_name || "U").split(" ").map((n) => n[0]).join("").slice(0, 2)}
            </span>
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{user?.full_name || "User"}</p>
              <StatusChip variant="draft" label={
                user?.role === "super_admin" ? "Super Admin" :
                user?.role === "dept_admin" ? "HOD" :
                user?.role === "faculty" ? "Faculty" :
                user?.role || "user"
              } />
            </div>
          )}
          <button onClick={handleLogout} className="p-1.5 rounded-lg hover:bg-accent transition-colors shrink-0" title="Logout">
            <LogOut className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    </aside>
  );
}
