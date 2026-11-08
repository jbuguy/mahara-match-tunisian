export type GovernorateMetric = "candidates" | "open_positions" | "published_courses" | "candidates_per_open_position";

export const METRIC_BREAKPOINTS: Record<GovernorateMetric, number[]> = {
  candidates: [10, 25, 50, 100],
  open_positions: [2, 5, 10, 20],
  published_courses: [1, 3, 5, 10],
  candidates_per_open_position: [1, 2, 5, 10],
};

export function metricColorClass(metric: GovernorateMetric, value: number | null): number {
  if (value === null || !Number.isFinite(value)) return 0;
  const breaks = METRIC_BREAKPOINTS[metric];
  let klass = 1;
  for (const breakpoint of breaks) {
    if (value >= breakpoint) klass += 1;
  }
  return Math.min(5, klass);
}

export function metricValue(row: { [key: string]: unknown }, metric: GovernorateMetric): number | null {
  const cell = row[metric] as { value?: number } | number | null | undefined;
  if (typeof cell === "number") return cell;
  return typeof cell?.value === "number" ? cell.value : null;
}
