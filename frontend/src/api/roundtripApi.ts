import { apiGet, apiPost } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { RoundTripOutbound, RoundTripPlan, RoundTripReturn } from "@/types/roundtrip";

export const roundtripApi = {
  outbounds: (params: ListParams) => apiGet<PageResult<RoundTripOutbound>>("/api/round-trips/outbounds", params),
  outbound: (id: string | number) => apiGet<RoundTripOutbound>(`/api/round-trips/outbounds/${id}`),
  expandReturn: (id: string | number) => apiPost(`/api/round-trips/outbounds/${id}/expand-return`),
  returns: (params: ListParams) => apiGet<PageResult<RoundTripReturn>>("/api/round-trips/returns", params),
  plans: (params: ListParams) => apiGet<PageResult<RoundTripPlan>>("/api/round-trips/plans", params),
  plan: (id: string | number) => apiGet<RoundTripPlan>(`/api/round-trips/plans/${id}`),
};
