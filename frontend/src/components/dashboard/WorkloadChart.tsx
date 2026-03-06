import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";

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

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20, top: 0, bottom: 0 }}>
        <XAxis type="number" domain={[0, 30]} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="name" width={60} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip
          formatter={(value: number, _name: string, props: { payload: WorkloadItem }) => [`${value}/${props.payload.max} hrs`, "Workload"]}
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
