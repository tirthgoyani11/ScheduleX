import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { FreeSlot, FreeSlotWithRooms, FreeRoom, FreeFaculty, SlotBooking, DateCheckResult } from "@/types";
import { toast } from "sonner";

export function useScheduling(timetableId?: string) {
  const qc = useQueryClient();

  // ── Free Slots for a faculty ──
  function useFreeSlots(facultyId: string | undefined, day?: string) {
    return useQuery<FreeSlot[]>({
      queryKey: ["free-slots", timetableId, facultyId, day],
      queryFn: () => {
        const params: Record<string, string> = { faculty_id: facultyId! };
        if (day) params.day = day;
        return api.get(`/scheduling/free-slots/${timetableId}`, params);
      },
      enabled: !!timetableId && !!facultyId,
    });
  }

  // ── Free Rooms at a day+period ──
  function useFreeRooms(day: string | undefined, period: number | undefined) {
    return useQuery<FreeRoom[]>({
      queryKey: ["free-rooms", timetableId, day, period],
      queryFn: () =>
        api.get(`/scheduling/free-rooms/${timetableId}`, { day: day!, period: period! }),
      enabled: !!timetableId && !!day && period != null,
    });
  }

  // ── Reschedule Options (free slots + rooms for an entry) ──
  function useRescheduleOptions(entryId: string | undefined, targetDate?: string) {
    return useQuery<FreeSlotWithRooms[]>({
      queryKey: ["reschedule-options", timetableId, entryId, targetDate],
      queryFn: () => {
        const params: Record<string, string> = { entry_id: entryId! };
        if (targetDate) params.target_date = targetDate;
        return api.get(`/scheduling/reschedule-options/${timetableId}`, params);
      },
      enabled: !!timetableId && !!entryId,
    });
  }

  // ── Date-specific availability check ──
  function useDateCheck(date: string | undefined) {
    return useQuery<DateCheckResult>({
      queryKey: ["date-check", date],
      queryFn: () => api.get("/scheduling/date-check", { date: date! }),
      enabled: !!date,
    });
  }

  // ── Free Faculty at a day+period (optionally date-aware) ──
  function useFreeFaculty(day: string | undefined, period: number | undefined, targetDate?: string) {
    return useQuery<FreeFaculty[]>({
      queryKey: ["free-faculty", timetableId, day, period, targetDate],
      queryFn: () => {
        const params: Record<string, string | number> = { day: day!, period: period! };
        if (targetDate) params.target_date = targetDate;
        return api.get(`/scheduling/free-faculty/${timetableId}`, params);
      },
      enabled: !!timetableId && !!day && period != null,
    });
  }

  // ── Bookings list ──
  function useBookings(bookingType?: string, status?: string) {
    return useQuery<SlotBooking[]>({
      queryKey: ["slot-bookings", bookingType, status],
      queryFn: () => {
        const params: Record<string, string> = {};
        if (bookingType) params.booking_type = bookingType;
        if (status) params.status = status;
        return api.get("/scheduling/bookings", params);
      },
    });
  }

  // ── Mutations ──

  const rescheduleMutation = useMutation({
    mutationFn: (body: {
      original_entry_id: string;
      new_day: string;
      new_period: number;
      new_room_id: string;
      target_date?: string;
      reason?: string;
    }) => api.post<SlotBooking>("/scheduling/reschedule", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      qc.invalidateQueries({ queryKey: ["free-slots"] });
      qc.invalidateQueries({ queryKey: ["free-rooms"] });
      toast.success("Reschedule request created");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to reschedule"),
  });

  const extraLectureMutation = useMutation({
    mutationFn: (body: {
      subject_id: string;
      day: string;
      period: number;
      room_id: string;
      target_date?: string;
      reason?: string;
    }) => api.post<SlotBooking>("/scheduling/extra-lecture", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      qc.invalidateQueries({ queryKey: ["free-slots"] });
      qc.invalidateQueries({ queryKey: ["free-rooms"] });
      toast.success("Extra lecture request submitted");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to request extra lecture"),
  });

  const extraLectureAssignMutation = useMutation({
    mutationFn: ({
      faculty_id,
      ...body
    }: {
      faculty_id: string;
      subject_id: string;
      day: string;
      period: number;
      room_id: string;
      target_date?: string;
      reason?: string;
    }) =>
      api.post<SlotBooking>(
        `/scheduling/extra-lecture-assign?faculty_id=${encodeURIComponent(faculty_id)}`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      qc.invalidateQueries({ queryKey: ["free-slots"] });
      qc.invalidateQueries({ queryKey: ["free-rooms"] });
      toast.success("Extra lecture assigned");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to assign extra lecture"),
  });

  const proxyMutation = useMutation({
    mutationFn: (body: {
      original_entry_id: string;
      proxy_faculty_id: string;
      target_date: string;
      reason?: string;
    }) => api.post<SlotBooking>("/scheduling/proxy", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      qc.invalidateQueries({ queryKey: ["free-faculty"] });
      toast.success("Proxy assigned successfully");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to assign proxy"),
  });

  const approveMutation = useMutation({
    mutationFn: (bookingId: string) =>
      api.post<SlotBooking>(`/scheduling/approve/${bookingId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      toast.success("Booking approved");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to approve"),
  });

  const rejectMutation = useMutation({
    mutationFn: (bookingId: string) =>
      api.post<SlotBooking>(`/scheduling/reject/${bookingId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      toast.success("Booking rejected");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to reject"),
  });

  const cancelMutation = useMutation({
    mutationFn: (bookingId: string) =>
      api.post<SlotBooking>(`/scheduling/cancel/${bookingId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["slot-bookings"] });
      toast.success("Booking cancelled");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail || "Failed to cancel"),
  });

  return {
    useFreeSlots,
    useFreeRooms,
    useRescheduleOptions,
    useFreeFaculty,
    useBookings,
    useDateCheck,
    rescheduleMutation,
    extraLectureMutation,
    extraLectureAssignMutation,
    proxyMutation,
    approveMutation,
    rejectMutation,
    cancelMutation,
  };
}
