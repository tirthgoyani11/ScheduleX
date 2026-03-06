import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Subject } from "@/types";
import { toast } from "sonner";

export function useSubjects(semester?: number, deptId?: string) {
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<Subject[]>({
    queryKey: ["subjects", semester, deptId],
    queryFn: () => {
      const params: Record<string, unknown> = {};
      if (semester) params.semester = semester;
      if (deptId) params.dept_id = deptId;
      return api.get("/subjects", Object.keys(params).length ? params : undefined);
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: {
      name: string;
      subject_code: string;
      semester: number;
      credits: number;
      weekly_periods: number;
      needs_lab?: boolean;
      batch_size?: number;
      batch?: string;
    }) => api.post<Subject>("/subjects", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subjects"] });
      toast.success("Subject added");
    },
    onError: () => toast.error("Failed to add subject"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; [key: string]: unknown }) =>
      api.put<Subject>(`/subjects/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subjects"] });
      toast.success("Subject updated");
    },
    onError: () => toast.error("Failed to update subject"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/subjects/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subjects"] });
      toast.success("Subject removed");
    },
    onError: () => toast.error("Failed to delete subject"),
  });

  return {
    data,
    isLoading,
    error: null,
    create: createMutation.mutateAsync,
    update: (id: string, body: Record<string, unknown>) => updateMutation.mutateAsync({ id, ...body }),
    remove: deleteMutation.mutateAsync,
  };
}
