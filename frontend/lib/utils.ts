export function scoreColor(score: number | null): string {
  if (score === null) return '#9CA3AF'; // gray
  if (score >= 85) return '#22c55e'; // green
  if (score >= 70) return '#D97706'; // amber
  return '#C2410C'; // terracotta/red
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function formatDateLabel(label: unknown): string {
  if (typeof label === "string") return formatDate(label);
  return String(label ?? "");
}

export function formatDelta(delta: number | undefined): string {
  if (delta === undefined) return '';
  const sign = delta >= 0 ? '+' : '';
  return `${sign}${Math.round(delta)} vs 30d avg`;
}
