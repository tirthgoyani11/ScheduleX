import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface WorkloadItem {
  name: string;
  fullName: string;
  current: number;
  max: number;
  percentage: number;
}

export function WorkloadChart({ data }: { data: WorkloadItem[] }) {
  const getColor = (pct: number) => {
    if (pct >= 90) return "hsl(0, 72%, 51%)";
    if (pct >= 75) return "hsl(27, 96%, 48%)";
    return "hsl(142, 64%, 24%)";
  };

  // Dynamic height: 40px per bar, min 200, max 500 for better visibility
  const chartHeight = Math.min(500, Math.max(200, data.length * 40));

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
        <XAxis type="number" domain={[0, "auto"]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis 
          type="category" 
          dataKey="name" 
          width={80} 
          tick={{ fontSize: 11 }} 
          tickLine={false} 
          axisLine={false}
          interval={0}
        />
        <Tooltip
          formatter={(value: number, _name: string, props: { payload: WorkloadItem }) => [`${value}/${props.payload.max} hrs`, props.payload.fullName]}
          contentStyle={{ borderRadius: 12, border: "1px solid hsl(var(--border))", fontSize: 12 }}
        />
        <Bar dataKey="current" radius={[0, 6, 6, 0]} barSize={20}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={getColor(entry.percentage)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
