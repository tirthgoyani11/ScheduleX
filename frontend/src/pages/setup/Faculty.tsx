import { useState } from "react";
import { Plus, Pencil, Trash2, Users, Search } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useFaculty } from "@/hooks/useFaculty";
import { EmptyState } from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { FacultySkeleton } from "@/components/skeletons/PageSkeletons";

export default function FacultyPage() {
  const { data: facultyList, isLoading, create, remove } = useFaculty();
  const [search, setSearch] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmpId, setNewEmpId] = useState("");
  const [newMaxLoad, setNewMaxLoad] = useState(20);
  const [newExpertise, setNewExpertise] = useState("");

  if (isLoading && facultyList.length === 0) return <FacultySkeleton />;

  const filtered = facultyList.filter((f) => {
    if (search && !f.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleAdd = async () => {
    const expertise = newExpertise ? newExpertise.split(",").map((s) => s.trim()).filter(Boolean) : [];
    await create({
      name: newName,
      employee_id: newEmpId,
      expertise,
      max_weekly_load: newMaxLoad,
    });
    setDrawerOpen(false);
    setNewName("");
    setNewEmpId("");
    setNewExpertise("");
    setNewMaxLoad(20);
  };

  const avatarColors = ["#6D28D9", "#1D4ED8", "#15803D", "#C2410C", "#9D174D", "#854D0E", "#0E7490", "#4338CA"];
  const getColor = (idx: number) => avatarColors[idx % avatarColors.length];

  return (
    <div className="space-y-6">
      <PageHeader title="Faculty" description="Manage department faculty members">
        <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
          <SheetTrigger asChild>
            <Button className="rounded-xl btn-press gap-2"><Plus className="h-4 w-4" />Add Faculty</Button>
          </SheetTrigger>
          <SheetContent className="w-[400px]">
            <SheetHeader><SheetTitle className="font-display">Add Faculty</SheetTitle></SheetHeader>
            <div className="space-y-4 mt-6">
              <div className="space-y-2"><Label>Full Name</Label><Input className="rounded-xl" placeholder="Dr. John Doe" value={newName} onChange={(e) => setNewName(e.target.value)} /></div>
              <div className="space-y-2"><Label>Employee ID</Label><Input className="rounded-xl font-mono" placeholder="EMP007" value={newEmpId} onChange={(e) => setNewEmpId(e.target.value)} /></div>
              <div className="space-y-2"><Label>Expertise (comma-separated)</Label><Input className="rounded-xl" placeholder="DSA, OS, Networks" value={newExpertise} onChange={(e) => setNewExpertise(e.target.value)} /></div>
              <div className="space-y-2">
                <Label>Max Weekly Load (periods)</Label>
                <Slider value={[newMaxLoad]} onValueChange={([v]) => setNewMaxLoad(v)} min={5} max={40} step={1} className="mt-2" />
                <p className="text-xs text-muted-foreground">{newMaxLoad} periods / week</p>
              </div>
              <Button className="w-full rounded-xl btn-press" onClick={handleAdd}>Add Faculty</Button>
            </div>
          </SheetContent>
        </Sheet>
      </PageHeader>

      {/* Search */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="rounded-xl pl-9" placeholder="Search faculty..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={Users} title="No faculty found" description="Add faculty members to get started" actionLabel="Add Faculty" onAction={() => setDrawerOpen(true)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((f, idx) => {
            const color = getColor(idx);
            return (
              <div key={f.faculty_id} className="bg-card rounded-xl shadow-sm p-5 card-hover group relative">
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
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
    </div>
  );
}
