import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { Room } from "@/types";
import { toast } from "sonner";

export function useRooms() {
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery<Room[]>({
    queryKey: ["rooms"],
    queryFn: () => api.get("/rooms"),
  });

  const createMutation = useMutation({
    mutationFn: (body: {
      name: string;
      capacity: number;
      room_type: string;
      has_projector?: boolean;
      has_computers?: boolean;
      has_ac?: boolean;
    }) => api.post<Room>("/rooms", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] });
      toast.success("Room added");
    },
    onError: () => toast.error("Failed to add room"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; [key: string]: unknown }) =>
      api.put<Room>(`/rooms/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] });
      toast.success("Room updated");
    },
    onError: () => toast.error("Failed to update room"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/rooms/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] });
      toast.success("Room removed");
    },
    onError: () => toast.error("Failed to delete room"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; [key: string]: unknown }) =>
      api.put<Room>(`/rooms/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] });
      toast.success("Room updated");
    },
    onError: () => toast.error("Failed to update room"),
  });

  return {
    data,
    isLoading,
    create: createMutation.mutateAsync,
    update: (id: string, body: Record<string, unknown>) => updateMutation.mutateAsync({ id, ...body }),
    remove: deleteMutation.mutateAsync,
  };
}
