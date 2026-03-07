import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface WorkloadItem {
  name: string;
  fullName: string;
  current: number;
  max: number;
  percentage: number;
  deptCode?: string;
  deptId?: string;
}

export function WorkloadChart({ data }: { data: WorkloadItem[] }) {
  const getColor = (pct: number) => {
    if (pct >= 90) return "hsl(0, 72%, 51%)";
    if (pct >= 75) return "hsl(27, 96%, 48%)";
    return "hsl(142, 64%, 24%)";
  };

  const sortedData = [...data].sort((a, b) => a.name.localeCompare(b.name));
  const chartHeight = Math.max(180, sortedData.length * 35);

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={sortedData} layout="vertical" margin={{ left: 5, right: 20, top: 5, bottom: 5 }}>
        <XAxis type="number" domain={[0, "auto"]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis
          type="category"
          dataKey="name"
          width={100}
          tick={{ fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval={0}
        />
        <Tooltip
          formatter={(value: number, _name: string, props: { payload: WorkloadItem }) => [`${value}/${props.payload.max} hrs`, props.payload.fullName]}
          contentStyle={{ borderRadius: 12, border: "1px solid hsl(var(--border))", fontSize: 12 }}
        />
        <Bar dataKey="current" radius={[0, 6, 6, 0]} barSize={20}>
          {sortedData.map((entry) => (
            <Cell key={entry.name} fill={getColor(entry.percentage)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
