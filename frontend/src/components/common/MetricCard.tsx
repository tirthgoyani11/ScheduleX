import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  icon: LucideIcon;
  value: string | number;
  label: string;
  trend?: { value: string; positive: boolean };
  chipClass?: string;
}

export function MetricCard({ icon: Icon, value, label, trend, chipClass = "chip-blue" }: MetricCardProps) {
  return (
    <div className="bg-card rounded-lg shadow-sm p-5 card-hover">
      <div className="flex items-start justify-between">
        <div className={`chip ${chipClass} !rounded-xl !p-2.5`}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <span className={`chip ${trend.positive ? "chip-green" : "chip-red"}`}>
            {trend.positive ? "↑" : "↓"} {trend.value}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-semibold font-display">{value}</p>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mt-1">{label}</p>
      </div>
    </div>
  );
}
