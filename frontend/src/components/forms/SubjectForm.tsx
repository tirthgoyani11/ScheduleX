import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { SubjectType } from "@/types";

const subjectSchema = z.object({
  name: z.string().min(1, "Name is required"),
  code: z.string().min(1, "Code is required"),
  credits: z.number().min(1).max(6),
  weeklyFrequency: z.number().min(1).max(6),
  type: z.enum(["THEORY", "LAB", "THEORY_LAB"]),
  batches: z.number().min(0).max(4),
});

type SubjectFormData = z.infer<typeof subjectSchema>;

interface SubjectFormProps {
  semester: number;
  onSubmit: (data: SubjectFormData & { semester: number; slotSize: 1 | 2; batchLabels: string[]; assignedFacultyIds: string[] }) => Promise<void>;
  onCancel?: () => void;
  isLoading?: boolean;
}

export function SubjectForm({ semester, onSubmit, onCancel, isLoading }: SubjectFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    formState: { errors },
  } = useForm<SubjectFormData>({
    resolver: zodResolver(subjectSchema),
    defaultValues: {
      name: "",
      code: "",
      credits: 3,
      weeklyFrequency: 3,
      type: "THEORY",
      batches: 0,
    },
  });

  const selectedType = watch("type");
  const batchCount = watch("batches");

  const handleFormSubmit = (data: SubjectFormData) => {
    const batchLabels = Array.from({ length: data.batches }, (_, i) => `Batch ${String.fromCharCode(65 + i)}`);
    onSubmit({
      ...data,
      semester,
      slotSize: data.type === "LAB" ? 2 : 1,
      batchLabels,
      assignedFacultyIds: [],
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label>Subject Name</Label>
        <Input className="rounded-xl" placeholder="Data Structures" {...register("name")} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>
      <div className="space-y-2">
        <Label>Subject Code</Label>
        <Input className="rounded-xl font-mono" placeholder="DSA301" {...register("code")} />
        {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label>Credits</Label>
          <Input type="number" className="rounded-xl" {...register("credits", { valueAsNumber: true })} min={1} max={6} />
        </div>
        <div className="space-y-2">
          <Label>Freq/week</Label>
          <Input type="number" className="rounded-xl" {...register("weeklyFrequency", { valueAsNumber: true })} min={1} max={6} />
        </div>
      </div>
      <div className="space-y-2">
        <Label>Type</Label>
        <div className="grid grid-cols-3 gap-2">
          {([["THEORY", "📚 Theory"], ["LAB", "🔬 Lab"], ["THEORY_LAB", "📚+🔬 Both"]] as const).map(([val, lbl]) => (
            <button
              key={val}
              type="button"
              onClick={() => {
                setValue("type", val as SubjectType);
                if (val === "THEORY") setValue("batches", 0);
              }}
              className={`p-2.5 rounded-xl border-2 text-xs font-medium transition-all ${
                selectedType === val ? "border-primary bg-accent" : "border-border hover:border-border-strong"
              }`}
            >
              {lbl}
            </button>
          ))}
        </div>
      </div>
      {selectedType !== "THEORY" && (
        <div className="space-y-2">
          <Label>Batches</Label>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="rounded-xl h-8 w-8"
              onClick={() => setValue("batches", Math.max(0, batchCount - 1))}
            >
              −
            </Button>
            <span className="font-mono font-medium w-8 text-center">{batchCount}</span>
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="rounded-xl h-8 w-8"
              onClick={() => setValue("batches", Math.min(4, batchCount + 1))}
            >
              +
            </Button>
          </div>
          {batchCount > 0 && (
            <p className="text-xs text-muted-foreground">
              {Array.from({ length: batchCount }, (_, i) => `Batch ${String.fromCharCode(65 + i)}`).join(", ")}
            </p>
          )}
        </div>
      )}
      <div className="flex gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} className="rounded-xl flex-1">
            Cancel
          </Button>
        )}
        <Button type="submit" className="rounded-xl btn-press flex-1" disabled={isLoading}>
          {isLoading ? "Saving..." : "Add Subject"}
        </Button>
      </div>
    </form>
  );
}
