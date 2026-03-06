import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { useState } from "react";

const facultySchema = z.object({
  name: z.string().min(1, "Name is required"),
  employeeId: z.string().min(1, "Employee ID is required"),
  email: z.string().email("Invalid email"),
});

type FacultyFormData = z.infer<typeof facultySchema>;

interface FacultyFormProps {
  onSubmit: (data: FacultyFormData & { maxWeeklyHours: number; isShared: boolean; subjectIds: string[] }) => Promise<void>;
  onCancel?: () => void;
  isLoading?: boolean;
}

export function FacultyForm({ onSubmit, onCancel, isLoading }: FacultyFormProps) {
  const [maxHours, setMaxHours] = useState(20);
  const [isShared, setIsShared] = useState(false);
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FacultyFormData>({
    resolver: zodResolver(facultySchema),
  });

  const handleFormSubmit = (data: FacultyFormData) => {
    onSubmit({
      ...data,
      maxWeeklyHours: maxHours,
      isShared,
      subjectIds: selectedSubjects,
    });
  };

  const toggleSubject = (id: string) => {
    setSelectedSubjects((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  // Group subjects by semester (placeholder — form not currently used)
  const subjects: { id: string; name: string; code: string; semester: number }[] = [];
  const semesters = [...new Set(subjects.map((s) => s.semester))].sort();

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label>Full Name</Label>
        <Input className="rounded-xl" placeholder="Dr. John Doe" {...register("name")} />
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>
      <div className="space-y-2">
        <Label>Employee ID</Label>
        <Input className="rounded-xl font-mono" placeholder="EMP007" {...register("employeeId")} />
        {errors.employeeId && <p className="text-xs text-destructive">{errors.employeeId.message}</p>}
      </div>
      <div className="space-y-2">
        <Label>Email</Label>
        <Input type="email" className="rounded-xl" placeholder="john@gcet.edu" {...register("email")} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>
      <div className="space-y-2">
        <Label>Max Weekly Hours</Label>
        <Slider
          value={[maxHours]}
          onValueChange={(v) => setMaxHours(v[0])}
          min={10}
          max={40}
          step={1}
          className="mt-2"
        />
        <p className="text-xs text-muted-foreground">{maxHours} hours / week</p>
      </div>
      <div className="flex items-center justify-between">
        <div>
          <Label>Shared Faculty</Label>
          {isShared && (
            <p className="text-xs text-muted-foreground mt-0.5">
              This faculty can be assigned across departments
            </p>
          )}
        </div>
        <Switch checked={isShared} onCheckedChange={setIsShared} />
      </div>
      <div className="space-y-2">
        <Label>Teachable Subjects</Label>
        <div className="max-h-48 overflow-y-auto space-y-3 border border-border rounded-xl p-3">
          {semesters.map((sem) => (
            <div key={sem}>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1.5">
                Semester {sem}
              </p>
              <div className="space-y-1">
                {subjects
                  .filter((s) => s.semester === sem)
                  .map((sub) => (
                    <label key={sub.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-accent/50 rounded-lg px-2 py-1 transition-colors">
                      <Checkbox
                        checked={selectedSubjects.includes(sub.id)}
                        onCheckedChange={() => toggleSubject(sub.id)}
                      />
                      <span>{sub.name}</span>
                      <span className="text-xs font-mono text-muted-foreground ml-auto">{sub.code}</span>
                    </label>
                  ))}
              </div>
            </div>
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
          {isLoading ? "Saving..." : "Add Faculty"}
        </Button>
      </div>
    </form>
  );
}
