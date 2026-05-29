import { apiGet } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { PlanResult } from "@/types/plan";

export const planApi = {
  list: (params: ListParams) => apiGet<PageResult<PlanResult>>("/api/plans", params),
};
