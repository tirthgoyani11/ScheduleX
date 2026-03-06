import { useState } from "react";
import { Building2, Save, Globe, Clock, Calendar } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useAuthStore } from "@/store/useAuthStore";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [collegeName, setCollegeName] = useState("CVM University");
  const [academicYear, setAcademicYear] = useState("2025-26");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [autoConflictCheck, setAutoConflictCheck] = useState(true);
  const [allowSaturdayClasses, setAllowSaturdayClasses] = useState(false);
  const [maxDailyHours, setMaxDailyHours] = useState("8");
  const [defaultSlotDuration, setDefaultSlotDuration] = useState("60");

  const handleSave = () => {
    toast.success("Settings saved successfully");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader title="School Settings" description="Configure institution-wide preferences">
        <Button onClick={handleSave} className="rounded-xl btn-press gap-2">
          <Save className="h-4 w-4" />Save Changes
        </Button>
      </PageHeader>

      {/* Institution Info */}
       <div className="bg-card rounded-lg shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-3 mb-1">
          <div className="h-9 w-9 rounded-xl bg-chip-blue-bg flex items-center justify-center">
            <Building2 className="h-4.5 w-4.5 text-chip-blue-txt" />
          </div>
          <h3 className="text-base font-medium font-display">Institution Details</h3>
        </div>
        <Separator />
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>College Name</Label>
            <Input className="rounded-xl" value={collegeName} onChange={(e) => setCollegeName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Academic Year</Label>
              <Input className="rounded-xl" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Asia/Kolkata">Asia/Kolkata (IST)</SelectItem>
                  <SelectItem value="America/New_York">America/New York (EST)</SelectItem>
                  <SelectItem value="Europe/London">Europe/London (GMT)</SelectItem>
                  <SelectItem value="Asia/Singapore">Asia/Singapore (SGT)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>

      {/* Departments */}
       <div className="bg-card rounded-lg shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-3 mb-1">
          <div className="h-9 w-9 rounded-xl bg-chip-purple-bg flex items-center justify-center">
            <Globe className="h-4.5 w-4.5 text-chip-purple-txt" />
          </div>
          <h3 className="text-base font-medium font-display">Departments</h3>
        </div>
        <Separator />
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 rounded-xl hover:bg-accent/50 transition-colors">
            <div>
              <p className="text-sm font-medium">Computer Engineering</p>
              <p className="text-xs font-mono text-muted-foreground">CE</p>
            </div>
            <span className="chip chip-blue">CE</span>
          </div>
        </div>
      </div>

      {/* Scheduling Preferences */}
       <div className="bg-card rounded-lg shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-3 mb-1">
          <div className="h-9 w-9 rounded-xl bg-chip-green-bg flex items-center justify-center">
            <Clock className="h-4.5 w-4.5 text-chip-green-txt" />
          </div>
          <h3 className="text-base font-medium font-display">Scheduling Preferences</h3>
        </div>
        <Separator />
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Auto Conflict Detection</p>
              <p className="text-xs text-muted-foreground">Automatically check for conflicts during generation</p>
            </div>
            <Switch checked={autoConflictCheck} onCheckedChange={setAutoConflictCheck} />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Saturday Classes</p>
              <p className="text-xs text-muted-foreground">Allow scheduling classes on Saturday</p>
            </div>
            <Switch checked={allowSaturdayClasses} onCheckedChange={setAllowSaturdayClasses} />
          </div>
          <Separator />
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Max Daily Hours per Faculty</Label>
              <Select value={maxDailyHours} onValueChange={setMaxDailyHours}>
                <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[4, 5, 6, 7, 8, 9, 10].map((h) => (
                    <SelectItem key={h} value={String(h)}>{h} hours</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Default Slot Duration</Label>
              <Select value={defaultSlotDuration} onValueChange={setDefaultSlotDuration}>
                <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="45">45 minutes</SelectItem>
                  <SelectItem value="50">50 minutes</SelectItem>
                  <SelectItem value="60">60 minutes</SelectItem>
                  <SelectItem value="90">90 minutes</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </div>

      {/* Academic Calendar */}
      <div className="bg-card rounded-lg shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-3 mb-1">
          <div className="h-9 w-9 rounded-xl bg-chip-orange-bg flex items-center justify-center">
            <Calendar className="h-4.5 w-4.5 text-chip-orange-txt" />
          </div>
          <h3 className="text-base font-medium font-display">Academic Calendar</h3>
        </div>
        <Separator />
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-border space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Odd Semester</p>
            <p className="text-sm font-medium">Jul 2025 – Dec 2025</p>
          </div>
          <div className="p-4 rounded-xl border border-border space-y-1">
            <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Even Semester</p>
            <p className="text-sm font-medium">Jan 2026 – May 2026</p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {/* TODO: [FEATURE] Add holiday calendar management */}
          Holiday calendar management coming in Phase 2.
        </p>
      </div>
    </div>
  );
}
