import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

interface RoomData {
  name: string;
  value: number;
  fill: string;
}

export function RoomUtilizationChart({ data, percentage }: { data: RoomData[]; percentage: number }) {
  const allZero = data.every((d) => d.value === 0);

  // When all values are 0, show a grey background ring
  const chartData = allZero
    ? [{ name: "Unused", value: 100, fill: "hsl(var(--muted))" }]
    : data;

  // Show top rooms sorted by utilization, limit legend to avoid overflow
  const topRooms = [...data].sort((a, b) => b.value - a.value).slice(0, 6);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <ResponsiveContainer width={200} height={200}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={90}
              dataKey="value"
              startAngle={90}
              endAngle={-270}
            >
              {chartData.map((entry, i) => (
                <Cell key={`${entry.name}-${i}`} fill={entry.fill} strokeWidth={0} />
              ))}
            </Pie>
            {!allZero && (
              <Tooltip
                formatter={(value: number) => [`${value}%`, "Utilization"]}
                contentStyle={{ borderRadius: 12, border: "1px solid hsl(var(--border))", fontSize: 12 }}
              />
            )}
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-3xl font-semibold font-display">{percentage}%</span>
        </div>
      </div>
      <div className="flex flex-wrap justify-center gap-x-3 gap-y-1.5 max-w-full px-2">
        {topRooms.map((d) => (
          <div key={d.name} className="flex items-center gap-1.5 text-xs whitespace-nowrap">
            <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: d.fill }} />
            <span className="text-muted-foreground truncate max-w-[80px]">{d.name}</span>
          </div>
        ))}
        {data.length > 6 && (
          <span className="text-xs text-muted-foreground">+{data.length - 6} more</span>
        )}
      </div>
    </div>
  );
}
