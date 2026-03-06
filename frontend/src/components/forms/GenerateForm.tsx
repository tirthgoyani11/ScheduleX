import { useState } from "react";
import { X, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const allDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

interface GenerateFormProps {
  semester: number;
  divisions: string[];
  workingDays: string[];
  onSemesterChange: (s: number) => void;
  onDivisionsChange: (d: string[]) => void;
  onWorkingDaysChange: (d: string[]) => void;
  onNext: () => void;
}

export function GenerateForm({
  semester,
  divisions,
  workingDays,
  onSemesterChange,
  onDivisionsChange,
  onWorkingDaysChange,
  onNext,
}: GenerateFormProps) {
  const [newDivision, setNewDivision] = useState("");

  return (
    <div className="bg-card rounded-lg shadow-sm p-6 space-y-5 max-w-xl">
      <div className="space-y-2">
        <Label>Semester</Label>
        <Select value={String(semester)} onValueChange={(v) => onSemesterChange(Number(v))}>
          <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
          <SelectContent>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
              <SelectItem key={s} value={String(s)}>Semester {s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Divisions</Label>
        <div className="flex flex-wrap gap-2">
          {divisions.map((d) => (
            <span key={d} className="chip chip-blue gap-1">
              Div {d}
              <button onClick={() => onDivisionsChange(divisions.filter((x) => x !== d))}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <div className="flex gap-1.5">
            <Input
              className="rounded-xl h-7 w-16 text-xs"
              value={newDivision}
              onChange={(e) => setNewDivision(e.target.value)}
              placeholder="B"
            />
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl h-7 text-xs"
              onClick={() => {
                if (newDivision) {
                  onDivisionsChange([...divisions, newDivision]);
                  setNewDivision("");
                }
              }}
            >
              +
            </Button>
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <Label>Academic Year</Label>
        <Input className="rounded-xl" defaultValue="2025-26" />
      </div>
      <div className="space-y-2">
        <Label>Working Days</Label>
        <div className="flex flex-wrap gap-2">
          {allDays.map((day) => (
            <label key={day} className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={workingDays.includes(day)}
                onCheckedChange={(checked) => {
                  if (checked) onWorkingDaysChange([...workingDays, day]);
                  else onWorkingDaysChange(workingDays.filter((d) => d !== day));
                }}
              />
              {day.slice(0, 3)}
            </label>
          ))}
        </div>
      </div>
      <Button onClick={onNext} className="rounded-xl btn-press gap-2">
        Next <ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
