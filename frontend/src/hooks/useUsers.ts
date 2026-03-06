import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { User } from "@/types";
import { toast } from "sonner";

export function useUsers(role?: string) {
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<User[]>({
    queryKey: ["users", role],
    queryFn: () => api.get("/auth/users", role ? { role } : undefined),
  });

  const createMutation = useMutation({
    mutationFn: (body: {
      email: string;
      password: string;
      full_name: string;
      role: string;
      college_id?: string;
      dept_id?: string;
      phone?: string;
    }) => api.post<User>("/auth/register", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User created");
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || "Failed to create user");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; [key: string]: unknown }) =>
      api.put<User>(`/auth/users/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User updated");
    },
    onError: () => toast.error("Failed to update user"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/users/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User removed");
    },
    onError: () => toast.error("Failed to remove user"),
  });

  return {
    data,
    isLoading,
    create: createMutation.mutateAsync,
    update: (id: string, body: Record<string, unknown>) => updateMutation.mutateAsync({ id, ...body }),
    remove: deleteMutation.mutateAsync,
  };
}
