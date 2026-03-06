import { useState } from "react";
import type { TimeSlot } from "@/types";
import { DEFAULT_TIME_SLOTS } from "@/types";

/**
 * Time slots are display-only metadata.
 * The backend uses integer periods (1-8).
 * This hook manages the local time slot display config.
 */
export function useTimeSlots() {
  const [data] = useState<TimeSlot[]>(DEFAULT_TIME_SLOTS);

  return {
    data,
    isLoading: false,
    error: null,
  };
}
