import { useState } from "react";
import { Plus, Pencil, Trash2, Users, Search } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useFaculty } from "@/hooks/useFaculty";
import { EmptyState } from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { FacultySkeleton } from "@/components/skeletons/PageSkeletons";
import type { Faculty } from "@/types";

const defaultForm = { name: "", empId: "", expertise: "", maxLoad: 20 };

export default function FacultyPage() {
  const { data: facultyList, isLoading, create, update, remove } = useFaculty();
  const [search, setSearch] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingFaculty, setEditingFaculty] = useState<Faculty | null>(null);
  const [form, setForm] = useState(defaultForm);

  const openCreate = () => {
    setEditingFaculty(null);
    setForm(defaultForm);
    setDrawerOpen(true);
  };

  const openEdit = (f: Faculty) => {
    setEditingFaculty(f);
    setForm({
      name: f.name,
      empId: f.employee_id,
      expertise: f.expertise?.join(", ") ?? "",
      maxLoad: f.max_weekly_load,
    });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    const expertise = form.expertise ? form.expertise.split(",").map((s) => s.trim()).filter(Boolean) : [];
    const body = {
      name: form.name,
      employee_id: form.empId,
      expertise,
      max_weekly_load: form.maxLoad,
    };
    if (editingFaculty) {
      await update(editingFaculty.faculty_id, body);
    } else {
      await create(body);
    }
    setDrawerOpen(false);
  };

  if (isLoading && facultyList.length === 0) return <FacultySkeleton />;

  const filtered = facultyList.filter((f) => {
    if (search && !f.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const avatarColors = ["#6D28D9", "#1D4ED8", "#15803D", "#C2410C", "#9D174D", "#854D0E", "#0E7490", "#4338CA"];
  const getColor = (idx: number) => avatarColors[idx % avatarColors.length];

  return (
    <div className="space-y-6">
      <PageHeader title="Faculty" description="Manage department faculty members">
        <Button className="rounded-xl btn-press gap-2" onClick={openCreate}><Plus className="h-4 w-4" />Add Faculty</Button>
      </PageHeader>

      {/* Search */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="rounded-xl pl-9" placeholder="Search faculty..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={Users} title="No faculty found" description="Add faculty members to get started" actionLabel="Add Faculty" onAction={openCreate} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((f, idx) => {
            const color = getColor(idx);
            return (
              <div key={f.faculty_id} className="bg-card rounded-xl shadow-sm p-5 card-hover group relative">
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                  <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7" onClick={() => openEdit(f)}><Pencil className="h-3.5 w-3.5" /></Button>
                  <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7 text-destructive" onClick={() => remove(f.faculty_id)}><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="h-10 w-10 rounded-full flex items-center justify-center text-sm font-semibold shrink-0" style={{ backgroundColor: color + "20", color }}>
                    {f.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                  </div>
                  <div>
                    <p className="font-medium">{f.name}</p>
                    <p className="text-xs font-mono text-muted-foreground">{f.employee_id}</p>
                  </div>
                </div>
                {f.expertise && f.expertise.length > 0 && (
                  <div className="border-t border-border pt-3 mb-3">
                    <p className="text-xs text-muted-foreground mb-2">Expertise:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {f.expertise.map((e) => (
                        <span key={e} className="chip chip-blue">{e}</span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="border-t border-border pt-3">
                  <span className="text-xs text-muted-foreground">Max Weekly Load: {f.max_weekly_load} periods</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Edit Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-[400px]">
          <SheetHeader><SheetTitle className="font-display">{editingFaculty ? "Edit Faculty" : "Add Faculty"}</SheetTitle></SheetHeader>
          <div className="space-y-4 mt-6">
            <div className="space-y-2"><Label>Full Name</Label><Input className="rounded-xl" placeholder="Dr. John Doe" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-2"><Label>Employee ID</Label><Input className="rounded-xl font-mono" placeholder="EMP007" value={form.empId} onChange={(e) => setForm({ ...form, empId: e.target.value })} /></div>
            <div className="space-y-2"><Label>Expertise (comma-separated)</Label><Input className="rounded-xl" placeholder="DSA, OS, Networks" value={form.expertise} onChange={(e) => setForm({ ...form, expertise: e.target.value })} /></div>
            <div className="space-y-2">
              <Label>Max Weekly Load (periods)</Label>
              <Slider value={[form.maxLoad]} onValueChange={([v]) => setForm({ ...form, maxLoad: v })} min={5} max={40} step={1} className="mt-2" />
              <p className="text-xs text-muted-foreground">{form.maxLoad} periods / week</p>
            </div>
            <Button className="w-full rounded-xl btn-press" onClick={handleSave} disabled={!form.name.trim() || !form.empId.trim()}>
              {editingFaculty ? "Update Faculty" : "Add Faculty"}
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
