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

export function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase();
}

export function formatPulledAt(pulledAt: string): string {
  // Format from backend: "2026-02-24T08:46:47 CST"
  const tIdx = pulledAt.indexOf("T");
  if (tIdx === -1) return pulledAt;
  const timeTz = pulledAt.slice(tIdx + 1); // "08:46:47 CST"
  const spaceIdx = timeTz.indexOf(" ");
  const time = spaceIdx === -1 ? timeTz : timeTz.slice(0, spaceIdx);
  const tz = spaceIdx === -1 ? "" : timeTz.slice(spaceIdx + 1);
  const [h, m] = time.split(":");
  const hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "pm" : "am";
  const hour12 = hour % 12 || 12;
  return `${hour12}:${m} ${ampm}${tz ? " " + tz : ""}`;
}

export function formatDelta(delta: number | undefined): string {
  if (delta === undefined) return '';
  const sign = delta >= 0 ? '+' : '';
  return `${sign}${Math.round(delta)} vs 30d avg`;
}
