import { Calendar, Clock, MapPin, MoreHorizontal, Play, Repeat2, Route, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { Monitor } from "@/types/monitor";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { StrategyTags } from "@/components/common/StrategyTags";
import { RouteCell } from "@/components/common/RouteCell";
import { formatDateTime, formatPrice } from "@/lib/format";

type RouteCardProps = {
  monitor: Monitor;
  onDelete: () => void;
  onToggle: () => void;
  onScan: () => void;
  onCancelScan?: () => void;
  scanning?: boolean;
};

export function RouteCard({ monitor, onDelete, onToggle, onScan, onCancelScan, scanning }: RouteCardProps) {
  const scanMode = monitor.trip_type === "ROUND_TRIP" ? (monitor.roundtrip_expand_return ? "深度扫描" : "轻量扫描") : "单程扫描";
  const hasActiveScan = ["QUEUED", "RUNNING", "CANCEL_REQUESTED"].includes(String(monitor.last_scan_status || ""));

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="mb-2 text-sm font-medium text-stone-500">{monitor.monitor_name}</div>
          <RouteCell from={monitor.from_city} to={monitor.to_city} fromAirports={monitor.from_airports} toAirports={monitor.to_airports} />
          {monitor.trip_type === "ROUND_TRIP" ? (
            <div className="mt-2 flex items-center gap-1 text-xs text-blue-600">
              <Repeat2 className="h-3.5 w-3.5" />
              往返 · {scanMode}
            </div>
          ) : null}
        </div>
        <StatusBadge status={monitor.enabled} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-2xl bg-[#fbf8f4] p-3">
          <div className="text-xs text-stone-500">启用日期</div>
          <div className="mt-1 font-semibold text-ink">{monitor.enabled_date_count} / {monitor.date_count}</div>
        </div>
        <div className="rounded-2xl bg-[#fbf8f4] p-3">
          <div className="text-xs text-stone-500">预算</div>
          <div className="mt-1 font-semibold text-ink">{formatPrice(monitor.max_price, "¥")}</div>
        </div>
        <div className="rounded-2xl bg-[#fbf8f4] p-3">
          <div className="text-xs text-stone-500">定时扫描</div>
          <div className="mt-1 font-semibold text-ink">{monitor.schedule_enabled ? monitor.schedule_cron || "已开启" : "未开启"}</div>
        </div>
        <div className="rounded-2xl bg-[#fbf8f4] p-3">
          <div className="text-xs text-stone-500">最近扫描</div>
          <div className="mt-1 flex items-center gap-2 font-semibold text-ink">
            {monitor.last_scan_status ? <StatusBadge status={monitor.last_scan_status} /> : "暂无"}
          </div>
        </div>
      </div>

      {monitor.next_scan_time ? (
        <div className="mt-3 flex items-center gap-2 text-xs text-stone-500">
          <Clock className="h-3.5 w-3.5" />
          下次扫描 {formatDateTime(monitor.next_scan_time)}
        </div>
      ) : null}

      <div className="mt-4">
        <StrategyTags direct={monitor.allow_direct} transfer={monitor.allow_transfer} train={monitor.allow_train_positioning} hidden={monitor.allow_hidden_city} />
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Button asChild size="sm"><Link to={`/monitors/${monitor.id}`}>查看</Link></Button>
        <Button asChild size="sm" variant="secondary"><Link to={`/results?monitor_id=${monitor.id}`}>结果</Link></Button>
        <Button asChild size="sm" variant="secondary"><Link to={`/monitors/${monitor.id}/edit#dates`}><Calendar className="h-4 w-4" />日期</Link></Button>
        {hasActiveScan && onCancelScan ? (
          <Button size="sm" variant="outline" onClick={onCancelScan}>停止扫描</Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={onScan} disabled={scanning || !monitor.enabled}><Play className="h-4 w-4" />{scanning ? "启动中" : "立即扫描"}</Button>
        )}
        <Button asChild size="sm" variant="secondary"><Link to={`/monitors/${monitor.id}/schedule`}>定时</Link></Button>
        {monitor.allow_train_positioning ? <Button asChild size="sm" variant="secondary"><Link to={`/monitors/${monitor.id}/positionings`}><MapPin className="h-4 w-4" />接驳</Link></Button> : null}
        {monitor.allow_transfer ? <Button asChild size="sm" variant="secondary"><Link to={`/monitors/${monitor.id}/transfers`}><Route className="h-4 w-4" />中转</Link></Button> : null}
        <Button asChild size="sm" variant="secondary"><Link to={`/monitors/${monitor.id}/edit`}>编辑</Link></Button>
        <Button size="sm" variant="ghost" onClick={onToggle}><MoreHorizontal className="h-4 w-4" />{monitor.enabled ? "停用" : "启用"}</Button>
        <Button size="sm" variant="ghost" className="text-red-600" onClick={onDelete}><Trash2 className="h-4 w-4" />删除</Button>
      </div>
    </Card>
  );
}
