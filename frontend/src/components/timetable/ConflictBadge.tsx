import { AlertTriangle } from "lucide-react";
import type { ConflictSeverity } from "@/types";

interface ConflictBadgeProps {
  severity: ConflictSeverity;
  count?: number;
}

const severityStyles: Record<ConflictSeverity, string> = {
  HIGH: "chip-red",
  MEDIUM: "chip-orange",
  LOW: "chip-yellow",
};

export function ConflictBadge({ severity, count }: ConflictBadgeProps) {
  return (
    <span className={`chip ${severityStyles[severity]} gap-1`}>
      <AlertTriangle className="h-3 w-3" />
      {count !== undefined ? `${count} ${severity}` : severity}
    </span>
  );
}
