type ChipVariant = "theory" | "lab" | "theory_lab" | "shared" | "conflict" | "approved" | "draft" | "high" | "medium" | "low" | "lecture" | "present" | "absent" | "published";

const variantMap: Record<ChipVariant, string> = {
  theory: "chip-purple",
  lab: "chip-green",
  theory_lab: "chip-blue",
  shared: "chip-pink",
  conflict: "chip-red",
  approved: "chip-green",
  draft: "chip-yellow",
  published: "chip-green",
  high: "chip-red",
  medium: "chip-orange",
  low: "chip-yellow",
  lecture: "chip-blue",
  present: "chip-green",
  absent: "chip-red",
};

interface StatusChipProps {
  variant: ChipVariant;
  label?: string;
}

export function StatusChip({ variant, label }: StatusChipProps) {
  return (
    <span className={`chip ${variantMap[variant]}`}>
      {label ?? variant.replace("_", " ").toUpperCase()}
    </span>
  );
}

export function getSubjectChipVariant(needsLab: boolean): ChipVariant {
  return needsLab ? "lab" : "theory";
}

export function getSlotChipVariant(type: string): ChipVariant {
  const lower = type.toLowerCase();
  if (lower === "lab") return "lab";
  if (lower === "break") return "conflict";
  return "lecture";
}

export function getSeverityChipVariant(s: string): ChipVariant {
  return s.toLowerCase() as ChipVariant;
}

export function getStatusChipVariant(s: string): ChipVariant {
  const lower = s.toLowerCase();
  if (lower === "published") return "published";
  if (lower === "draft") return "draft";
  return "conflict";
}
