import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, ArrowLeft, ArrowRight, Check, Loader2, X } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusChip, getSubjectChipVariant } from "@/components/common/StatusChip";
import { useTimetableStore } from "@/store/useTimetableStore";
import { useTimetable } from "@/hooks/useTimetable";
import { useSubjects } from "@/hooks/useSubjects";
import { useFaculty } from "@/hooks/useFaculty";

const allDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function GeneratePage() {
  const store = useTimetableStore();
  const { generate, isGenerating } = useTimetable();
  const { data: allSubjects } = useSubjects(store.selectedSemester);
  const { data: allFaculty } = useFaculty();
  const navigate = useNavigate();
  const [newDivision, setNewDivision] = useState("");
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [generatingText, setGeneratingText] = useState("");
  const [academicYear, setAcademicYear] = useState("2025-26");

  const semSubjects = allSubjects;

  const handleGenerate = async () => {
    const steps = ["Placing subjects...", "Checking conflicts...", "Optimizing schedule..."];
    for (const step of steps) {
      setGeneratingText(step);
      await new Promise((r) => setTimeout(r, 700));
    }

    // Build faculty_subject_map: { faculty_id: [subject_id, ...] }
    const fsMap: Record<string, string[]> = {};
    for (const [key, facultyId] of Object.entries(assignments)) {
      // key is either subject_id or "subject_id-batch"
      const subjectId = key.includes("-") ? key.split("-")[0] : key;
      if (!fsMap[facultyId]) fsMap[facultyId] = [];
      if (!fsMap[facultyId].includes(subjectId)) {
        fsMap[facultyId].push(subjectId);
      }
    }

    const result = await generate({
      semester: store.selectedSemester,
      academic_year: academicYear,
      faculty_subject_map: fsMap,
      time_limit_seconds: 120,
    });
    navigate(`/timetable/view/${result.timetable_id}`);
  };

  const steps = [
    { num: 1, label: "Config" },
    { num: 2, label: "Assign Faculty" },
    { num: 3, label: "Generate" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Generate Timetable" description="Create an optimized schedule in 3 steps" />

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {steps.map((step, i) => (
          <div key={step.num} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              store.generatingStep === step.num ? "bg-primary text-primary-foreground" :
              store.generatingStep > step.num ? "bg-chip-green-bg text-chip-green-txt" : "bg-muted text-muted-foreground"
            }`}>
              {store.generatingStep > step.num ? <Check className="h-4 w-4" /> : <span>{step.num}</span>}
              <span>{step.label}</span>
            </div>
            {i < steps.length - 1 && <div className="w-8 h-px bg-border" />}
          </div>
        ))}
      </div>

      {/* Step 1 */}
      {store.generatingStep === 1 && (
        <div className="bg-card rounded-lg shadow-sm p-6 space-y-5 max-w-xl">
          <div className="space-y-2">
            <Label>Semester</Label>
            <Select value={String(store.selectedSemester)} onValueChange={(v) => store.setSemester(Number(v))}>
              <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
              <SelectContent>
                {[1,2,3,4,5,6,7,8].map((s) => <SelectItem key={s} value={String(s)}>Semester {s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Divisions</Label>
            <div className="flex flex-wrap gap-2">
              {store.divisions.map((d) => (
                <span key={d} className="chip chip-blue gap-1">
                  Div {d}
                  <button onClick={() => store.setDivisions(store.divisions.filter((x) => x !== d))}><X className="h-3 w-3" /></button>
                </span>
              ))}
              <div className="flex gap-1.5">
                <Input className="rounded-xl h-7 w-16 text-xs" value={newDivision} onChange={(e) => setNewDivision(e.target.value)} placeholder="B" />
                <Button variant="outline" size="sm" className="rounded-xl h-7 text-xs" onClick={() => { if (newDivision) { store.setDivisions([...store.divisions, newDivision]); setNewDivision(""); } }}>+</Button>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Academic Year</Label>
            <Input className="rounded-xl" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Working Days</Label>
            <div className="flex flex-wrap gap-2">
              {allDays.map((day) => (
                <label key={day} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={store.workingDays.includes(day)}
                    onCheckedChange={(checked) => {
                      if (checked) store.setWorkingDays([...store.workingDays, day]);
                      else store.setWorkingDays(store.workingDays.filter((d) => d !== day));
                    }}
                  />
                  {day.slice(0, 3)}
                </label>
              ))}
            </div>
          </div>
          <Button onClick={() => store.setStep(2)} className="rounded-xl btn-press gap-2">
            Next <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Step 2 */}
      {store.generatingStep === 2 && (
        <div className="space-y-4 max-w-2xl">
          {semSubjects.length === 0 ? (
            <div className="bg-card rounded-lg shadow-sm p-6 text-center">
              <p className="text-muted-foreground">No subjects found for Semester {store.selectedSemester}. Add subjects first.</p>
            </div>
          ) : (
            semSubjects.map((sub) => (
              <div key={sub.subject_id} className="bg-card rounded-lg shadow-sm p-5 space-y-3">
                <div className="flex items-center gap-3">
                  <StatusChip variant={getSubjectChipVariant(sub.needs_lab)} label={sub.needs_lab ? "LAB" : "THEORY"} />
                  <span className="font-medium">{sub.name}</span>
                  <span className="font-mono text-xs text-muted-foreground">{sub.subject_code}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground w-20">Faculty:</span>
                  <Select onValueChange={(v) => setAssignments({...assignments, [sub.subject_id]: v})}>
                    <SelectTrigger className="rounded-xl max-w-xs"><SelectValue placeholder="Select faculty" /></SelectTrigger>
                    <SelectContent>
                      {allFaculty.map((f) => (
                        <SelectItem key={f.faculty_id} value={f.faculty_id}>
                          {f.name} ({f.max_weekly_load} max periods)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            ))
          )}
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => store.setStep(1)} className="rounded-xl gap-2"><ArrowLeft className="h-4 w-4" />Back</Button>
            <Button onClick={() => store.setStep(3)} className="rounded-xl btn-press gap-2">Next <ArrowRight className="h-4 w-4" /></Button>
          </div>
        </div>
      )}

      {/* Step 3 */}
      {store.generatingStep === 3 && (
        <div className="bg-card rounded-lg shadow-sm p-8 max-w-lg mx-auto text-center space-y-6">
          <div className="space-y-2">
            <h3 className="text-lg font-semibold font-display">Ready to Generate</h3>
            <p className="text-muted-foreground text-sm">Semester {store.selectedSemester} · Div {store.divisions.join(", ")} · {store.workingDays.length} days</p>
          </div>
          <div className="bg-muted rounded-xl p-4 text-left text-sm space-y-1">
            <p><strong>Subjects:</strong> {semSubjects.length}</p>
            <p><strong>Faculty assigned:</strong> {Object.keys(assignments).length}</p>
            <p><strong>Working days:</strong> {store.workingDays.map(d => d.slice(0,3)).join(", ")}</p>
          </div>
          {isGenerating ? (
            <div className="space-y-3">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full animate-pulse" style={{ width: "70%" }} />
              </div>
              <p className="text-sm text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />{generatingText}
              </p>
            </div>
          ) : (
            <div className="flex gap-3 justify-center">
              <Button variant="outline" onClick={() => store.setStep(2)} className="rounded-xl gap-2"><ArrowLeft className="h-4 w-4" />Back</Button>
              <Button onClick={handleGenerate} size="lg" className="rounded-xl btn-press gap-2"><Zap className="h-4 w-4" />Generate Timetable</Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
