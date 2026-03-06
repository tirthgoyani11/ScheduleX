import { Clock, GripVertical } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusChip, getSlotChipVariant } from "@/components/common/StatusChip";
import { useTimeSlots } from "@/hooks/useTimeSlots";

export default function TimeSlotsPage() {
  const { data: slots } = useTimeSlots();

  return (
    <div className="space-y-6">
      <PageHeader title="Time Slots" description="Standard class periods used for timetable generation" />

      {/* Info banner */}
      <div className="chip-blue rounded-xl p-3 text-sm">
        These are the standard periods used by the solver. Lectures = 1 period, Labs = 2 consecutive periods.
      </div>

      <div className="space-y-2">
        {slots.map((slot) => (
          <div key={slot.period} className="bg-card rounded-xl shadow-sm p-4 flex items-center gap-4 hover:bg-accent/50 transition-colors">
            <GripVertical className="h-4 w-4 text-muted-foreground" />
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="font-mono text-sm font-medium">
              {slot.startTime} → {slot.endTime}
            </span>
            <StatusChip variant={getSlotChipVariant(slot.type)} label={slot.type} />
            <span className="text-sm text-muted-foreground flex-1">"{slot.label}"</span>
            <span className="text-xs font-mono text-muted-foreground">Period {slot.period}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
