import { AlertTriangle, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusChip, getSeverityChipVariant } from "@/components/common/StatusChip";
import type { Conflict, ConflictStatus } from "@/types";

const severityBorder: Record<string, string> = {
  HIGH: "border-l-4 border-l-destructive",
  MEDIUM: "border-l-4 border-l-chip-orange-txt",
  LOW: "border-l-4 border-l-chip-yellow-txt",
};

interface ConflictListProps {
  conflicts: Conflict[];
  onUpdateStatus: (id: string, status: ConflictStatus) => void;
}

export function ConflictList({ conflicts, onUpdateStatus }: ConflictListProps) {
  const unresolved = conflicts.filter((c) => c.status === "UNRESOLVED");
  const resolved = conflicts.filter((c) => c.status === "RESOLVED" || c.status === "IGNORED");

  return (
    <div className="space-y-4">
      {unresolved.map((conflict) => (
        <div key={conflict.id} className={`bg-card rounded-lg shadow-sm p-5 ${severityBorder[conflict.severity]}`}>
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle
                className={`h-4 w-4 ${
                  conflict.severity === "HIGH"
                    ? "text-destructive"
                    : conflict.severity === "MEDIUM"
                    ? "text-chip-orange-txt"
                    : "text-chip-yellow-txt"
                }`}
              />
              <StatusChip variant={getSeverityChipVariant(conflict.severity)} />
              <span className="text-xs font-mono text-muted-foreground">{conflict.type}</span>
            </div>
          </div>
          <p className="text-sm mb-2">{conflict.description}</p>
          <div className="bg-accent/50 rounded-xl p-3 flex items-start gap-2 mb-4">
            <span className="text-sm">💡</span>
            <p className="text-sm text-muted-foreground">{conflict.suggestion}</p>
          </div>
          <div className="flex gap-2 justify-end">
            <Button
              variant="ghost"
              size="sm"
              className="rounded-xl gap-1.5 text-muted-foreground"
              onClick={() => onUpdateStatus(conflict.id, "IGNORED")}
            >
              <X className="h-3.5 w-3.5" />Ignore
            </Button>
            <Button
              size="sm"
              className="rounded-xl btn-press gap-1.5"
              onClick={() => onUpdateStatus(conflict.id, "RESOLVED")}
            >
              <Check className="h-3.5 w-3.5" />Apply Fix
            </Button>
          </div>
        </div>
      ))}

      {resolved.map((conflict) => (
        <div key={conflict.id} className="bg-card rounded-lg shadow-sm p-5 opacity-50">
          <div className="flex items-center gap-2 mb-2">
            <span className="chip chip-green">
              ✓ {conflict.status === "RESOLVED" ? "Resolved" : "Ignored"}
            </span>
            <span className="text-xs font-mono text-muted-foreground">{conflict.type}</span>
          </div>
          <p className="text-sm line-through text-muted-foreground">{conflict.description}</p>
        </div>
      ))}
    </div>
  );
}
