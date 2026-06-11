import { PlanResult } from "@/types/plan";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceText } from "@/components/common/PriceText";
import { RiskBadge } from "@/components/common/RiskBadge";
import { RouteText } from "@/components/common/RouteText";
import { formatMinutes } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { PlanFlightMeta } from "@/components/plans/PlanFlightMeta";

const completenessLabels: Record<string, string> = {
  FULL_ROUND_TRIP: "完整数据",
  OUTBOUND_WITH_STARTING_PRICE: "去程+起价",
};

export function RoundTripPlanCard({ plan }: { plan: PlanResult }) {
  const completenessLabel = completenessLabels[plan.data_completeness || ""] || plan.data_completeness;

  return (
    <Card className="border-green-200/60">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <Badge className="border-green-200 bg-green-50 text-green-700 font-medium">完整往返</Badge>
              <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs text-stone-500">往返</span>
              {completenessLabel && (
                <span className="inline-flex items-center rounded-full border border-green-200 px-2.5 py-0.5 text-xs text-green-700">{completenessLabel}</span>
              )}
              <span className="text-sm text-stone-500">
                去程 {plan.depart_date} / 返程 {plan.return_date || "—"}
              </span>
            </div>
            <CardTitle className="text-base">
              <RouteText from={plan.from_city} to={plan.to_city} tripType="ROUND_TRIP" />
            </CardTitle>
          </div>
          <div className="text-right shrink-0">
            <div className="text-xs text-green-600 font-medium mb-0.5">往返总价</div>
            <PriceText value={plan.total_price} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-2 md:grid-cols-2">
          <PlanFlightMeta
            label="去程"
            airline={plan.outbound_airline}
            flightNo={plan.outbound_flight_no}
            departTime={plan.outbound_depart_time}
            arriveTime={plan.outbound_arrive_time}
            departAirport={plan.outbound_depart_airport}
            arriveAirport={plan.outbound_arrive_airport}
          />
          <PlanFlightMeta
            label="返程"
            airline={plan.return_airline}
            flightNo={plan.return_flight_no}
            departTime={plan.return_depart_time}
            arriveTime={plan.return_arrive_time}
            departAirport={plan.return_depart_airport}
            arriveAirport={plan.return_arrive_airport}
          />
          {!plan.outbound_airline && plan.outbound_summary && (
            <div className="rounded-xl border border-border bg-[#fbf8f4] p-3">
              <div className="text-xs text-stone-400 mb-1">去程摘要</div>
              <div className="text-sm font-medium text-ink">{plan.outbound_summary}</div>
            </div>
          )}
          {!plan.return_airline && plan.return_summary && (
            <div className="rounded-xl border border-border bg-[#fbf8f4] p-3">
              <div className="text-xs text-stone-400 mb-1">返程摘要</div>
              <div className="text-sm font-medium text-ink">{plan.return_summary}</div>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 text-sm text-stone-600 flex-wrap">
          <RiskBadge risk={plan.risk_level} />
          {plan.total_duration_minutes != null && <span>{formatMinutes(plan.total_duration_minutes)}</span>}
          {plan.transfer_count != null && plan.transfer_count > 0 && <span>{plan.transfer_count} 次中转</span>}
          {plan.score != null && <span>评分 {plan.score.toFixed(1)}</span>}
          {plan.data_completeness && (
            <span className="text-xs text-stone-400">{plan.data_completeness}</span>
          )}
        </div>
        {plan.reason && <p className="text-sm text-stone-500">{plan.reason}</p>}
        {plan.warning && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-700">{plan.warning}</div>
        )}
      </CardContent>
    </Card>
  );
}
