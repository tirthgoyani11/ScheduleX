import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Department } from "@/types";
import { useAuthStore } from "@/store/useAuthStore";

export function useDepartments() {
  const user = useAuthStore((s) => s.user);
  const collegeId = user?.college_id;

  const { data = [], isLoading } = useQuery<Department[]>({
    queryKey: ["departments", collegeId],
    queryFn: () => api.get(`/colleges/${collegeId}/departments`),
    enabled: !!collegeId,
  });

  return { data, isLoading };
}
