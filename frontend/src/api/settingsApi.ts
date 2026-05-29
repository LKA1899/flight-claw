import { apiGet, apiPut } from "@/lib/api";

export interface SettingsData {
  browser: Record<string, unknown>;
  storage: Record<string, unknown>;
  notification: Record<string, unknown>;
  llm: Record<string, unknown>;
  safety_policy: string[];
}

export const settingsApi = {
  get: () => apiGet<SettingsData>("/api/settings"),
  update: (payload: { headless: boolean }) => apiPut<{ headless: boolean }>("/api/settings", payload),
};
