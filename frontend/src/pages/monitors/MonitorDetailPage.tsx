import { CalendarDays, Clock, Edit, MapPin, Play, Route } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { RouteCell } from "@/components/common/RouteCell";
import { StrategyTags } from "@/components/common/StrategyTags";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime, formatPrice } from "@/lib/format";

export function MonitorDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["monitor", id], queryFn: () => monitorApi.get(id) });
  const scanNow = useMutation({
    mutationFn: () => monitorApi.scanNow(id),
    onSuccess: (data) => {
      toast.success("扫描已启动");
      queryClient.invalidateQueries({ queryKey: ["monitor", id] });
      navigate(`/scans/${data.scan_id}`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "启动扫描失败"),
  });

  if (query.isLoading) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} />;
  const monitor = query.data!;

  return (
    <>
      <PageHeader
        title={monitor.monitor_name}
        description="关注路线详情、扫描策略、日期配置和定时扫描入口。"
        actions={
          <>
            <Button onClick={() => scanNow.mutate()} disabled={scanNow.isPending || !monitor.enabled}><Play className="h-4 w-4" />{scanNow.isPending ? "启动中" : "立即扫描"}</Button>
            <Button asChild variant="secondary"><Link to={`/monitors/${id}/schedule`}><Clock className="h-4 w-4" />定时扫描</Link></Button>
            <Button asChild variant="secondary"><Link to={`/monitors/${id}/edit#dates`}><CalendarDays className="h-4 w-4" />日期管理</Link></Button>
            {monitor.allow_train_positioning ? <Button asChild variant="secondary"><Link to={`/monitors/${id}/positionings`}><MapPin className="h-4 w-4" />接驳城市</Link></Button> : null}
            {monitor.allow_transfer ? <Button asChild variant="secondary"><Link to={`/monitors/${id}/transfers`}><Route className="h-4 w-4" />中转城市</Link></Button> : null}
            <Button asChild variant="secondary"><Link to={`/monitors/${id}/edit`}><Edit className="h-4 w-4" />编辑</Link></Button>
          </>
        }
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>路线摘要</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <RouteCell from={monitor.from_city} to={monitor.to_city} fromAirports={monitor.from_airports} toAirports={monitor.to_airports} />
            <StrategyTags direct={monitor.allow_direct} transfer={monitor.allow_transfer} train={monitor.allow_train_positioning} hidden={monitor.allow_hidden_city} />
            {monitor.trip_type === "ROUND_TRIP" ? (
              <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
                往返采集方式：{monitor.roundtrip_expand_return ? "深度扫描，会展开部分去程采集返程明细并生成完整组合。" : "轻量扫描，仅采集去程列表和往返起价，不生成完整购票推荐。"}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>限制</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between"><span>状态</span><StatusBadge status={monitor.enabled} /></div>
            <div className="flex justify-between"><span>预算</span><b>{formatPrice(monitor.max_price, "¥")}</b></div>
            <div className="flex justify-between"><span>日期</span><b>{monitor.enabled_date_count} / {monitor.date_count}</b></div>
            <div className="flex justify-between"><span>最长时长</span><b>{monitor.max_total_hours || "-"}h</b></div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader><CardTitle>扫描计划</CardTitle></CardHeader>
          <CardContent className="grid gap-4 text-sm md:grid-cols-4">
            <Summary label="定时状态" value={monitor.schedule_enabled ? monitor.schedule_cron || "已开启" : "未开启"} />
            <Summary label="时区" value={monitor.schedule_timezone || "Asia/Shanghai"} />
            <Summary label="最近扫描" value={formatDateTime(monitor.last_scan_time)} />
            <Summary label="下次扫描" value={formatDateTime(monitor.next_scan_time)} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function Summary({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl bg-[#fbf8f4] p-4">
      <div className="text-xs text-stone-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}
