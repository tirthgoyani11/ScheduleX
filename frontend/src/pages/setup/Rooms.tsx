import { useState } from "react";
import { Plus, Pencil, Trash2, DoorOpen } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip } from "@/components/common/StatusChip";
import { useRooms } from "@/hooks/useRooms";
import { EmptyState } from "@/components/common/EmptyState";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Room } from "@/types";

const defaultForm = { name: "", capacity: 60, roomType: "classroom", hasProjector: false, hasComputers: false, hasAc: false };

export default function RoomsPage() {
  const { data: rooms, isLoading, create, update, remove } = useRooms();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [form, setForm] = useState(defaultForm);

  const openCreate = () => {
    setEditingRoom(null);
    setForm(defaultForm);
    setDialogOpen(true);
  };

  const openEdit = (room: Room) => {
    setEditingRoom(room);
    setForm({
      name: room.name,
      capacity: room.capacity,
      roomType: room.room_type,
      hasProjector: room.has_projector,
      hasComputers: room.has_computers,
      hasAc: room.has_ac,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    const body = {
      name: form.name,
      capacity: form.capacity,
      room_type: form.roomType,
      has_projector: form.hasProjector,
      has_computers: form.hasComputers,
      has_ac: form.hasAc,
    };
    if (editingRoom) {
      await update(editingRoom.room_id, body);
    } else {
      await create(body);
    }
    setDialogOpen(false);
  };

  if (isLoading && rooms.length === 0) {
    return <div className="p-6 text-muted-foreground">Loading rooms...</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Rooms & Labs" description="Manage classrooms and lab spaces">
        <Button className="rounded-xl btn-press gap-2" onClick={openCreate}><Plus className="h-4 w-4" />Add Room</Button>
      </PageHeader>

      {rooms.length === 0 ? (
        <EmptyState icon={DoorOpen} title="No rooms" description="Add classrooms and labs to get started" actionLabel="Add Room" onAction={openCreate} />
      ) : (
        <div className="bg-card rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Name</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Type</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Capacity</th>
                <th className="text-left py-3 px-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Facilities</th>
                <th className="py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((room) => (
                <tr key={room.room_id} className="border-b border-border last:border-0 group hover:bg-accent/50 transition-colors">
                  <td className="py-3 px-4 font-medium">{room.name}</td>
                  <td className="py-3 px-4">
                    <StatusChip
                      variant={room.room_type === "lab" ? "lab" : room.room_type === "seminar" ? "lecture" : "theory"}
                      label={room.room_type.toUpperCase()}
                    />
                  </td>
                  <td className="py-3 px-4">{room.capacity}</td>
                  <td className="py-3 px-4">
                    <div className="flex gap-1.5 flex-wrap">
                      {room.has_projector && <span className="px-2 py-0.5 rounded-full bg-accent text-xs">Projector</span>}
                      {room.has_computers && <span className="px-2 py-0.5 rounded-full bg-accent text-xs">Computers</span>}
                      {room.has_ac && <span className="px-2 py-0.5 rounded-full bg-accent text-xs">AC</span>}
                      {!room.has_projector && !room.has_computers && !room.has_ac && <span className="text-muted-foreground text-xs">—</span>}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 justify-end">
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7" onClick={() => openEdit(room)}><Pencil className="h-3.5 w-3.5" /></Button>
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7 text-destructive" onClick={() => remove(room.room_id)}><Trash2 className="h-3.5 w-3.5" /></Button>
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
          <DialogHeader><DialogTitle className="font-display">{editingRoom ? "Edit Room" : "Add Room"}</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Room Name</Label>
              <Input className="rounded-xl" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Room 101" />
            </div>
            <div className="space-y-2">
              <Label>Capacity</Label>
              <Input type="number" className="rounded-xl" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} min={1} max={500} />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <div className="grid grid-cols-3 gap-2">
                {([
                  ["classroom", "🏫 Classroom"],
                  ["lab", "🔬 Lab"],
                  ["seminar", "🎤 Seminar"],
                ] as const).map(([val, lbl]) => (
                  <button
                    key={val}
                    onClick={() => setForm({ ...form, roomType: val })}
                    className={`p-2.5 rounded-xl border-2 text-xs font-medium transition-all ${
                      form.roomType === val ? "border-primary bg-accent" : "border-border hover:border-border-strong"
                    }`}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>Facilities</Label>
              <div className="flex gap-3 flex-wrap">
                {([
                  ["hasProjector", "Projector"],
                  ["hasComputers", "Computers"],
                  ["hasAc", "AC"],
                ] as const).map(([key, lbl]) => (
                  <button
                    key={key}
                    onClick={() => setForm({ ...form, [key]: !form[key] })}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                      form[key] ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-border-strong"
                    }`}
                  >
                    {form[key] ? "✓ " : ""}{lbl}
                  </button>
                ))}
              </div>
            </div>
            <Button onClick={handleSave} className="w-full rounded-xl btn-press" disabled={!form.name.trim()}>
              {editingRoom ? "Update Room" : "Add Room"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
