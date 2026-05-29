import { apiGet } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { PriceRaw } from "@/types/price";

export const priceApi = {
  list: (params: ListParams) => apiGet<PageResult<PriceRaw>>("/api/prices", params),
};
