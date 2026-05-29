import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import type { ReactNode } from "react";
import { scanApi } from "@/api/scanApi";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RouteCell } from "@/components/common/RouteCell";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, formatDuration } from "@/lib/format";

export function ScanDetailPage() {
  const { id = "" } = useParams();
  const scanQuery = useQuery({ queryKey: ["scan", id], queryFn: () => scanApi.get(id) });
  const stepsQuery = useQuery({ queryKey: ["scan-steps", id], queryFn: () => scanApi.steps(id) });
  const tasksQuery = useQuery({ queryKey: ["scan-tasks", id], queryFn: () => scanApi.tasks(id) });
  const reportQuery = useQuery({ queryKey: ["scan-report", id], queryFn: () => scanApi.report(id) });

  if (scanQuery.isLoading) return <LoadingState />;
  if (scanQuery.isError) return <ErrorState error={scanQuery.error} />;

  const scan = scanQuery.data!;
  const steps = stepsQuery.data || [];
  const tasks = tasksQuery.data || [];
  const report = reportQuery.data;

  return (
    <>
      <PageHeader
        title={scan.scan_no}
        description="固定扫描管线的执行详情。这里用于排查生成任务、浏览器查询、解析、分析和报告生成。"
        actions={
          <>
            <Button asChild variant="secondary"><Link to={`/tasks?scan_id=${scan.id}`}>查看任务</Link></Button>
            {report ? <Button asChild><Link to={`/reports/${report.id}`}>查看报告</Link></Button> : null}
          </>
        }
      />

      {scan.status === "FAILED" ? (
        <Alert className="mb-5 border-red-200 bg-red-50 text-red-800">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>扫描失败</AlertTitle>
          <AlertDescription>{scan.error_message || "请查看失败步骤的错误信息。"}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
        <div className="space-y-5">
          <Card>
            <CardContent className="grid gap-4 p-5 md:grid-cols-5">
              <Summary label="状态" value={<StatusBadge status={scan.status} />} />
              <Summary label="触发" value={scan.trigger_type === "SCHEDULED" ? "定时" : "手动"} />
              <Summary label="行程" value={scan.trip_type === "ROUND_TRIP" ? "往返" : "单程"} />
              <Summary label="开始" value={formatDateTime(scan.start_time || scan.create_time)} />
              <Summary label="耗时" value={formatDuration(scan.duration_seconds)} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>扫描步骤日志</CardTitle></CardHeader>
            <CardContent>
              {stepsQuery.isLoading ? <LoadingState /> : steps.length ? (
                <div className="space-y-3">
                  {steps.map((step) => (
                    <div key={step.id} className="rounded-xl border border-border bg-white p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <div className="font-semibold text-ink">{step.step_name}</div>
                          <div className="text-xs text-stone-500">{step.step_code}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm text-stone-500">{formatDuration(step.duration_seconds)}</span>
                          <StatusBadge status={step.status} />
                        </div>
                      </div>
                      {step.error_message ? <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{step.error_message}</div> : null}
                      {step.output_json ? <pre className="mt-3 max-h-44 overflow-auto rounded-lg bg-stone-950 p-3 text-xs text-stone-100">{step.output_json}</pre> : null}
                    </div>
                  ))}
                </div>
              ) : <EmptyState title="暂无步骤日志" />}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader><CardTitle>扫描上下文</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              {scan.from_city && scan.to_city ? <RouteCell from={scan.from_city} to={scan.to_city} /> : <div>{scan.monitor_name || "全部路线"}</div>}
              <div className="flex justify-between"><span className="text-stone-500">Monitor</span><span>{scan.monitor_id || "-"}</span></div>
              <div className="flex justify-between"><span className="text-stone-500">Batch</span><span>{scan.batch_no || "-"}</span></div>
              <div className="flex justify-between"><span className="text-stone-500">任务统计</span><span>{scan.success_task_count}/{scan.total_task_count}</span></div>
              <div className="flex justify-between"><span className="text-stone-500">失败任务</span><span>{scan.failed_task_count}</span></div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>查询任务</CardTitle></CardHeader>
            <CardContent>
              {tasks.length ? (
                <Table>
                  <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>日期</TableHead><TableHead>状态</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {tasks.slice(0, 8).map((task) => (
                      <TableRow key={task.id}>
                        <TableCell>#{task.id}</TableCell>
                        <TableCell>{task.depart_date}{task.return_date ? <div className="text-xs text-stone-500">{task.return_date}</div> : null}</TableCell>
                        <TableCell><StatusBadge status={task.status} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : <EmptyState title="暂无查询任务" />}
              {tasks.length ? <Button asChild variant="secondary" className="mt-4"><Link to={`/tasks?scan_id=${scan.id}`}>查看全部任务</Link></Button> : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function Summary({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <div className="text-xs text-stone-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}
