export interface QueryBatch {
  id: number;
  batch_no: string;
  trigger_type: string;
  status: string;
  total_task_count: number;
  success_task_count: number;
  failed_task_count: number;
  start_time?: string | null;
  end_time?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
  create_time?: string | null;
}

export interface QueryTask {
  id: number;
  batch_no: string;
  scan_id?: number | null;
  monitor_id: number;
  monitor_name?: string | null;
  depart_date: string;
  return_date?: string | null;
  trip_type: "ONE_WAY" | "ROUND_TRIP";
  query_type: string;
  platform: string;
  from_city: string;
  to_city: string;
  transfer_city?: string | null;
  status: string;
  error_message?: string | null;
  screenshot_path?: string | null;
  html_path?: string | null;
  text_path?: string | null;
  parse_status?: string | null;
  parse_error_message?: string | null;
  parsed_time?: string | null;
  strategy_snapshot_json?: string | null;
  data_completeness?: string | null;
  roundtrip_stage?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  create_time?: string | null;
}
