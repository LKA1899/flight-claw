import { PlanResult } from "@/types/plan";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceText } from "@/components/common/PriceText";
import { RiskBadge } from "@/components/common/RiskBadge";
import { RouteText } from "@/components/common/RouteText";
import { formatMinutes } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

const priceTypeLabels: Record<string, string> = {
  ONE_WAY_PRICE: "单程价",
  ROUND_TRIP_STARTING_PRICE: "往返起价",
  ROUND_TRIP_TOTAL_PRICE: "往返总价",
};

export function PlanCard({ plan }: { plan: PlanResult }) {
  const priceLabel = priceTypeLabels[plan.price_type || ""] || plan.price_type;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <Badge className="border-sky-200 bg-sky-50 text-sky-700">单程</Badge>
              <Badge className="border-blue-200 bg-blue-50 text-blue-700">{plan.plan_type}</Badge>
              <span className="text-sm text-stone-500">日期 {plan.depart_date}</span>
            </div>
            <CardTitle className="text-base truncate">{plan.title}</CardTitle>
            <p className="mt-1 text-sm text-stone-500">
              <RouteText from={plan.from_city} to={plan.to_city} tripType={plan.trip_type} />
            </p>
          </div>
          <div className="text-right shrink-0">
            {priceLabel && <div className="text-xs text-stone-400 mb-0.5">{priceLabel}</div>}
            <PriceText value={plan.total_price} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-3 text-sm text-stone-600 flex-wrap">
          <RiskBadge risk={plan.risk_level} />
          {plan.total_duration_minutes != null && <span>{formatMinutes(plan.total_duration_minutes)}</span>}
          {plan.transfer_count != null && plan.transfer_count > 0 && <span>{plan.transfer_count} 次中转</span>}
          <span>评分 {plan.score?.toFixed(1) ?? "-"}</span>
        </div>
        {plan.reason && <p className="text-sm text-stone-500">{plan.reason}</p>}
        {plan.warning && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-700">{plan.warning}</div>
        )}
      </CardContent>
    </Card>
  );
}
