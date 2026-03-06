import { useState, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { CalendarClock, RefreshCw, UserPlus, BookPlus, Check, X, Loader2, Search } from "lucide-react";
import { useScheduling } from "@/hooks/useScheduling";
import { useTimetable } from "@/hooks/useTimetable";
import { useFaculty } from "@/hooks/useFaculty";
import { useSubjects } from "@/hooks/useSubjects";
import { useAuthStore } from "@/store/useAuthStore";
import type { BookingStatus, FreeSlotWithRooms, FreeRoom, Timetable, DateSlotCheck } from "@/types";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const statusColor: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  approved: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  cancelled: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
};

export default function SchedulingPage() {
  const user = useAuthStore((s) => s.user);
  const isHOD = user?.role === "dept_admin" || user?.role === "super_admin";
  const { data: timetables } = useTimetable();
  const publishedTT = useMemo(
    () => timetables.filter((t: Timetable) => t.status.toUpperCase() === "PUBLISHED"),
    [timetables]
  );
  const [selectedTT, setSelectedTT] = useState<string>("");
  const ttId = selectedTT || publishedTT[0]?.timetable_id || "";

  const scheduling = useScheduling(ttId);
  const { data: bookings = [], isLoading: bookingsLoading } = scheduling.useBookings();
  const { data: allFaculty = [] } = useFaculty();
  const { data: subjects = [] } = useSubjects();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scheduling Management"
        description="Reschedule lectures, assign proxies, and book extra lectures"
      />

      {/* Timetable selector */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-4">
            <Label className="whitespace-nowrap font-medium">Published Timetable:</Label>
            <Select value={ttId} onValueChange={setSelectedTT}>
              <SelectTrigger className="w-80">
                <SelectValue placeholder="Select timetable" />
              </SelectTrigger>
              <SelectContent>
                {publishedTT.map((t: Timetable) => (
                  <SelectItem key={t.timetable_id} value={t.timetable_id}>
                    Sem {t.semester} — {t.academic_year} (Score: {t.optimization_score ?? "N/A"})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {!ttId ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">No published timetable available. Generate and publish one first.</CardContent></Card>
      ) : (
        <Tabs defaultValue="bookings">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="bookings" className="gap-1"><CalendarClock className="h-4 w-4" />Bookings</TabsTrigger>
            <TabsTrigger value="slot-check" className="gap-1"><Search className="h-4 w-4" />Slot Check</TabsTrigger>
            <TabsTrigger value="reschedule" className="gap-1"><RefreshCw className="h-4 w-4" />Reschedule</TabsTrigger>
            <TabsTrigger value="extra" className="gap-1"><BookPlus className="h-4 w-4" />Extra Lecture</TabsTrigger>
            {isHOD && <TabsTrigger value="proxy" className="gap-1"><UserPlus className="h-4 w-4" />Proxy</TabsTrigger>}
          </TabsList>

          {/* ── Bookings Tab ──────────────────────────────── */}
          <TabsContent value="bookings">
            <BookingsTable
              bookings={bookings}
              isLoading={bookingsLoading}
              isHOD={isHOD}
              onApprove={(id) => scheduling.approveMutation.mutate(id)}
              onReject={(id) => scheduling.rejectMutation.mutate(id)}
              onCancel={(id) => scheduling.cancelMutation.mutate(id)}
            />
          </TabsContent>

          {/* ── Slot Check Tab ────────────────────────────── */}
          <TabsContent value="slot-check">
            <SlotCheckPanel scheduling={scheduling} />
          </TabsContent>

          {/* ── Reschedule Tab ────────────────────────────── */}
          <TabsContent value="reschedule">
            <RescheduleForm
              ttId={ttId}
              timetable={publishedTT.find((t: Timetable) => t.timetable_id === ttId)}
              scheduling={scheduling}
              isHOD={isHOD}
            />
          </TabsContent>

          {/* ── Extra Lecture Tab ──────────────────────────── */}
          <TabsContent value="extra">
            <ExtraLectureForm
              ttId={ttId}
              scheduling={scheduling}
              subjects={subjects}
              faculty={allFaculty}
              isHOD={isHOD}
            />
          </TabsContent>

          {/* ── Proxy Tab (HOD only) ──────────────────────── */}
          {isHOD && (
            <TabsContent value="proxy">
              <ProxyForm
                ttId={ttId}
                timetable={publishedTT.find((t: Timetable) => t.timetable_id === ttId)}
                scheduling={scheduling}
              />
            </TabsContent>
          )}
        </Tabs>
      )}
    </div>
  );
}


// ── Bookings Table ───────────────────────────────────────────

function BookingsTable({
  bookings,
  isLoading,
  isHOD,
  onApprove,
  onReject,
  onCancel,
}: {
  bookings: any[];
  isLoading: boolean;
  isHOD: boolean;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  if (isLoading) return <Card><CardContent className="py-12 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></CardContent></Card>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">All Bookings</CardTitle>
      </CardHeader>
      <CardContent>
        {bookings.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No bookings yet</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Faculty</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Day / Period</TableHead>
                  <TableHead>Room</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Requested By</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bookings.map((b: any) => (
                  <TableRow key={b.booking_id}>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {b.booking_type.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{b.faculty_name}</TableCell>
                    <TableCell>{b.subject_name}</TableCell>
                    <TableCell>{b.day}, P{b.period}</TableCell>
                    <TableCell>{b.room_name}</TableCell>
                    <TableCell>{b.target_date || "—"}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[b.status] || ""}`}>
                        {b.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{b.requested_by_name}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {isHOD && b.status === "pending" && (
                          <>
                            <Button size="sm" variant="ghost" className="h-7 text-green-600" onClick={() => onApprove(b.booking_id)}>
                              <Check className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" className="h-7 text-red-600" onClick={() => onReject(b.booking_id)}>
                              <X className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {(b.status === "pending" || b.status === "approved") && (
                          <Button size="sm" variant="ghost" className="h-7 text-muted-foreground" onClick={() => onCancel(b.booking_id)}>
                            Cancel
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}


// ── Reschedule Form ──────────────────────────────────────────

function RescheduleForm({
  ttId,
  timetable,
  scheduling,
  isHOD,
}: {
  ttId: string;
  timetable?: Timetable;
  scheduling: ReturnType<typeof useScheduling>;
  isHOD: boolean;
}) {
  const [entryId, setEntryId] = useState("");
  const [selectedSlot, setSelectedSlot] = useState<{ day: string; period: number } | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [reason, setReason] = useState("");

  const entry = timetable?.entries.find((e) => e.entry_id === entryId);

  // Auto-fetch free slots + rooms when an entry is selected (optionally filtered by date)
  const { data: options = [], isLoading: optionsLoading } = scheduling.useRescheduleOptions(
    entryId || undefined, targetDate || undefined
  );

  // Find the rooms for the currently selected slot
  const selectedSlotData = selectedSlot
    ? options.find((o) => o.day === selectedSlot.day && o.period === selectedSlot.period)
    : null;

  const handleSelectEntry = (id: string) => {
    setEntryId(id);
    setSelectedSlot(null);
    setSelectedRoomId("");
  };

  const handleSelectSlot = (day: string, period: number) => {
    setSelectedSlot({ day, period });
    setSelectedRoomId("");
  };

  const handleSubmit = () => {
    if (!entryId || !selectedSlot || !selectedRoomId) return;
    scheduling.rescheduleMutation.mutate({
      original_entry_id: entryId,
      new_day: selectedSlot.day,
      new_period: selectedSlot.period,
      new_room_id: selectedRoomId,
      target_date: targetDate || undefined,
      reason: reason || undefined,
    });
  };

  // Group entries by faculty for selection
  const entries = timetable?.entries.filter((e) => e.entry_type === "regular") || [];
  const grouped = useMemo(() => {
    const m = new Map<string, typeof entries>();
    for (const e of entries) {
      if (!m.has(e.faculty_name)) m.set(e.faculty_name, []);
      m.get(e.faculty_name)!.push(e);
    }
    return m;
  }, [entries]);

  // Group options by day for display
  const optionsByDay = useMemo(() => {
    const m = new Map<string, FreeSlotWithRooms[]>();
    for (const o of options) {
      if (!m.has(o.day)) m.set(o.day, []);
      m.get(o.day)!.push(o);
    }
    return m;
  }, [options]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Reschedule a Lecture</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Step 1 — Select entry + optional date */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2 md:col-span-2">
            <Label>Step 1: Select Lecture to Reschedule</Label>
            <Select value={entryId} onValueChange={handleSelectEntry}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a lecture..." />
              </SelectTrigger>
              <SelectContent>
                {Array.from(grouped.entries()).map(([fName, entryList]) => (
                  entryList.map((e) => (
                    <SelectItem key={e.entry_id} value={e.entry_id}>
                      {fName} — {e.subject_name} ({e.day}, P{e.period})
                    </SelectItem>
                  ))
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Target Date (optional — filters to that day)</Label>
            <Input
              type="date"
              value={targetDate}
              onChange={(e) => { setTargetDate(e.target.value); setSelectedSlot(null); setSelectedRoomId(""); }}
            />
          </div>
        </div>

        {entryId && entry && (
          <div className="rounded-lg border p-3 bg-muted/50 text-sm space-y-1">
            <p><strong>Current:</strong> {entry.day}, Period {entry.period}</p>
            <p><strong>Subject:</strong> {entry.subject_name}</p>
            <p><strong>Faculty:</strong> {entry.faculty_name}</p>
            <p><strong>Room:</strong> {entry.room_name}</p>
            {targetDate && <p><strong>Checking for:</strong> {targetDate} ({new Date(targetDate + "T00:00").toLocaleDateString("en-US", { weekday: "long" })})</p>}
          </div>
        )}

        {/* Step 2 — Auto-fetched free slots */}
        {entryId && (
          <div className="space-y-2">
            <Label>Step 2: Select a Free Slot (faculty &amp; students both free)</Label>
            {optionsLoading ? (
              <div className="flex items-center gap-2 py-4 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Finding available slots...
              </div>
            ) : options.length === 0 ? (
              <p className="text-sm text-muted-foreground py-2">No free slots found where both faculty and students are available.</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Day</TableHead>
                      <TableHead>Period</TableHead>
                      <TableHead>Time</TableHead>
                      <TableHead>Free Rooms</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {options.map((opt) => {
                      const isSelected = selectedSlot?.day === opt.day && selectedSlot?.period === opt.period;
                      return (
                        <TableRow
                          key={`${opt.day}-${opt.period}`}
                          className={`cursor-pointer transition-colors ${isSelected ? "bg-primary/10" : "hover:bg-muted/50"}`}
                          onClick={() => handleSelectSlot(opt.day, opt.period)}
                        >
                          <TableCell className="font-medium">{opt.day}</TableCell>
                          <TableCell>P{opt.period} — {opt.slot_label}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{opt.start_time} – {opt.end_time}</TableCell>
                          <TableCell>
                            <Badge variant="secondary">{opt.free_rooms.length} room{opt.free_rooms.length !== 1 ? "s" : ""}</Badge>
                          </TableCell>
                          <TableCell>
                            {isSelected && <Check className="h-4 w-4 text-primary" />}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}

        {/* Step 3 — Select room for the chosen slot */}
        {selectedSlot && selectedSlotData && (
          <div className="space-y-2">
            <Label>Step 3: Select Room ({selectedSlotData.free_rooms.length} available on {selectedSlot.day}, P{selectedSlot.period})</Label>
            <Select value={selectedRoomId} onValueChange={setSelectedRoomId}>
              <SelectTrigger className="w-full md:w-96">
                <SelectValue placeholder="Select a room..." />
              </SelectTrigger>
              <SelectContent>
                {selectedSlotData.free_rooms.map((r) => (
                  <SelectItem key={r.room_id} value={r.room_id}>
                    {r.room_name} ({r.room_type}, {r.capacity} seats)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Optional: reason */}
        {selectedRoomId && (
          <div className="space-y-2">
            <Label>Reason (optional)</Label>
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this being rescheduled?" rows={2} />
          </div>
        )}

        <Button
          onClick={handleSubmit}
          disabled={!entryId || !selectedSlot || !selectedRoomId || scheduling.rescheduleMutation.isPending}
          className="gap-2"
        >
          {scheduling.rescheduleMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          <RefreshCw className="h-4 w-4" />
          {isHOD ? "Reschedule (Auto-approve)" : "Request Reschedule"}
        </Button>
      </CardContent>
    </Card>
  );
}


// ── Extra Lecture Form ────────────────────────────────────────

function ExtraLectureForm({
  ttId,
  scheduling,
  subjects,
  faculty,
  isHOD,
}: {
  ttId: string;
  scheduling: ReturnType<typeof useScheduling>;
  subjects: any[];
  faculty: any[];
  isHOD: boolean;
}) {
  const [subjectId, setSubjectId] = useState("");
  const [day, setDay] = useState("");
  const [period, setPeriod] = useState<number | undefined>();
  const [roomId, setRoomId] = useState("");
  const [facultyId, setFacultyId] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [reason, setReason] = useState("");

  const { data: freeRooms = [] } = scheduling.useFreeRooms(day || undefined, period);

  const handleSubmit = () => {
    if (!subjectId || !day || !period || !roomId) return;
    if (isHOD) {
      if (!facultyId) return;
      scheduling.extraLectureAssignMutation.mutate({
        faculty_id: facultyId,
        subject_id: subjectId,
        day,
        period,
        room_id: roomId,
        target_date: targetDate || undefined,
        reason: reason || undefined,
      });
    } else {
      scheduling.extraLectureMutation.mutate({
        subject_id: subjectId,
        day,
        period,
        room_id: roomId,
        target_date: targetDate || undefined,
        reason: reason || undefined,
      });
    }
  };

  // Show free faculty for HOD at selected slot
  const { data: freeFacultyAtSlot = [] } = scheduling.useFreeFaculty(day || undefined, period);

  const isPending = scheduling.extraLectureMutation.isPending || scheduling.extraLectureAssignMutation.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Book Extra Lecture</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>Subject</Label>
            <Select value={subjectId} onValueChange={setSubjectId}>
              <SelectTrigger><SelectValue placeholder="Select subject" /></SelectTrigger>
              <SelectContent>
                {subjects.map((s: any) => (
                  <SelectItem key={s.subject_id} value={s.subject_id}>{s.name} ({s.subject_code})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Day</Label>
            <Select value={day} onValueChange={setDay}>
              <SelectTrigger><SelectValue placeholder="Day" /></SelectTrigger>
              <SelectContent>
                {DAYS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Period</Label>
            <Input type="number" min={1} max={10} value={period ?? ""} onChange={(e) => setPeriod(Number(e.target.value) || undefined)} placeholder="Period #" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>Room ({freeRooms.length} free)</Label>
            <Select value={roomId} onValueChange={setRoomId}>
              <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
              <SelectContent>
                {freeRooms.map((r) => (
                  <SelectItem key={r.room_id} value={r.room_id}>{r.room_name} ({r.room_type}, {r.capacity})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {isHOD && (
            <div className="space-y-2">
              <Label>Faculty ({freeFacultyAtSlot.length} free)</Label>
              <Select value={facultyId} onValueChange={setFacultyId}>
                <SelectTrigger><SelectValue placeholder="Select faculty" /></SelectTrigger>
                <SelectContent>
                  {freeFacultyAtSlot.map((f) => (
                    <SelectItem key={f.faculty_id} value={f.faculty_id}>
                      {f.name} (Load: {f.current_load}/{f.max_weekly_load})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <Label>Target Date (optional)</Label>
            <Input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Reason (optional)</Label>
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is an extra lecture needed?" rows={2} />
        </div>

        {/* Free slots preview */}
        {day && (
          <FreeSlotPreview ttId={ttId} scheduling={scheduling} day={day} />
        )}

        <Button
          onClick={handleSubmit}
          disabled={!subjectId || !day || !period || !roomId || (isHOD && !facultyId) || isPending}
          className="gap-2"
        >
          {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          <BookPlus className="h-4 w-4" />
          {isHOD ? "Assign Extra Lecture" : "Request Extra Lecture"}
        </Button>
      </CardContent>
    </Card>
  );
}


// ── Free Slot Preview ──────────────────────────────────────────

function FreeSlotPreview({
  ttId,
  scheduling,
  day,
}: {
  ttId: string;
  scheduling: ReturnType<typeof useScheduling>;
  day: string;
}) {
  // For faculty users we don't know faculty_id here, skip preview for now
  // This shows free rooms at each period for the selected day
  return (
    <div className="rounded-lg border p-3 bg-muted/30">
      <p className="text-sm font-medium mb-2">Free rooms on {day} — click a period above to see available rooms</p>
    </div>
  );
}


// ── Slot Check Panel ───────────────────────────────────────────

function SlotCheckPanel({
  scheduling,
}: {
  scheduling: ReturnType<typeof useScheduling>;
}) {
  const [date, setDate] = useState("");
  const [expandedPeriod, setExpandedPeriod] = useState<number | null>(null);

  const { data: result, isLoading } = scheduling.useDateCheck(date || undefined);

  const togglePeriod = (period: number) => {
    setExpandedPeriod((prev) => (prev === period ? null : period));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Check Slot Availability by Date</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Pick a date to see room and faculty availability for every time slot.
          This considers both the regular timetable and any approved bookings (reschedules, extra lectures, proxies) on that specific date.
        </p>

        <div className="flex items-end gap-4">
          <div className="space-y-2">
            <Label>Select Date</Label>
            <Input
              type="date"
              value={date}
              onChange={(e) => { setDate(e.target.value); setExpandedPeriod(null); }}
              className="w-56"
            />
          </div>
          {result && (
            <Badge variant="outline" className="h-9 text-sm px-4">
              {result.day_of_week}, {result.date}
            </Badge>
          )}
        </div>

        {isLoading && (
          <div className="flex items-center gap-2 py-6 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking availability...
          </div>
        )}

        {result && (
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Period</TableHead>
                  <TableHead className="w-32">Time</TableHead>
                  <TableHead>Free Rooms</TableHead>
                  <TableHead>Busy Rooms</TableHead>
                  <TableHead>Free Faculty</TableHead>
                  <TableHead>Busy Faculty</TableHead>
                  <TableHead className="w-16"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.slots.map((slot: DateSlotCheck) => (
                  <>
                    <TableRow
                      key={slot.period}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => togglePeriod(slot.period)}
                    >
                      <TableCell className="font-medium">P{slot.period} — {slot.slot_label}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{slot.start_time} – {slot.end_time}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                          {slot.free_rooms.length} free
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                          {slot.busy_rooms.length} busy
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                          {slot.free_faculty.length} free
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                          {slot.busy_faculty.length} busy
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="text-xs text-muted-foreground">{expandedPeriod === slot.period ? "▲" : "▼"}</span>
                      </TableCell>
                    </TableRow>
                    {expandedPeriod === slot.period && (
                      <TableRow key={`${slot.period}-detail`}>
                        <TableCell colSpan={7} className="bg-muted/30 p-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Rooms */}
                            <div>
                              <h4 className="font-medium text-sm mb-2">Rooms</h4>
                              <div className="space-y-1">
                                {slot.free_rooms.map((r) => (
                                  <div key={r.room_id} className="flex items-center gap-2 text-sm">
                                    <span className="h-2 w-2 rounded-full bg-green-500" />
                                    {r.room_name}
                                    <span className="text-muted-foreground text-xs">({r.room_type}, {r.capacity} seats)</span>
                                  </div>
                                ))}
                                {slot.busy_rooms.map((r) => (
                                  <div key={r.room_id} className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <span className="h-2 w-2 rounded-full bg-red-500" />
                                    {r.room_name}
                                    <span className="text-xs">({r.room_type}, {r.capacity} seats)</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                            {/* Faculty */}
                            <div>
                              <h4 className="font-medium text-sm mb-2">Faculty</h4>
                              <div className="space-y-1">
                                {slot.free_faculty.map((f) => (
                                  <div key={f.faculty_id} className="flex items-center gap-2 text-sm">
                                    <span className="h-2 w-2 rounded-full bg-green-500" />
                                    {f.name}
                                    <span className="text-muted-foreground text-xs">(Load: {f.current_load}/{f.max_weekly_load})</span>
                                  </div>
                                ))}
                                {slot.busy_faculty.map((f) => (
                                  <div key={f.faculty_id} className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <span className="h-2 w-2 rounded-full bg-red-500" />
                                    {f.name}
                                    <span className="text-xs capitalize">({f.reason.replace("_", " ")})</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {date && !isLoading && !result && (
          <p className="text-sm text-muted-foreground py-2">No data returned. Make sure it's a valid weekday.</p>
        )}
      </CardContent>
    </Card>
  );
}


// ── Proxy Form (HOD only) ──────────────────────────────────────

function ProxyForm({
  ttId,
  timetable,
  scheduling,
}: {
  ttId: string;
  timetable?: Timetable;
  scheduling: ReturnType<typeof useScheduling>;
}) {
  const [entryId, setEntryId] = useState("");
  const [proxyFacultyId, setProxyFacultyId] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [reason, setReason] = useState("");

  const entry = timetable?.entries.find((e) => e.entry_id === entryId);

  // Free faculty at the entry's slot
  const { data: freeFac = [] } = scheduling.useFreeFaculty(
    entry?.day || undefined,
    entry?.period
  );

  const handleSubmit = () => {
    if (!entryId || !proxyFacultyId || !targetDate) return;
    scheduling.proxyMutation.mutate({
      original_entry_id: entryId,
      proxy_faculty_id: proxyFacultyId,
      target_date: targetDate,
      reason: reason || undefined,
    });
  };

  // Group entries by faculty
  const entries = timetable?.entries.filter((e) => e.entry_type === "regular") || [];
  const grouped = useMemo(() => {
    const m = new Map<string, typeof entries>();
    for (const e of entries) {
      if (!m.has(e.faculty_name)) m.set(e.faculty_name, []);
      m.get(e.faculty_name)!.push(e);
    }
    return m;
  }, [entries]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Assign Proxy Faculty</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          When a faculty is unavailable, assign another free faculty to cover their class.
          The system shows only faculty who are free at that particular slot.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Select Class to Cover</Label>
            <Select value={entryId} onValueChange={(v) => { setEntryId(v); setProxyFacultyId(""); }}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a lecture..." />
              </SelectTrigger>
              <SelectContent>
                {Array.from(grouped.entries()).map(([fName, entryList]) => (
                  entryList.map((e) => (
                    <SelectItem key={e.entry_id} value={e.entry_id}>
                      {fName} — {e.subject_name} ({e.day}, P{e.period})
                    </SelectItem>
                  ))
                ))}
              </SelectContent>
            </Select>
          </div>

          {entry && (
            <div className="rounded-lg border p-3 bg-muted/50 text-sm space-y-1">
              <p><strong>Class:</strong> {entry.subject_name}</p>
              <p><strong>Original Faculty:</strong> {entry.faculty_name}</p>
              <p><strong>Slot:</strong> {entry.day}, Period {entry.period}</p>
              <p><strong>Room:</strong> {entry.room_name}</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>Proxy Faculty ({freeFac.length} available)</Label>
            <Select value={proxyFacultyId} onValueChange={setProxyFacultyId}>
              <SelectTrigger><SelectValue placeholder="Select proxy" /></SelectTrigger>
              <SelectContent>
                {freeFac
                  .filter((f) => entry ? f.name !== entry.faculty_name : true)
                  .map((f) => (
                    <SelectItem key={f.faculty_id} value={f.faculty_id}>
                      {f.name} (Load: {f.current_load}/{f.max_weekly_load})
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Date of Absence</Label>
            <Input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Reason (optional)</Label>
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for absence..." rows={2} />
          </div>
        </div>

        <Button
          onClick={handleSubmit}
          disabled={!entryId || !proxyFacultyId || !targetDate || scheduling.proxyMutation.isPending}
          className="gap-2"
        >
          {scheduling.proxyMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          <UserPlus className="h-4 w-4" />
          Assign Proxy
        </Button>
      </CardContent>
    </Card>
  );
}
