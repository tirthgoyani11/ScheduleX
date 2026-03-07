import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Timetable, JobResponse, GenerateAllResponse } from "@/types";
import { toast } from "sonner";

export function useTimetable(timetableId?: string, deptId?: string) {
  const qc = useQueryClient();

  // Fetch list of timetables
  const listQuery = useQuery<Timetable[]>({
    queryKey: ["timetables", deptId],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (deptId) params.dept_id = deptId;
      return api.get("/timetable", params);
    },
    enabled: !timetableId,
  });

  // Fetch single timetable — poll while DRAFT with no entries (still generating)
  const singleQuery = useQuery<Timetable>({
    queryKey: ["timetable", timetableId],
    queryFn: () => api.get(`/timetable/${timetableId}`),
    enabled: !!timetableId,
    refetchInterval: (query) => {
      const tt = query.state.data;
      if (!tt) return false;
      const isDraft = tt.status === "DRAFT" || tt.status === "draft";
      const isEmpty = !tt.entries || tt.entries.length === 0;
      // Poll every 2s while timetable is still being generated
      return isDraft && isEmpty ? 2000 : false;
    },
  });

  const generateMutation = useMutation({
    mutationFn: (body: {
      semester: number;
      academic_year: string;
      faculty_subject_map: Record<string, string[]>;
      working_days?: string[];
      time_limit_seconds?: number;
    }) => api.post<JobResponse>("/timetable/generate", body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["timetables"] });
      toast.success(`Timetable generated (${data.status})`);
    },
    onError: () => toast.error("Failed to generate timetable"),
  });

  const generateAllMutation = useMutation({
    mutationFn: (body: {
      academic_year: string;
      working_days?: string[];
      time_limit_seconds?: number;
    }) => api.post<GenerateAllResponse>("/timetable/generate-all", body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["timetables"] });
      toast.success(`Generated ${data.succeeded}/${data.total} semesters`);
    },
    onError: () => toast.error("Failed to generate all timetables"),
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => api.post(`/timetable/${id}/publish`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["timetables"] });
      qc.invalidateQueries({ queryKey: ["timetable"] });
      toast.success("Timetable published");
    },
    onError: () => toast.error("Failed to publish"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/timetable/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["timetables"] });
      toast.success("Timetable deleted");
    },
    onError: () => toast.error("Failed to delete"),
  });

  return {
    // List
    data: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    // Single
    timetable: singleQuery.data ?? null,
    timetableLoading: singleQuery.isLoading,
    // Mutations
    generate: generateMutation.mutateAsync,
    isGenerating: generateMutation.isPending,
    generateAll: generateAllMutation.mutateAsync,
    isGeneratingAll: generateAllMutation.isPending,
    publish: publishMutation.mutateAsync,
    remove: deleteMutation.mutateAsync,
    error: null,
  };
}
