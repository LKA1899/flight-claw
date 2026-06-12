import { apiGet, apiPut } from "@/lib/api";

export interface SettingsData {
  browser: {
    profile_path: string;
    headless: boolean;
    query_interval: string;
    scan_interval_min_seconds: number;
    scan_interval_max_seconds: number;
    scan_interval_min_allowed: number;
    scan_interval_max_allowed: number;
  };
  storage: Record<string, unknown>;
  notification: Record<string, unknown>;
  safety_policy: string[];
}

export interface SettingsUpdatePayload {
  headless: boolean;
  scan_interval_min_seconds: number;
  scan_interval_max_seconds: number;
}

export const settingsApi = {
  get: () => apiGet<SettingsData>("/api/settings"),
  update: (payload: SettingsUpdatePayload) => apiPut<SettingsUpdatePayload>("/api/settings", payload),
};
