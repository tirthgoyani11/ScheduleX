import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TimeSlot } from "@/types";

const timeSlotSchema = z.object({
  label: z.string().min(1, "Label is required"),
  start_time: z.string().min(1, "Start time is required"),
  end_time: z.string().min(1, "End time is required"),
  slot_type: z.enum(["lecture", "lab", "break"]),
});

type TimeSlotFormData = z.infer<typeof timeSlotSchema>;

interface TimeSlotFormProps {
  initialData?: TimeSlot;
  onSubmit: (data: Omit<TimeSlot, "slot_id" | "college_id">) => Promise<void>;
  onCancel?: () => void;
  isLoading?: boolean;
}

export function TimeSlotForm({ initialData, onSubmit, onCancel, isLoading }: TimeSlotFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<TimeSlotFormData>({
    resolver: zodResolver(timeSlotSchema),
    defaultValues: {
      label: initialData?.label || "",
      start_time: initialData?.start_time || "09:00",
      end_time: initialData?.end_time || "10:00",
      slot_type: initialData?.slot_type || "lecture",
    },
  });

  const selectedType = watch("slot_type");
  const start_time = watch("start_time");
  const end_time = watch("end_time");

  const getDuration = (): number => {
    const [sh, sm] = start_time.split(":").map(Number);
    const [eh, em] = end_time.split(":").map(Number);
    return (eh - sh) * 60 + (em - sm);
  };

  const handleFormSubmit = (data: TimeSlotFormData) => {
    onSubmit({
      label: data.label,
      start_time: data.start_time,
      end_time: data.end_time,
      slot_type: data.slot_type,
      slot_order: initialData?.slot_order || 0,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label>Label</Label>
        <Input className="rounded-xl" placeholder="Period 1" {...register("label")} />
        {errors.label && <p className="text-xs text-destructive">{errors.label.message}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label>Start Time</Label>
          <Input type="time" className="rounded-xl" {...register("start_time")} />
        </div>
        <div className="space-y-2">
          <Label>End Time</Label>
          <Input type="time" className="rounded-xl" {...register("end_time")} />
        </div>
      </div>
      {start_time && end_time && (
        <p className="text-xs text-muted-foreground">{getDuration()} minutes</p>
      )}
      <div className="space-y-2">
        <Label>Type</Label>
        <div className="grid grid-cols-3 gap-3">
          {(["lecture", "lab", "break"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setValue("slot_type", t)}
              className={`p-3 rounded-xl border-2 text-sm font-medium transition-all ${
                selectedType === t ? "border-primary bg-accent" : "border-border hover:border-border-strong"
              }`}
            >
              {t === "lecture" ? "📚 Lecture" : t === "lab" ? "🔬 Lab" : "☕ Break"}
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} className="rounded-xl flex-1">
            Cancel
          </Button>
        )}
        <Button type="submit" className="rounded-xl btn-press flex-1" disabled={isLoading}>
          {isLoading ? "Saving..." : initialData ? "Update Slot" : "Add Slot"}
        </Button>
      </div>
    </form>
  );
}
