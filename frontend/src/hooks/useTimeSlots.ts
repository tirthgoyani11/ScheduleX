import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { TimeSlot } from "@/types";
import { DEFAULT_TIME_SLOTS } from "@/types";
import api from "@/lib/api";

/**
 * Fetches time slots from the backend API.
 * Falls back to DEFAULT_TIME_SLOTS while loading or on error.
 */
export function useTimeSlots() {
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<TimeSlot[]>({
    queryKey: ["timeslots"],
    queryFn: async () => {
      const res = await api.get("/timeslots");
      return res.data;
    },
  });

  const createSlot = useMutation({
    mutationFn: (body: Omit<TimeSlot, "slot_id" | "college_id">) =>
      api.post("/timeslots", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timeslots"] }),
  });

  const updateSlot = useMutation({
    mutationFn: ({ slot_id, ...body }: Partial<TimeSlot> & { slot_id: string }) =>
      api.put(`/timeslots/${slot_id}`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timeslots"] }),
  });

  const deleteSlot = useMutation({
    mutationFn: (slot_id: string) =>
      api.delete(`/timeslots/${slot_id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timeslots"] }),
  });

  const reorderSlots = useMutation({
    mutationFn: (slot_ids: string[]) =>
      api.put("/timeslots/reorder/bulk", { slot_ids }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timeslots"] }),
  });

  const seedDefaults = useMutation({
    mutationFn: () =>
      api.post("/timeslots/seed-defaults").then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timeslots"] }),
  });

  return {
    data: data ?? DEFAULT_TIME_SLOTS,
    isLoading,
    error,
    createSlot,
    updateSlot,
    deleteSlot,
    reorderSlots,
    seedDefaults,
  };
}
