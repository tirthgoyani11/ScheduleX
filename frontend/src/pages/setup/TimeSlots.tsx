import { useState } from "react";
import { Clock, Plus, Pencil, Trash2, ArrowUp, ArrowDown, RotateCcw } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusChip, getSlotChipVariant } from "@/components/common/StatusChip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTimeSlots } from "@/hooks/useTimeSlots";
import type { TimeSlot } from "@/types";
import { useToast } from "@/hooks/use-toast";

const emptyForm = { label: "", start_time: "09:00", end_time: "10:00", slot_type: "lecture" as string, slot_order: 1 };

export default function TimeSlotsPage() {
  const { data: slots, isLoading, createSlot, updateSlot, deleteSlot, reorderSlots, seedDefaults } = useTimeSlots();
  const { toast } = useToast();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState<TimeSlot | null>(null);
  const [form, setForm] = useState(emptyForm);

  const openCreate = () => {
    setEditingSlot(null);
    setForm({ ...emptyForm, slot_order: slots.length + 1 });
    setDialogOpen(true);
  };

  const openEdit = (slot: TimeSlot) => {
    setEditingSlot(slot);
    setForm({
      label: slot.label,
      start_time: slot.start_time,
      end_time: slot.end_time,
      slot_type: slot.slot_type,
      slot_order: slot.slot_order,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingSlot) {
        await updateSlot.mutateAsync({ slot_id: editingSlot.slot_id, ...form });
        toast({ title: "Slot updated" });
      } else {
        await createSlot.mutateAsync(form as any);
        toast({ title: "Slot created" });
      }
      setDialogOpen(false);
    } catch (e: any) {
      toast({ title: "Error", description: e?.response?.data?.detail || "Failed to save", variant: "destructive" });
    }
  };

  const handleDelete = async (slot: TimeSlot) => {
    if (!confirm(`Delete "${slot.label}"?`)) return;
    try {
      await deleteSlot.mutateAsync(slot.slot_id);
      toast({ title: "Slot deleted" });
    } catch (e: any) {
      toast({ title: "Error", description: e?.response?.data?.detail || "Failed to delete", variant: "destructive" });
    }
  };

  const moveSlot = async (index: number, direction: "up" | "down") => {
    const ids = slots.map((s) => s.slot_id);
    const swap = direction === "up" ? index - 1 : index + 1;
    if (swap < 0 || swap >= ids.length) return;
    [ids[index], ids[swap]] = [ids[swap], ids[index]];
    try {
      await reorderSlots.mutateAsync(ids);
    } catch (e: any) {
      toast({ title: "Error", description: "Failed to reorder", variant: "destructive" });
    }
  };

  const handleSeedDefaults = async () => {
    try {
      await seedDefaults.mutateAsync();
      toast({ title: "Default slots created" });
    } catch (e: any) {
      toast({ title: "Error", description: e?.response?.data?.detail || "Failed to seed", variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Time Slots" description="Configure class periods, lab sessions, and breaks for timetable generation">
        <div className="flex gap-2">
          {slots.length === 0 && (
            <Button variant="outline" className="rounded-xl gap-2" onClick={handleSeedDefaults}>
              <RotateCcw className="h-4 w-4" /> Load Defaults
            </Button>
          )}
          <Button className="rounded-xl gap-2" onClick={openCreate}>
            <Plus className="h-4 w-4" /> Add Slot
          </Button>
        </div>
      </PageHeader>

      {/* Info banner */}
      <div className="chip-blue rounded-xl p-3 text-sm">
        Configure when lectures, labs, and breaks happen during the day. Only <strong>lecture</strong> and <strong>lab</strong> slots are used by the solver; <strong>break</strong> slots are display-only.
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading…</div>
      ) : slots.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No time slots configured. Click <strong>Load Defaults</strong> to start with the standard schedule, or <strong>Add Slot</strong> to build your own.
        </div>
      ) : (
        <div className="space-y-2">
          {slots.map((slot, idx) => (
            <div key={slot.slot_id || idx} className="bg-card rounded-xl shadow-sm p-4 flex items-center gap-4 hover:bg-accent/50 transition-colors">
              {/* Reorder arrows */}
              <div className="flex flex-col gap-0.5">
                <button onClick={() => moveSlot(idx, "up")} disabled={idx === 0} className="text-muted-foreground hover:text-foreground disabled:opacity-20">
                  <ArrowUp className="h-3.5 w-3.5" />
                </button>
                <button onClick={() => moveSlot(idx, "down")} disabled={idx === slots.length - 1} className="text-muted-foreground hover:text-foreground disabled:opacity-20">
                  <ArrowDown className="h-3.5 w-3.5" />
                </button>
              </div>

              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm font-medium">
                {slot.start_time} → {slot.end_time}
              </span>
              <StatusChip variant={getSlotChipVariant(slot.slot_type)} label={slot.slot_type.toUpperCase()} />
              <span className="text-sm text-muted-foreground flex-1">"{slot.label}"</span>
              <span className="text-xs font-mono text-muted-foreground">#{slot.slot_order}</span>

              {/* Actions */}
              <button onClick={() => openEdit(slot)} className="text-muted-foreground hover:text-foreground">
                <Pencil className="h-4 w-4" />
              </button>
              <button onClick={() => handleDelete(slot)} className="text-muted-foreground hover:text-destructive">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingSlot ? "Edit Time Slot" : "Add Time Slot"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Label</Label>
              <Input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} placeholder="e.g. Period 1, Lab, Lunch" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Start Time</Label>
                <Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
              </div>
              <div className="grid gap-2">
                <Label>End Time</Label>
                <Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Type</Label>
              <Select value={form.slot_type} onValueChange={(v) => setForm({ ...form, slot_type: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="lecture">Lecture</SelectItem>
                  <SelectItem value="lab">Lab</SelectItem>
                  <SelectItem value="break">Break</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Order</Label>
              <Input type="number" min={1} max={20} value={form.slot_order} onChange={(e) => setForm({ ...form, slot_order: parseInt(e.target.value) || 1 })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={!form.label || !form.start_time || !form.end_time}>
              {editingSlot ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
