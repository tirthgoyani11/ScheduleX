import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Label } from "recharts";

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

  // Group data by department
  const groupedData: { dept: string; faculty: WorkloadItem[] }[] = [];
  const deptMap = new Map<string, WorkloadItem[]>();
  
  data.forEach((item) => {
    const dept = item.deptCode || "Unknown";
    if (!deptMap.has(dept)) {
      deptMap.set(dept, []);
    }
    deptMap.get(dept)!.push(item);
  });

  // Convert to array and sort departments
  Array.from(deptMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([dept, faculty]) => {
      groupedData.push({ dept, faculty });
    });

  // If only one department, hide department headers for cleaner view
  const showDeptHeaders = groupedData.length > 1;

  return (
    <div className="space-y-1">
      {groupedData.map(({ dept, faculty }) => (
        <div key={dept} className="mb-4">
          {showDeptHeaders && (
            <div className="mb-2 px-2 py-1.5 bg-muted/50 rounded-md">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {dept} Department
              </h4>
            </div>
          )}
          <ResponsiveContainer width="100%" height={Math.max(150, faculty.length * 35)}>
            <BarChart data={faculty} layout="vertical" margin={{ left: 5, right: 20, top: 5, bottom: 5 }}>
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
                {faculty.map((entry) => (
                  <Cell key={entry.name} fill={getColor(entry.percentage)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}
