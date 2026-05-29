export interface Report {
  id: number;
  scan_id?: number | null;
  monitor_id?: number | null;
  batch_no?: string | null;
  title: string;
  content_md?: string | null;
  llm_enabled?: boolean;
  llm_content_md?: string | null;
  llm_error_message?: string | null;
  create_time?: string | null;
}
