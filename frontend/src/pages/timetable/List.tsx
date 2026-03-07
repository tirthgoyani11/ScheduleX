import { useState } from "react";
import { Link } from "react-router-dom";
import { Eye, Trash2, Send, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { StatusChip, getStatusChipVariant } from "@/components/common/StatusChip";
import { useTimetable } from "@/hooks/useTimetable";
import { useDepartments } from "@/hooks/useDepartments";
import { useAuthStore } from "@/store/useAuthStore";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Timetable } from "@/types";

export default function TimetableListPage() {
  const user = useAuthStore((s) => s.user);
  const isSuperAdmin = user?.role === "super_admin";
  const { data: departments } = useDepartments();
  const [selectedDeptId, setSelectedDeptId] = useState<string>("all");

  const deptIdParam = isSuperAdmin && selectedDeptId !== "all" ? selectedDeptId : undefined;
  const { data: timetables, isLoading, publish, remove } = useTimetable(undefined, deptIdParam);

  // Group timetables by department for super_admin "all" view
  const groupedByDept: Record<string, { name: string; timetables: Timetable[] }> = {};
  if (isSuperAdmin && selectedDeptId === "all") {
    for (const tt of timetables) {
      const key = tt.dept_id ?? "unknown";
      if (!groupedByDept[key]) {
        groupedByDept[key] = { name: tt.dept_name ?? "Unknown", timetables: [] };
      }
      groupedByDept[key].timetables.push(tt);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Timetables" description="View and manage generated timetables">
        {!isSuperAdmin && (
          <Link to="/timetable/generate">
            <Button className="rounded-xl btn-press">Generate New</Button>
          </Link>
        )}
      </PageHeader>

      {isSuperAdmin && (
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-muted-foreground">Department</label>
          <Select value={selectedDeptId} onValueChange={setSelectedDeptId}>
            <SelectTrigger className="w-[260px] rounded-xl">
              <SelectValue placeholder="All Departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              {departments.map((d) => (
                <SelectItem key={d.dept_id} value={d.dept_id}>
                  {d.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {timetables.length === 0 ? (
        <div className="bg-card rounded-lg shadow-sm p-12 text-center">
          <p className="text-muted-foreground">No timetables generated yet.</p>
          {!isSuperAdmin && (
            <Link to="/timetable/generate">
              <Button className="rounded-xl btn-press mt-4">Generate Your First Timetable</Button>
            </Link>
          )}
        </div>
      ) : isSuperAdmin && selectedDeptId === "all" ? (
        // Grouped view for super admin
        <div className="space-y-8">
          {Object.entries(groupedByDept).map(([deptId, group]) => (
            <div key={deptId}>
              <h3 className="text-lg font-semibold mb-3 text-primary">{group.name}</h3>
              <div className="space-y-3">
                {group.timetables.map((tt) => (
                  <TimetableCard key={tt.timetable_id} tt={tt} publish={publish} remove={remove} showDept={false} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {timetables.map((tt) => (
            <TimetableCard key={tt.timetable_id} tt={tt} publish={publish} remove={remove} showDept={isSuperAdmin} />
          ))}
        </div>
      )}
    </div>
  );
}

function TimetableCard({
  tt,
  publish,
  remove,
  showDept,
}: {
  tt: Timetable;
  publish: (id: string) => void;
  remove: (id: string) => void;
  showDept: boolean;
}) {
  return (
    <div className="bg-card rounded-lg shadow-sm p-5 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div>
          <p className="font-medium">
            {showDept && tt.dept_name && (
              <span className="text-primary">{tt.dept_name} · </span>
            )}
            Semester {tt.semester} · {tt.academic_year}
          </p>
          <p className="text-sm text-muted-foreground mt-0.5">
            {tt.entries.length} entries · Score: {tt.optimization_score ?? "N/A"}/100
          </p>
        </div>
        <StatusChip variant={getStatusChipVariant(tt.status)} label={tt.status} />
      </div>
      <div className="flex items-center gap-2">
        <Link to={`/timetable/view/${tt.timetable_id}`}>
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5">
            <Eye className="h-3.5 w-3.5" />View
          </Button>
        </Link>
        {tt.status.toUpperCase() === "DRAFT" && (
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={() => publish(tt.timetable_id)}>
            <Send className="h-3.5 w-3.5" />Publish
          </Button>
        )}
        <Button variant="ghost" size="sm" className="rounded-xl text-destructive" onClick={() => remove(tt.timetable_id)}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
