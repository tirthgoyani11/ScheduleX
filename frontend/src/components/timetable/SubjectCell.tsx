import type { TimetableEntry } from "@/types";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

function getEntryColor(entryType: string): string {
  if (entryType === "lab") return "bg-subject-lab";
  return "bg-subject-theory";
}

interface SubjectCellProps {
  entry: TimetableEntry;
}

export function SubjectCell({ entry }: SubjectCellProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`min-h-[70px] rounded-xl p-3 relative ${getEntryColor(entry.entry_type)} hover:brightness-95 transition-all cursor-pointer`}
        >
          <p className="text-sm font-medium truncate">{entry.subject_name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{entry.faculty_name}</p>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[10px] text-muted-foreground">{entry.room_name}</span>
            {entry.batch && (
              <span className="chip chip-blue !text-[10px] !px-1.5 !py-0">{entry.batch}</span>
            )}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent className="rounded-xl p-3 max-w-[200px]">
        <p className="font-medium text-sm">{entry.subject_name}</p>
        <p className="text-xs mt-1">Faculty: {entry.faculty_name}</p>
        <p className="text-xs">Room: {entry.room_name}</p>
        {entry.batch && <p className="text-xs">Batch: {entry.batch}</p>}
      </TooltipContent>
    </Tooltip>
  );
}
