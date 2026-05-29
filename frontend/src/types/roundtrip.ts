export interface RoundTripOutbound {
  id: number;
  task_id: number;
  batch_no: string;
  monitor_id: number;
  monitor_name?: string | null;
  platform: string;
  from_city: string;
  to_city: string;
  depart_date: string;
  return_date: string;
  outbound_rank?: number | null;
  airline?: string | null;
  flight_no?: string | null;
  depart_time?: string | null;
  arrive_time?: string | null;
  depart_airport?: string | null;
  arrive_airport?: string | null;
  duration_minutes?: number | null;
  transfer_count?: number | null;
  transfer_city?: string | null;
  display_total_price?: number | null;
  currency: string;
  price_type: string;
  price_display_text?: string | null;
  return_detail_status: string;
  data_completeness: string;
  is_complete_plan: boolean;
  source_html_path?: string | null;
  source_screenshot_path?: string | null;
  create_time?: string | null;
}

export interface RoundTripReturn {
  id: number;
  task_id: number;
  batch_no: string;
  monitor_id: number;
  outbound_id: number;
  from_city: string;
  to_city: string;
  depart_date: string;
  return_date: string;
  return_rank?: number | null;
  airline?: string | null;
  flight_no?: string | null;
  depart_time?: string | null;
  arrive_time?: string | null;
  total_price?: number | null;
  price_delta?: number | null;
  currency: string;
  price_type: string;
  price_display_text?: string | null;
}

export interface RoundTripPlan {
  id: number;
  task_id: number;
  batch_no: string;
  monitor_id: number;
  monitor_name?: string | null;
  outbound_id: number;
  return_id: number;
  depart_date: string;
  return_date: string;
  leg_type: string;
  price_type: string;
  total_price: number;
  currency: string;
  total_duration_minutes?: number | null;
  total_transfer_count?: number | null;
  outbound_summary?: string | null;
  return_summary?: string | null;
  risk_level?: string | null;
  score?: number | null;
  reason?: string | null;
  warning?: string | null;
  data_completeness: string;
  is_complete_plan: boolean;
  outbound?: RoundTripOutbound | null;
  return_flight?: RoundTripReturn | null;
  create_time?: string | null;
}
