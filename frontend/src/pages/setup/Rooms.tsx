import { useState } from "react";
import { Plus, Pencil, Trash2, DoorOpen } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip } from "@/components/common/StatusChip";
import { useRooms } from "@/hooks/useRooms";
import { EmptyState } from "@/components/common/EmptyState";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RoomsPage() {
  const { data: rooms, isLoading, create, update, remove } = useRooms();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<any>(null);
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState(60);
  const [roomType, setRoomType] = useState<string>("classroom");
  const [hasProjector, setHasProjector] = useState(false);
  const [hasComputers, setHasComputers] = useState(false);
  const [hasAc, setHasAc] = useState(false);

  const handleEdit = (room: any) => {
    setEditingRoom(room);
    setName(room.name);
    setCapacity(room.capacity);
    setRoomType(room.room_type);
    setHasProjector(room.has_projector || false);
    setHasComputers(room.has_computers || false);
    setHasAc(room.has_ac || false);
    setDialogOpen(true);
  };

  const handleAdd = async () => {
    if (editingRoom) {
      await update(editingRoom.room_id, {
        name,
        capacity,
        room_type: roomType,
        has_projector: hasProjector,
        has_computers: hasComputers,
        has_ac: hasAc,
      });
    } else {
      await create({
        name,
        capacity,
        room_type: roomType,
        has_projector: hasProjector,
        has_computers: hasComputers,
        has_ac: hasAc,
      });
    }
    setDialogOpen(false);
    setEditingRoom(null);
    setName("");
    setCapacity(60);
    setRoomType("classroom");
    setHasProjector(false);
    setHasComputers(false);
    setHasAc(false);
  };

  if (isLoading && rooms.length === 0) {
    return <div className="p-6 text-muted-foreground">Loading rooms...</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Rooms & Labs" description="Manage classrooms and lab spaces">
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) { setEditingRoom(null); setName(""); setCapacity(60); setRoomType("classroom"); setHasProjector(false); setHasComputers(false); setHasAc(false); } }}>
          <DialogTrigger asChild>
            <Button className="rounded-xl btn-press gap-2"><Plus className="h-4 w-4" />Add Room</Button>
          </DialogTrigger>
          <DialogContent className="rounded-lg max-w-md">
            <DialogHeader><DialogTitle className="font-display">{editingRoom ? "Edit Room" : "Add Room"}</DialogTitle></DialogHeader>
            <div className="space-y-4 mt-2">
              <div className="space-y-2">
                <Label>Room Name</Label>
                <Input className="rounded-xl" value={name} onChange={(e) => setName(e.target.value)} placeholder="Room 101" />
              </div>
              <div className="space-y-2">
                <Label>Capacity</Label>
                <Input type="number" className="rounded-xl" value={capacity} onChange={(e) => setCapacity(Number(e.target.value))} min={1} max={500} />
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
                      onClick={() => setRoomType(val)}
                      className={`p-2.5 rounded-xl border-2 text-xs font-medium transition-all ${
                        roomType === val ? "border-primary bg-accent" : "border-border hover:border-border-strong"
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
                    [hasProjector, setHasProjector, "Projector"],
                    [hasComputers, setHasComputers, "Computers"],
                    [hasAc, setHasAc, "AC"],
                  ] as [boolean, React.Dispatch<React.SetStateAction<boolean>>, string][]).map(([val, setter, lbl]) => (
                    <button
                      key={lbl}
                      onClick={() => setter(!val)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                        val ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-border-strong"
                      }`}
                    >
                      {val ? "✓ " : ""}{lbl}
                    </button>
                  ))}
                </div>
              </div>
              <Button onClick={handleAdd} className="w-full rounded-xl btn-press" disabled={!name.trim()}>{editingRoom ? "Update Room" : "Add Room"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </PageHeader>

      {rooms.length === 0 ? (
        <EmptyState icon={DoorOpen} title="No rooms" description="Add classrooms and labs to get started" actionLabel="Add Room" onAction={() => setDialogOpen(true)} />
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
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7" onClick={() => handleEdit(room)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="rounded-xl h-7 w-7 text-destructive" onClick={() => remove(room.room_id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
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
