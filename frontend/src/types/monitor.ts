export interface Monitor {
  id: number;
  monitor_name: string;
  from_city: string;
  from_airports?: string | null;
  to_city: string;
  to_airports?: string | null;
  platform: string;
  trip_type: "ONE_WAY" | "ROUND_TRIP";
  allow_direct: boolean;
  allow_transfer: boolean;
  allow_train_positioning: boolean;
  allow_hidden_city: boolean;
  max_transfer_count?: number | null;
  max_total_hours?: number | null;
  max_price?: number | null;
  roundtrip_data_level: "OUTBOUND_ONLY" | "FULL_COMBINATION";
  roundtrip_expand_return: boolean;
  roundtrip_outbound_expand_mode: "NONE" | "LOWEST_TOP_N" | "SPECIFIC_RANKS" | "ALL";
  roundtrip_expand_top_n: number;
  roundtrip_expand_ranks?: string | null;
  roundtrip_return_fetch_limit: number;
  roundtrip_return_sort_strategy: string;
  roundtrip_save_all_outbounds: boolean;
  roundtrip_expand_only_priced: boolean;
  roundtrip_skip_expand_over_budget: boolean;
  continue_on_expand_failed: boolean;
  save_step_snapshot: boolean;
  manual_takeover_enabled: boolean;
  enabled: boolean;
  schedule_enabled?: boolean;
  schedule_cron?: string | null;
  schedule_timezone?: string | null;
  schedule_remark?: string | null;
  last_scan_id?: number | null;
  last_scan_time?: string | null;
  last_scan_status?: string | null;
  next_scan_time?: string | null;
  remark?: string | null;
  date_count: number;
  enabled_date_count: number;
  create_time?: string | null;
  update_time?: string | null;
}

export interface MonitorDate {
  id: number;
  monitor_id: number;
  depart_date: string;
  return_date?: string | null;
  enabled: boolean;
  remark?: string | null;
  create_time?: string | null;
  update_time?: string | null;
}

export interface PositioningCity {
  id: number;
  monitor_id: number;
  from_city: string;
  positioning_city: string;
  positioning_type: "TRAIN" | "BUS" | "SELF";
  estimated_cost: number;
  estimated_minutes: number;
  enabled: boolean;
  sort_no: number;
  remark?: string | null;
  create_time?: string | null;
  update_time?: string | null;
}

export interface TransferCity {
  id: number;
  monitor_id: number;
  transfer_city: string;
  transfer_airports?: string | null;
  enabled: boolean;
  sort_no: number;
  remark?: string | null;
  create_time?: string | null;
  update_time?: string | null;
}

export interface MonitorSchedulePayload {
  schedule_enabled: boolean;
  schedule_cron?: string | null;
  schedule_timezone?: string | null;
  schedule_remark?: string | null;
}

export type MonitorPayload = Omit<
  Monitor,
  | "id"
  | "date_count"
  | "enabled_date_count"
  | "schedule_enabled"
  | "schedule_cron"
  | "schedule_timezone"
  | "schedule_remark"
  | "last_scan_id"
  | "last_scan_time"
  | "last_scan_status"
  | "next_scan_time"
  | "create_time"
  | "update_time"
>;
export type PositioningPayload = Omit<PositioningCity, "id" | "monitor_id" | "from_city" | "create_time" | "update_time">;
export type TransferPayload = Omit<TransferCity, "id" | "monitor_id" | "create_time" | "update_time">;
