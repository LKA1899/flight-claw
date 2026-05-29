import { apiGet } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { Report } from "@/types/report";

export const reportApi = {
  list: (params: ListParams) => apiGet<PageResult<Report>>("/api/reports", params),
  get: (id: string | number) => apiGet<Report>(`/api/reports/${id}`),
};
