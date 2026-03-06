import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import LoginPage from "@/pages/Login";
import RegisterPage from "@/pages/Register";
import DashboardPage from "@/pages/Dashboard";
import TimeSlotsPage from "@/pages/setup/TimeSlots";
import SubjectsPage from "@/pages/setup/Subjects";
import FacultyPage from "@/pages/setup/Faculty";
import RoomsPage from "@/pages/setup/Rooms";
import GeneratePage from "@/pages/timetable/Generate";
import TimetableListPage from "@/pages/timetable/List";
import TimetableViewPage from "@/pages/timetable/View";
import ConflictsPage from "@/pages/timetable/Conflicts";
import ExportPage from "@/pages/Export";
import SettingsPage from "@/pages/Settings";
import WhatsNewPage from "@/pages/WhatsNew";
import NotFound from "@/pages/NotFound";

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
            <Route path="/" element={<DashboardPage />} />
            <Route path="/setup/time-slots" element={<TimeSlotsPage />} />
            <Route path="/setup/subjects" element={<SubjectsPage />} />
            <Route path="/setup/faculty" element={<FacultyPage />} />
            <Route path="/setup/rooms" element={<RoomsPage />} />
            <Route path="/timetable/generate" element={<GeneratePage />} />
            <Route path="/timetable/list" element={<TimetableListPage />} />
            <Route path="/timetable/view/:id" element={<TimetableViewPage />} />
            <Route path="/timetable/conflicts/:id" element={<ConflictsPage />} />
            <Route path="/timetable/conflicts" element={<ConflictsPage />} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/whats-new" element={<WhatsNewPage />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
