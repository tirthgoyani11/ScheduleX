import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Faculty } from "@/types";
import { toast } from "sonner";

export function useFaculty() {
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<Faculty[]>({
    queryKey: ["faculty"],
    queryFn: () => api.get("/faculty"),
  });

  const createMutation = useMutation({
    mutationFn: (body: {
      name: string;
      employee_id: string;
      expertise?: string[];
      max_weekly_load?: number;
      preferred_time?: string;
      user_id?: string;
    }) => api.post<Faculty>("/faculty", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["faculty"] });
      toast.success("Faculty added");
    },
    onError: () => toast.error("Failed to add faculty"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; [key: string]: unknown }) =>
      api.put<Faculty>(`/faculty/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["faculty"] });
      toast.success("Faculty updated");
    },
    onError: () => toast.error("Failed to update faculty"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/faculty/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["faculty"] });
      toast.success("Faculty removed");
    },
    onError: () => toast.error("Failed to delete faculty"),
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
