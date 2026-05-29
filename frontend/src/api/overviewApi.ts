import { apiGet } from "@/lib/api";
import type { BestDaily } from "@/types/plan";
import type { Monitor } from "@/types/monitor";
import type { Scan } from "@/types/scan";

export interface OverviewData {
  active_monitors: number;
  today_tasks: number;
  today_scan_count: number;
  running_scan_count: number;
  success_rate: number;
  price_drops: number;
  recent_scans: Scan[];
  next_scheduled_scan?: Monitor | null;
  task_status_distribution: Record<string, number>;
  best_opportunities: BestDaily[];
  manual_attention_count: number;
}

export const overviewApi = {
  get: () => apiGet<OverviewData>("/api/overview"),
};
