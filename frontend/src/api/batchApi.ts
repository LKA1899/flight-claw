import { apiGet } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { QueryBatch } from "@/types/task";

export const batchApi = {
  list: (params: ListParams) => apiGet<PageResult<QueryBatch>>("/api/batches", params),
};
