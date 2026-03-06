import { useState } from "react";
import { Plus, Pencil, Trash2, BookOpen } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip, getSubjectChipVariant } from "@/components/common/StatusChip";
import { useSubjects } from "@/hooks/useSubjects";
import { EmptyState } from "@/components/common/EmptyState";
import { useSetupStore } from "@/store/useSetupStore";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SubjectsSkeleton } from "@/components/skeletons/PageSkeletons";

export default function SubjectsPage() {
  const { currentSemester, setSemester } = useSetupStore();
  const { data: allSubjects, isLoading, create, update, remove } = useSubjects(currentSemester);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState<any>(null);
  const [newName, setNewName] = useState("");
  const [newCode, setNewCode] = useState("");
  const [newNeedsLab, setNewNeedsLab] = useState(false);
  const [newCredits, setNewCredits] = useState(3);
  const [newPeriods, setNewPeriods] = useState(3);
  const [newBatchSize, setNewBatchSize] = useState(0);
  const [newBatch, setNewBatch] = useState("");

  const handleEdit = (subject: any) => {
    setEditingSubject(subject);
    setNewName(subject.name);
    setNewCode(subject.subject_code);
    setNewNeedsLab(subject.needs_lab);
    setNewCredits(subject.credits);
    setNewPeriods(subject.weekly_periods);
    setNewBatchSize(subject.batch_size || 0);
    setNewBatch(subject.batch || "");
    setDialogOpen(true);
  };

  const handleAdd = async () => {
    if (editingSubject) {
      await update(editingSubject.subject_id, {
        name: newName,
        subject_code: newCode,
        semester: currentSemester,
        credits: newCredits,
        weekly_periods: newPeriods,
        needs_lab: newNeedsLab,
        batch_size: newBatchSize,
        batch: newBatch || undefined,
      });
    } else {
      await create({
        name: newName,
        subject_code: newCode,
        semester: currentSemester,
        credits: newCredits,
        weekly_periods: newPeriods,
        needs_lab: newNeedsLab,
        batch_size: newBatchSize,
        batch: newBatch || undefined,
      });
    }
    setDialogOpen(false);
    setEditingSubject(null);
    setNewName("");
    setNewCode("");
    setNewNeedsLab(false);
    setNewCredits(3);
    setNewPeriods(3);
    setNewBatchSize(0);
    setNewBatch("");
  };

  if (isLoading && allSubjects.length === 0) return <SubjectsSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title="Subjects" description="Manage subjects by semester">
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) { setEditingSubject(null); setNewName(""); setNewCode(""); setNewNeedsLab(false); setNewCredits(3); setNewPeriods(3); setNewBatchSize(0); setNewBatch(""); } }}>
          <DialogTrigger asChild>
            <Button className="rounded-xl btn-press gap-2"><Plus className="h-4 w-4" />Add Subject</Button>
          </DialogTrigger>
          <DialogContent className="rounded-lg max-w-md">
            <DialogHeader><DialogTitle className="font-display">{editingSubject ? "Edit Subject" : "Add Subject"}</DialogTitle></DialogHeader>
            <div className="space-y-4 mt-2">
              <div className="space-y-2">
                <Label>Subject Name</Label>
                <Input className="rounded-xl" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Data Structures" />
              </div>
              <div className="space-y-2">
                <Label>Subject Code</Label>
                <Input className="rounded-xl font-mono" value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="DSA301" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Credits</Label>
                  <Input type="number" className="rounded-xl" value={newCredits} onChange={(e) => setNewCredits(Number(e.target.value))} min={1} max={6} />
                </div>
                <div className="space-y-2">
                  <Label>Periods/week</Label>
                  <Input type="number" className="rounded-xl" value={newPeriods} onChange={(e) => setNewPeriods(Number(e.target.value))} min={1} max={10} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  {([
                    [false, "📚 Theory"],
                    [true, "🔬 Needs Lab"],
                  ] as const).map(([val, lbl]) => (
                    <button
                      key={String(val)}
                      onClick={() => setNewNeedsLab(val)}
                      className={`p-2.5 rounded-xl border-2 text-xs font-medium transition-all ${
                        newNeedsLab === val ? "border-primary bg-accent" : "border-border hover:border-border-strong"
                      }`}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Batch Size</Label>
                  <Input type="number" className="rounded-xl" value={newBatchSize} onChange={(e) => setNewBatchSize(Number(e.target.value))} min={0} />
                </div>
                <div className="space-y-2">
                  <Label>Batch Label</Label>
                  <Input className="rounded-xl" value={newBatch} onChange={(e) => setNewBatch(e.target.value)} placeholder="Batch A" />
                </div>
              </div>
              <Button onClick={handleAdd} className="w-full rounded-xl btn-press">{editingSubject ? "Update Subject" : "Add Subject"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </PageHeader>

      {/* Semester tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
          <button
            key={sem}
            onClick={() => setSemester(sem)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
              currentSemester === sem ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:bg-accent"
            }`}
          >
            Sem {sem}
          </button>
        ))}
      </div>

      {allSubjects.length === 0 ? (
        <EmptyState icon={BookOpen} title="No subjects" description={`No subjects found for Semester ${currentSemester}`} actionLabel="Add Subject" onAction={() => setDialogOpen(true)} />
      ) : (
        <div className="bg-card rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Code</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Name</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Type</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Credits</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Periods/wk</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Batch</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {allSubjects.map((sub) => (
                <tr key={sub.subject_id} className="border-b border-border last:border-0 group hover:bg-accent/50 transition-colors">
                  <td className="py-3 px-4 font-mono font-medium">{sub.subject_code}</td>
                  <td className="py-3 px-4">{sub.name}</td>
                  <td className="py-3 px-4"><StatusChip variant={getSubjectChipVariant(sub.needs_lab)} label={sub.needs_lab ? "LAB" : "THEORY"} /></td>
                  <td className="py-3 px-4">{sub.credits}</td>
                  <td className="py-3 px-4">{sub.weekly_periods}</td>
                  <td className="py-3 px-4">{sub.batch || "—"}</td>
                  <td className="py-3 px-4">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 justify-end">
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7" onClick={() => handleEdit(sub)}><Pencil className="h-3.5 w-3.5" /></Button>
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7 text-destructive" onClick={() => remove(sub.subject_id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
