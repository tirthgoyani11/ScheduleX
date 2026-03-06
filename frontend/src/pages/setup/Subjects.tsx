import { useState } from "react";
import { Plus, Pencil, Trash2, BookOpen } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip, getSubjectChipVariant } from "@/components/common/StatusChip";
import { useSubjects } from "@/hooks/useSubjects";
import { useDepartments } from "@/hooks/useDepartments";
import { useAuthStore } from "@/store/useAuthStore";
import { EmptyState } from "@/components/common/EmptyState";
import { useSetupStore } from "@/store/useSetupStore";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SubjectsSkeleton } from "@/components/skeletons/PageSkeletons";
import type { Subject } from "@/types";

const defaultForm = {
  name: "", code: "", credits: 3, lectureHours: 3, labHours: 0, batchSize: 60, batch: "", needsLab: false,
};

export default function SubjectsPage() {
  const user = useAuthStore((s) => s.user);
  const isSuperAdmin = user?.role === "super_admin";
  const { data: departments } = useDepartments();
  const [selectedDeptId, setSelectedDeptId] = useState<string>("");

  const activeDeptId = isSuperAdmin && selectedDeptId && selectedDeptId !== "all" ? selectedDeptId : undefined;
  const { currentSemester, setSemester } = useSetupStore();
  const { data: allSubjects, isLoading, create, update, remove } = useSubjects(currentSemester, activeDeptId);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
  const [form, setForm] = useState(defaultForm);

  const openCreate = () => {
    setEditingSubject(null);
    setForm(defaultForm);
    setDialogOpen(true);
  };

  const openEdit = (sub: Subject) => {
    setEditingSubject(sub);
    setForm({
      name: sub.name,
      code: sub.subject_code,
      credits: sub.credits,
      lectureHours: sub.lecture_hours || sub.weekly_periods,
      labHours: sub.lab_hours || 0,
      batchSize: sub.batch_size || 60,
      batch: sub.batch || "",
      needsLab: sub.needs_lab,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    const body = {
      name: form.name,
      subject_code: form.code,
      semester: currentSemester,
      credits: form.credits,
      weekly_periods: form.lectureHours + form.labHours,
      lecture_hours: form.lectureHours,
      lab_hours: form.labHours,
      needs_lab: form.labHours > 0 || form.needsLab,
      batch_size: form.batchSize,
      batch: form.batch || undefined,
    };
    if (editingSubject) {
      await update(editingSubject.subject_id, body);
    } else {
      await create(body);
    }
    setDialogOpen(false);
  };

  if (isLoading && allSubjects.length === 0) return <SubjectsSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title="Subjects" description="Manage subjects by semester">
        <Button className="rounded-xl btn-press gap-2" onClick={openCreate}><Plus className="h-4 w-4" />Add Subject</Button>
      </PageHeader>

      {/* Department filter & Semester tabs */}
      <div className="flex items-center gap-3 flex-wrap">
        {isSuperAdmin && departments.length > 0 && (
          <Select value={selectedDeptId} onValueChange={setSelectedDeptId}>
            <SelectTrigger className="w-[200px] rounded-xl">
              <SelectValue placeholder="All Departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              {departments.map((d) => (
                <SelectItem key={d.dept_id} value={d.dept_id}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

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
        <EmptyState icon={BookOpen} title="No subjects" description={`No subjects found for Semester ${currentSemester}`} actionLabel="Add Subject" onAction={openCreate} />
      ) : (
        <div className="bg-card rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Code</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Name</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Type</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Credits</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">L</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">P</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Batch</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {allSubjects.map((sub) => (
                <tr key={sub.subject_id} className="border-b border-border last:border-0 group hover:bg-accent/50 transition-colors">
                  <td className="py-3 px-4 font-mono font-medium">{sub.subject_code}</td>
                  <td className="py-3 px-4">{sub.name}</td>
                  <td className="py-3 px-4"><StatusChip variant={getSubjectChipVariant(sub.needs_lab)} label={sub.lab_hours > 0 ? "L+P" : "THEORY"} /></td>
                  <td className="py-3 px-4">{sub.credits}</td>
                  <td className="py-3 px-4">{sub.lecture_hours || sub.weekly_periods}</td>
                  <td className="py-3 px-4">{sub.lab_hours || 0}</td>
                  <td className="py-3 px-4">{sub.batch || "—"}</td>
                  <td className="py-3 px-4">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 justify-end">
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7" onClick={() => openEdit(sub)}><Pencil className="h-3.5 w-3.5" /></Button>
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7 text-destructive" onClick={() => remove(sub.subject_id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="rounded-lg max-w-md">
          <DialogHeader><DialogTitle className="font-display">{editingSubject ? "Edit Subject" : "Add Subject"}</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Subject Name</Label>
              <Input className="rounded-xl" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Data Structures" />
            </div>
            <div className="space-y-2">
              <Label>Subject Code</Label>
              <Input className="rounded-xl font-mono" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="DSA301" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>Credits</Label>
                <Input type="number" className="rounded-xl" value={form.credits} onChange={(e) => setForm({ ...form, credits: Number(e.target.value) })} min={1} max={6} />
              </div>
              <div className="space-y-2">
                <Label>Lecture hrs/wk</Label>
                <Input type="number" className="rounded-xl" value={form.lectureHours} onChange={(e) => setForm({ ...form, lectureHours: Number(e.target.value) })} min={0} max={10} />
              </div>
              <div className="space-y-2">
                <Label>Lab hrs/wk</Label>
                <Input type="number" className="rounded-xl" value={form.labHours} onChange={(e) => setForm({ ...form, labHours: Number(e.target.value) })} min={0} max={10} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Batch Size</Label>
                <Input type="number" className="rounded-xl" value={form.batchSize} onChange={(e) => setForm({ ...form, batchSize: Number(e.target.value) })} min={0} />
              </div>
              <div className="space-y-2">
                <Label>Batch Label</Label>
                <Input className="rounded-xl" value={form.batch} onChange={(e) => setForm({ ...form, batch: e.target.value })} placeholder="Batch A" />
              </div>
            </div>
            <Button onClick={handleSave} className="w-full rounded-xl btn-press" disabled={!form.name.trim() || !form.code.trim()}>
              {editingSubject ? "Update Subject" : "Add Subject"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
