import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { DashboardStats, FacultyLoad, RoomUtilisation } from "@/types";

export function useDashboard() {
  const statsQuery = useQuery<DashboardStats>({
    queryKey: ["analytics", "dashboard"],
    queryFn: () => api.get("/analytics/dashboard"),
  });

  const facultyLoadQuery = useQuery<FacultyLoad[]>({
    queryKey: ["analytics", "faculty-load"],
    queryFn: () => api.get("/analytics/faculty-load"),
  });

  const roomUtilQuery = useQuery<RoomUtilisation[]>({
    queryKey: ["analytics", "room-utilisation"],
    queryFn: () => api.get("/analytics/room-utilisation"),
  });

  return {
    stats: statsQuery.data ?? { faculty_count: 0, timetable_count: 0, subject_count: 0, room_count: 0 },
    facultyLoad: facultyLoadQuery.data ?? [],
    roomUtilisation: roomUtilQuery.data ?? [],
    isLoading: statsQuery.isLoading || facultyLoadQuery.isLoading || roomUtilQuery.isLoading,
  };
}
