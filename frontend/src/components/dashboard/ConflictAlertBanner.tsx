import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ConflictAlertBannerProps {
  count: number;
  timetableId: string;
}

export function ConflictAlertBanner({ count, timetableId }: ConflictAlertBannerProps) {
  if (count === 0) return null;

  return (
    <div className="bg-chip-orange-bg rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 text-chip-orange-txt" />
        <span className="text-sm font-medium text-chip-orange-txt">
          {count} high-priority conflict{count > 1 ? "s" : ""} detected
        </span>
      </div>
      <Link to={`/timetable/conflicts/${timetableId}`}>
        <Button
          size="sm"
          className="rounded-xl btn-press gap-1.5 bg-chip-orange-txt hover:bg-chip-orange-txt/90 text-primary-foreground"
        >
          Resolve Now <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </Link>
    </div>
  );
}
