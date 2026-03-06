import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

interface RoomData {
  name: string;
  value: number;
  fill: string;
  capacity?: number;
  bookedSlots?: number;
  totalSlots?: number;
}

export function RoomUtilizationChart({ data, percentage }: { data: RoomData[]; percentage: number }) {
  const [query, setQuery] = useState("");

  const filteredRooms = useMemo(() => {
    const q = query.trim().toLowerCase();
    const source = [...data].sort((a, b) => b.value - a.value);
    if (!q) return source;
    return source.filter((room) => room.name.toLowerCase().includes(q));
  }, [data, query]);

  const utilizationBadge = (value: number) => {
    if (value >= 80) return "bg-red-100 text-red-700";
    if (value >= 60) return "bg-amber-100 text-amber-700";
    if (value >= 40) return "bg-sky-100 text-sky-700";
    if (value >= 20) return "bg-emerald-100 text-emerald-700";
    return "bg-slate-100 text-slate-700";
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{data.length} rooms</span>
        <span className="text-xs font-medium text-muted-foreground">Avg {percentage}%</span>
      </div>

        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search room name..."
          className="h-9"
        />

        <ScrollArea className="h-[280px] rounded-md border border-border/70 p-2">
          <div className="space-y-2 pr-3">
            {filteredRooms.map((room) => (
              <div
                key={room.name}
                className="rounded-md border border-border/60 p-2.5"
                style={{ background: `color-mix(in srgb, ${room.fill} 12%, hsl(var(--background)))` }}
              >
                <div className="mb-1.5 flex items-start justify-between gap-3">
                  <span className="text-xs font-medium" title={room.name}>{room.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${utilizationBadge(room.value)}`}>
                    {room.value}%
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-black/10">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${Math.max(0, Math.min(room.value, 100))}%`, backgroundColor: room.fill }}
                  />
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                  {typeof room.bookedSlots === "number" && typeof room.totalSlots === "number" && (
                    <span>{room.bookedSlots}/{room.totalSlots} slots booked</span>
                  )}
                  {typeof room.capacity === "number" && <span>Capacity {room.capacity}</span>}
                </div>
              </div>
            ))}
            {filteredRooms.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">No rooms match your search.</p>
            )}
          </div>
        </ScrollArea>
    </div>
  );
}
