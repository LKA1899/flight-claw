import type { QueryTask } from "@/types/task";

export interface Scan {
  id: number;
  scan_no: string;
  batch_no?: string | null;
  monitor_id?: number | null;
  monitor_name?: string | null;
  from_city?: string | null;
  to_city?: string | null;
  trigger_type: string;
  status: string;
  trip_type?: "ONE_WAY" | "ROUND_TRIP" | null;
  total_task_count: number;
  success_task_count: number;
  failed_task_count: number;
  partial_task_count: number;
  start_time?: string | null;
  end_time?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
  create_time?: string | null;
}

export interface ScanStepLog {
  id: number;
  scan_id: number;
  step_code: string;
  step_name: string;
  status: string;
  input_json?: string | null;
  output_json?: string | null;
  error_message?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  duration_seconds?: number | null;
  create_time?: string | null;
}

export interface ScanDetail {
  scan: Scan;
  steps: ScanStepLog[];
  tasks: QueryTask[];
}

export interface ScanOption {
  scan_id: number;
  scan_no: string;
  batch_no?: string | null;
  monitor_id?: number | null;
  monitor_name?: string | null;
  from_city?: string | null;
  to_city?: string | null;
  route_label: string;
  label: string;
  start_time?: string | null;
  create_time?: string | null;
  trigger_type: string;
  status: string;
  total_task_count: number;
  success_task_count: number;
  failed_task_count: number;
}
