import { apiGet, apiPost } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { Scan, ScanOption, ScanStepLog } from "@/types/scan";
import type { QueryTask } from "@/types/task";

export const scanApi = {
  list: (params: ListParams) => apiGet<PageResult<Scan>>("/api/scans", params),
  options: (params?: ListParams) => apiGet<ScanOption[]>("/api/scan-options", params),
  get: (id: string | number) => apiGet<Scan>(`/api/scans/${id}`),
  cancel: (id: string | number) => apiPost<Scan>(`/api/scans/${id}/cancel`),
  restart: (id: string | number) => apiPost<Scan>(`/api/scans/${id}/restart`),
  steps: (id: string | number) => apiGet<ScanStepLog[]>(`/api/scans/${id}/steps`),
  tasks: (id: string | number) => apiGet<QueryTask[]>(`/api/scans/${id}/tasks`),
};
