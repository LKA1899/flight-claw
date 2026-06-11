export interface PlanResult {
  id: number;
  batch_no: string;
  monitor_id: number;
  monitor_name?: string | null;
  depart_date: string;
  return_date?: string | null;
  trip_type?: string;
  plan_type: string;
  source_type?: "ONE_WAY_PLAN" | "ROUNDTRIP_CLUE" | "ROUNDTRIP_PLAN" | string;
  price_type?: string;
  title: string;
  from_city?: string | null;
  to_city?: string | null;
  total_price: number;
  currency: string;
  total_duration_minutes?: number | null;
  transfer_count?: number | null;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | string;
  score: number;
  reason?: string | null;
  warning?: string | null;
  detail_json?: string | null;
  airline?: string | null;
  flight_no?: string | null;
  depart_time?: string | null;
  arrive_time?: string | null;
  depart_airport?: string | null;
  arrive_airport?: string | null;
  // Enriched round-trip clue fields (from detail_json)
  outbound_airline?: string | null;
  outbound_flight_no?: string | null;
  outbound_depart_time?: string | null;
  outbound_arrive_time?: string | null;
  outbound_depart_airport?: string | null;
  outbound_arrive_airport?: string | null;
  return_airline?: string | null;
  return_flight_no?: string | null;
  return_depart_time?: string | null;
  return_arrive_time?: string | null;
  return_depart_airport?: string | null;
  return_arrive_airport?: string | null;
  return_detail_status?: string | null;
  data_completeness?: string | null;
  // Enriched round-trip plan fields
  outbound_summary?: string | null;
  return_summary?: string | null;
  create_time?: string | null;
}

export interface BestDaily {
  id: number;
  batch_no: string;
  monitor_id: number;
  monitor_name?: string | null;
  depart_date: string;
  best_price?: number | null;
  prev_best_price?: number | null;
  price_trend?: number | null;
  summary?: string | null;
  best_plan?: PlanResult | null;
  cheapest_plan?: PlanResult | null;
  safest_plan?: PlanResult | null;
  aggressive_plan?: PlanResult | null;
  create_time?: string | null;
}
