import { AlertTriangle, CheckCircle2, Plane, Radar, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { overviewApi } from "@/api/overviewApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { EmptyState } from "@/components/common/EmptyState";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { PriceText } from "@/components/common/PriceText";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDateTime, formatDuration } from "@/lib/format";

export function OverviewPage() {
  const query = useQuery({ queryKey: ["overview"], queryFn: overviewApi.get });
  if (query.isLoading) return <LoadingState rows={4} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data!;
  const dist = data.task_status_distribution || {};

  return (
    <>
      <PageHeader title="今日旅行雷达" description="汇总关注路线、扫描状态、查询任务和低价机会。" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="关注路线" value={data.active_monitors} hint="当前启用的 Monitor" icon={<Plane className="h-5 w-5" />} />
        <MetricCard title="今日扫描" value={data.today_scan_count ?? 0} hint={`运行中 ${data.running_scan_count ?? 0}`} icon={<Radar className="h-5 w-5" />} />
        <MetricCard title="成功率" value={`${data.success_rate}%`} hint="今日查询任务成功比例" icon={<CheckCircle2 className="h-5 w-5" />} />
        <MetricCard title="降价机会" value={data.price_drops} hint="较上次更便宜的日期" icon={<Sparkles className="h-5 w-5" />} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader><CardTitle>今日机会</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {data.best_opportunities.length ? data.best_opportunities.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-[#fbf8f4] p-4">
                <div>
                  <div className="font-medium text-ink">{item.monitor_name || "关注路线"} · {item.depart_date}</div>
                  <p className="mt-1 text-sm text-stone-500">{item.summary || "已生成今日机会，建议查看候选方案和报告。"}</p>
                </div>
                <PriceText value={item.best_price} trend={item.price_trend} />
              </div>
            )) : <EmptyState title="还没有今日机会" description="完成真实查询、价格解析和方案分析后会显示在这里。" />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>最近扫描记录</CardTitle></CardHeader>
          <CardContent>
            {data.recent_scans?.length ? (
              <div className="space-y-3">
                {data.recent_scans.slice(0, 4).map((scan) => (
                  <div key={scan.id} className="rounded-xl border border-border bg-white p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium">{scan.scan_no}</span>
                      <StatusBadge status={scan.status} />
                    </div>
                    <div className="mt-1 text-sm text-stone-500">{scan.monitor_name || "全部路线"}</div>
                    <div className="mt-1 text-sm text-stone-500">{formatDateTime(scan.start_time || scan.create_time)} · {formatDuration(scan.duration_seconds)}</div>
                    <Button asChild variant="secondary" size="sm" className="mt-3"><Link to={`/scans/${scan.id}`}>查看扫描详情</Link></Button>
                  </div>
                ))}
              </div>
            ) : <EmptyState title="暂无扫描记录" />}
          </CardContent>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>任务状态分布</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {["PENDING", "RUNNING", "SUCCESS", "FAILED"].map((status) => (
              <div key={status} className="flex items-center justify-between rounded-xl bg-[#fbf8f4] px-4 py-3">
                <StatusBadge status={status} />
                <span className="font-semibold text-ink">{dist[status] || 0}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className={data.manual_attention_count ? "border-amber-200 bg-amber-50" : ""}>
          <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5" />人工处理提示</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm text-stone-600">
            <div>
              {data.manual_attention_count ? `当前有 ${data.manual_attention_count} 个失败任务，可能需要登录、验证码或页面变更处理。` : "当前没有需要人工处理的失败任务。"}
            </div>
            <div className="rounded-xl bg-white/70 p-3">
              下一个定时扫描：{data.next_scheduled_scan ? `${data.next_scheduled_scan.monitor_name} · ${formatDateTime(data.next_scheduled_scan.next_scan_time)}` : "暂无"}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
