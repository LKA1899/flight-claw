import { PlanResult } from "@/types/plan";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceText } from "@/components/common/PriceText";
import { RouteText } from "@/components/common/RouteText";
import { Badge } from "@/components/ui/badge";

const returnStatusLabels: Record<string, string> = {
  NOT_EXPANDED: "未展开",
  EXPANDING: "展开中",
  EXPANDED: "已展开",
  EXPAND_FAILED: "展开失败",
};

const returnStatusStyles: Record<string, string> = {
  NOT_EXPANDED: "border-stone-200 bg-stone-50 text-stone-600",
  EXPANDING: "border-blue-200 bg-blue-50 text-blue-700",
  EXPANDED: "border-green-200 bg-green-50 text-green-700",
  EXPAND_FAILED: "border-red-200 bg-red-50 text-red-700",
};

const completenessLabels: Record<string, string> = {
  OUTBOUND_WITH_STARTING_PRICE: "去程+往返起价",
  OUTBOUND_ONLY: "仅去程",
  FULL_ROUND_TRIP: "完整往返",
  SNAPSHOT_ONLY: "仅快照",
};

export function RoundTripClueCard({ plan }: { plan: PlanResult }) {
  const outboundFlight = [
    plan.outbound_airline,
    plan.outbound_flight_no,
  ].filter(Boolean).join(" ");

  const outboundTime = [plan.outbound_depart_time, plan.outbound_arrive_time].filter(Boolean).join(" – ");

  const status = plan.return_detail_status || "NOT_EXPANDED";
  const statusLabel = returnStatusLabels[status] || status;
  const statusStyle = returnStatusStyles[status] || returnStatusStyles.NOT_EXPANDED;
  const completenessLabel = completenessLabels[plan.data_completeness || ""] || plan.data_completeness;

  return (
    <Card className="border-amber-300 bg-amber-50/30">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <Badge className="border-amber-300 bg-amber-100 text-amber-800 font-medium">往返线索</Badge>
              <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs text-stone-500">往返</span>
              <span className="text-sm text-stone-500">
                去程 {plan.depart_date}{plan.return_date ? ` / 返程 ${plan.return_date}` : ""}
              </span>
            </div>
            <CardTitle className="text-base">
              <RouteText from={plan.from_city} to={plan.to_city} tripType="ROUND_TRIP" />
            </CardTitle>
            {outboundFlight && (
              <p className="mt-1.5 text-sm text-stone-700">
                去程：<span className="font-medium">{outboundFlight}</span>
                {outboundTime ? ` · ${outboundTime}` : ""}
              </p>
            )}
            {plan.outbound_depart_airport && (
              <p className="text-xs text-stone-400 mt-0.5">{plan.outbound_depart_airport} → {plan.outbound_arrive_airport || "—"}</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <div className="text-xs text-amber-600 font-medium mb-0.5">往返起价</div>
            <PriceText value={plan.total_price} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-stone-500">返程状态：</span>
          <Badge className={statusStyle}>{statusLabel}</Badge>
          {completenessLabel && (
            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs text-stone-500">{completenessLabel}</span>
          )}
          {plan.price_type && (
            <span className="text-xs text-stone-400">{plan.price_type}</span>
          )}
        </div>
        {plan.warning && (
          <div className="rounded-lg border-2 border-amber-300 bg-amber-100 p-3 text-sm text-amber-800 font-medium">
            ⚠ {plan.warning}
          </div>
        )}
        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-2.5 text-xs text-amber-700">
          该价格是去程列表展示的往返起价，未包含明确返程航班，不能作为最终购票推荐。
        </div>
        {plan.reason && <p className="text-xs text-stone-400">{plan.reason}</p>}
      </CardContent>
    </Card>
  );
}
