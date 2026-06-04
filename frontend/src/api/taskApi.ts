import { apiBaseUrl, apiGet, apiPost } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { QueryTask } from "@/types/task";

export const taskApi = {
  list: (params: ListParams) => apiGet<PageResult<QueryTask>>("/api/tasks", params),
  run: (id: string | number) => apiPost(`/api/tasks/${id}/run`),
  cancel: (id: string | number) => apiPost<QueryTask>(`/api/tasks/${id}/cancel`),
  reset: (id: string | number) => apiPost<QueryTask>(`/api/tasks/${id}/reset`),
  parsePrice: (id: string | number) => apiPost(`/api/tasks/${id}/parse-price`),
  screenshotUrl: (id: string | number) => `${apiBaseUrl}/api/tasks/${id}/screenshot`,
};
