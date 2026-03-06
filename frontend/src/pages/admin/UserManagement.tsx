import { useState } from "react";
import { Plus, Pencil, Trash2, Users, Search, Shield, GraduationCap, Mail } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/common/EmptyState";
import { useUsers } from "@/hooks/useUsers";
import { useAuthStore } from "@/store/useAuthStore";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { User } from "@/types";

const defaultForm = { full_name: "", email: "", password: "", role: "dept_admin" as string };

export default function UserManagementPage() {
  const currentUser = useAuthStore((s) => s.user);
  const { data: users, isLoading, create, update, remove } = useUsers();

  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("hods");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  const hods = users.filter((u) => u.role === "dept_admin");
  const faculty = users.filter((u) => u.role === "faculty");
  const activeList = tab === "hods" ? hods : faculty;
  const filtered = activeList.filter((u) =>
    !search || u.full_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase())
  );

  const openCreate = (role: string) => {
    setEditingUser(null);
    setForm({ ...defaultForm, role });
    setDrawerOpen(true);
  };

  const openEdit = (u: User) => {
    setEditingUser(u);
    setForm({ full_name: u.full_name, email: u.email, password: "", role: u.role });
    setDrawerOpen(true);
  };

  const handleSave = async () => {
    if (editingUser) {
      await update(editingUser.user_id, {
        full_name: form.full_name,
        email: form.email,
        role: form.role,
      });
    } else {
      await create({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        role: form.role,
        college_id: currentUser?.college_id,
        dept_id: currentUser?.dept_id ?? undefined,
      });
    }
    setDrawerOpen(false);
  };

  const handleDelete = async () => {
    if (deleteTarget) {
      await remove(deleteTarget.user_id);
      setDeleteTarget(null);
    }
  };

  const avatarColors = ["#6D28D9", "#1D4ED8", "#15803D", "#C2410C", "#9D174D", "#854D0E", "#0E7490", "#4338CA"];
  const getColor = (idx: number) => avatarColors[idx % avatarColors.length];

  const roleLabel = (role: string) => {
    if (role === "dept_admin") return "HOD";
    if (role === "faculty") return "Faculty";
    if (role === "super_admin") return "Super Admin";
    return role;
  };

  const roleChipClass = (role: string) => {
    if (role === "dept_admin") return "chip-purple";
    if (role === "faculty") return "chip-blue";
    if (role === "super_admin") return "chip-green";
    return "chip-yellow";
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="User Management" description="Manage HODs and Faculty members" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card rounded-xl shadow-sm p-5 animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-muted" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-muted rounded w-2/3" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="User Management" description="Manage HODs and Faculty user accounts">
        <Button className="rounded-xl btn-press gap-2" onClick={() => openCreate(tab === "hods" ? "dept_admin" : "faculty")}>
          <Plus className="h-4 w-4" />Add {tab === "hods" ? "HOD" : "Faculty"}
        </Button>
      </PageHeader>

      <Tabs value={tab} onValueChange={setTab}>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <TabsList className="rounded-xl">
            <TabsTrigger value="hods" className="rounded-xl gap-2">
              <Shield className="h-4 w-4" />HODs
              <span className="chip chip-purple ml-1">{hods.length}</span>
            </TabsTrigger>
            <TabsTrigger value="faculty" className="rounded-xl gap-2">
              <GraduationCap className="h-4 w-4" />Faculty
              <span className="chip chip-blue ml-1">{faculty.length}</span>
            </TabsTrigger>
          </TabsList>
          <div className="relative max-w-xs flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input className="rounded-xl pl-9" placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>

        <TabsContent value="hods" className="mt-4">
          <UserGrid
            users={filtered}
            getColor={getColor}
            roleLabel={roleLabel}
            roleChipClass={roleChipClass}
            onEdit={openEdit}
            onDelete={setDeleteTarget}
            emptyRole="HOD"
            onAdd={() => openCreate("dept_admin")}
          />
        </TabsContent>
        <TabsContent value="faculty" className="mt-4">
          <UserGrid
            users={filtered}
            getColor={getColor}
            roleLabel={roleLabel}
            roleChipClass={roleChipClass}
            onEdit={openEdit}
            onDelete={setDeleteTarget}
            emptyRole="Faculty"
            onAdd={() => openCreate("faculty")}
          />
        </TabsContent>
      </Tabs>

      {/* Create / Edit Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-[400px]">
          <SheetHeader>
            <SheetTitle className="font-display">
              {editingUser ? `Edit ${roleLabel(form.role)}` : `Add ${roleLabel(form.role)}`}
            </SheetTitle>
          </SheetHeader>
          <div className="space-y-4 mt-6">
            <div className="space-y-2">
              <Label>Full Name</Label>
              <Input className="rounded-xl" placeholder="Dr. John Doe" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input className="rounded-xl" type="email" placeholder="john@cvmu.edu.in" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            {!editingUser && (
              <div className="space-y-2">
                <Label>Password</Label>
                <Input className="rounded-xl" type="password" placeholder="Minimum 6 characters" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
            )}
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger className="rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dept_admin">HOD (Department Admin)</SelectItem>
                  <SelectItem value="faculty">Faculty</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              className="w-full rounded-xl btn-press"
              onClick={handleSave}
              disabled={!form.full_name.trim() || !form.email.trim() || (!editingUser && form.password.length < 6)}
            >
              {editingUser ? "Update User" : "Create User"}
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {deleteTarget?.full_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will deactivate the user account. They will no longer be able to log in.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-xl">Cancel</AlertDialogCancel>
            <AlertDialogAction className="rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={handleDelete}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function UserGrid({
  users,
  getColor,
  roleLabel,
  roleChipClass,
  onEdit,
  onDelete,
  emptyRole,
  onAdd,
}: {
  users: User[];
  getColor: (idx: number) => string;
  roleLabel: (role: string) => string;
  roleChipClass: (role: string) => string;
  onEdit: (u: User) => void;
  onDelete: (u: User) => void;
  emptyRole: string;
  onAdd: () => void;
}) {
  if (users.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title={`No ${emptyRole}s found`}
        description={`Add ${emptyRole} members to manage them here`}
        actionLabel={`Add ${emptyRole}`}
        onAction={onAdd}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {users.map((u, idx) => {
        const color = getColor(idx);
        return (
          <div key={u.user_id} className="bg-card rounded-xl shadow-sm p-5 card-hover group relative">
            <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
              <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7" onClick={() => onEdit(u)}>
                <Pencil className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7 text-destructive" onClick={() => onDelete(u)}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="flex items-center gap-3 mb-3">
              <div
                className="h-10 w-10 rounded-full flex items-center justify-center text-sm font-semibold shrink-0"
                style={{ backgroundColor: color + "20", color }}
              >
                {u.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
              </div>
              <div className="min-w-0">
                <p className="font-medium truncate">{u.full_name}</p>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Mail className="h-3 w-3 shrink-0" />
                  <span className="truncate">{u.email}</span>
                </div>
              </div>
            </div>
            <div className="border-t border-border pt-3">
              <span className={`chip ${roleChipClass(u.role)}`}>{roleLabel(u.role)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
