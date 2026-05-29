import { apiGet } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { Report } from "@/types/report";
import type { Scan, ScanStepLog } from "@/types/scan";
import type { QueryTask } from "@/types/task";

export const scanApi = {
  list: (params: ListParams) => apiGet<PageResult<Scan>>("/api/scans", params),
  get: (id: string | number) => apiGet<Scan>(`/api/scans/${id}`),
  steps: (id: string | number) => apiGet<ScanStepLog[]>(`/api/scans/${id}/steps`),
  tasks: (id: string | number) => apiGet<QueryTask[]>(`/api/scans/${id}/tasks`),
  report: (id: string | number) => apiGet<Report | null>(`/api/scans/${id}/report`),
};
