import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Batch } from "@/types";
import { toast } from "sonner";

export function useBatches(semester?: number) {
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<Batch[]>({
    queryKey: ["batches", semester],
    queryFn: () =>
      api.get("/batch", semester ? { semester } : undefined),
  });

  const createMutation = useMutation({
    mutationFn: (body: { semester: number; name: string; size?: number }) =>
      api.post<Batch>("/batch", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["batches"] });
      toast.success("Batch added");
    },
    onError: () => toast.error("Failed to add batch"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/batch/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["batches"] });
      toast.success("Batch removed");
    },
    onError: () => toast.error("Failed to delete batch"),
  });

  return {
    data,
    isLoading,
    create: createMutation.mutateAsync,
    remove: deleteMutation.mutateAsync,
  };
}
