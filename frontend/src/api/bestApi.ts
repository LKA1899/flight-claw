import { apiGet } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { BestDaily } from "@/types/plan";

export const bestApi = {
  list: (params: ListParams) => apiGet<PageResult<BestDaily>>("/api/best", params),
};
