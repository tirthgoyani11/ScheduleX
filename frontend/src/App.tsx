import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import LoginPage from "@/pages/Login";
import RegisterPage from "@/pages/Register";
import DashboardPage from "@/pages/Dashboard";
import HodDashboard from "@/pages/dashboards/HodDashboard";
import FacultyDashboard from "@/pages/dashboards/FacultyDashboard";
import UserManagementPage from "@/pages/admin/UserManagement";
import TimeSlotsPage from "@/pages/setup/TimeSlots";
import SubjectsPage from "@/pages/setup/Subjects";
import FacultyPage from "@/pages/setup/Faculty";
import RoomsPage from "@/pages/setup/Rooms";
import GeneratePage from "@/pages/timetable/Generate";
import TimetableListPage from "@/pages/timetable/List";
import TimetableViewPage from "@/pages/timetable/View";
import ConflictsPage from "@/pages/timetable/Conflicts";
import ExportPage from "@/pages/Export";
import SchedulingPage from "@/pages/Scheduling";
import ChatPage from "@/pages/Chat";
import SettingsPage from "@/pages/Settings";
import WhatsNewPage from "@/pages/WhatsNew";
import NotFound from "@/pages/NotFound";
import { RoleDashboard } from "@/components/layout/RoleDashboard";
import { RoleGuard } from "@/components/layout/RoleGuard";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          {/* Auth routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Dashboard routes */}
          <Route element={<DashboardLayout />}>
            <Route path="/" element={<RoleDashboard />} />
            <Route path="/dashboard/hod" element={<RoleGuard roles={["dept_admin"]}><HodDashboard /></RoleGuard>} />
            <Route path="/dashboard/faculty" element={<RoleGuard roles={["faculty"]}><FacultyDashboard /></RoleGuard>} />
            <Route path="/admin/users" element={<RoleGuard roles={["super_admin"]}><UserManagementPage /></RoleGuard>} />
            <Route path="/setup/time-slots" element={<RoleGuard roles={["super_admin", "dept_admin"]}><TimeSlotsPage /></RoleGuard>} />
            <Route path="/setup/subjects" element={<RoleGuard roles={["super_admin", "dept_admin"]}><SubjectsPage /></RoleGuard>} />
            <Route path="/setup/faculty" element={<RoleGuard roles={["super_admin", "dept_admin"]}><FacultyPage /></RoleGuard>} />
            <Route path="/setup/rooms" element={<RoleGuard roles={["super_admin", "dept_admin"]}><RoomsPage /></RoleGuard>} />
            <Route path="/timetable/generate" element={<RoleGuard roles={["super_admin", "dept_admin"]}><GeneratePage /></RoleGuard>} />
            <Route path="/timetable/list" element={<TimetableListPage />} />
            <Route path="/timetable/view/:id" element={<TimetableViewPage />} />
            <Route path="/timetable/conflicts/:id" element={<RoleGuard roles={["super_admin", "dept_admin"]}><ConflictsPage /></RoleGuard>} />
            <Route path="/timetable/conflicts" element={<RoleGuard roles={["super_admin", "dept_admin"]}><ConflictsPage /></RoleGuard>} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="/scheduling" element={<RoleGuard roles={["super_admin", "dept_admin", "faculty"]}><SchedulingPage /></RoleGuard>} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/settings" element={<RoleGuard roles={["super_admin"]}><SettingsPage /></RoleGuard>} />
            <Route path="/whats-new" element={<WhatsNewPage />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
