import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { formatPrice } from "@/lib/format";

export function PriceText({ value, trend }: { value?: number | null; trend?: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-lg font-semibold text-ink">{formatPrice(value)}</span>
      {trend !== undefined && trend !== null ? (
        <span className={trend < 0 ? "flex items-center text-xs text-green-600" : "flex items-center text-xs text-red-600"}>
          {trend < 0 ? <ArrowDownRight className="h-3.5 w-3.5" /> : <ArrowUpRight className="h-3.5 w-3.5" />}
          {formatPrice(Math.abs(trend))}
        </span>
      ) : null}
    </div>
  );
}
