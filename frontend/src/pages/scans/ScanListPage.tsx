import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { scanApi } from "@/api/scanApi";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RouteCell } from "@/components/common/RouteCell";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataPagination } from "@/components/query/DataPagination";
import { DateRangeFilter } from "@/components/query/DateRangeFilter";
import { FilterSelect } from "@/components/query/FilterSelect";
import { ListToolbar } from "@/components/query/ListToolbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { STATUS_OPTIONS } from "@/lib/constants";
import { formatDateTime, formatDuration } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";
import { toast } from "sonner";

export function ScanListPage() {
  const qp = usePagedParams(20);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["scans", qp.params], queryFn: () => scanApi.list(qp.params) });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["scans"] });
  const cancelScan = useMutation({
    mutationFn: scanApi.cancel,
    onSuccess: () => {
      toast.success("已请求停止扫描");
      invalidate();
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "停止失败"),
  });
  const restartScan = useMutation({
    mutationFn: scanApi.restart,
    onSuccess: () => {
      toast.success("扫描已重新加入队列");
      invalidate();
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "重新开始失败"),
  });

  return (
    <>
      <PageHeader title="扫描记录" description="每次手动或定时扫描都会生成一条记录，并保留任务、步骤日志和报告。" />
      <ListToolbar
        keyword={String(qp.params.keyword || "")}
        onKeywordChange={(value) => qp.setValue("keyword", value)}
        onReset={qp.reset}
        onRefresh={() => query.refetch()}
        filters={
          <>
            <Input placeholder="monitor_id" value={String(qp.params.monitor_id || "")} onChange={(event) => qp.setValue("monitor_id", event.target.value)} className="w-32 shrink-0" />
            <FilterSelect value={String(qp.params.status || "")} onChange={(value) => qp.setValue("status", value)} options={STATUS_OPTIONS.map((item) => ({ value: item, label: item }))} placeholder="状态" />
            <FilterSelect value={String(qp.params.trigger_type || "")} onChange={(value) => qp.setValue("trigger_type", value)} options={[{ value: "MANUAL", label: "手动" }, { value: "SCHEDULED", label: "定时" }]} placeholder="触发方式" />
            <FilterSelect value={String(qp.params.trip_type || "")} onChange={(value) => qp.setValue("trip_type", value)} options={[{ value: "ONE_WAY", label: "单程" }, { value: "ROUND_TRIP", label: "往返" }]} placeholder="行程类型" />
            <DateRangeFilter start={String(qp.params.start_date || "")} end={String(qp.params.end_date || "")} onStartChange={(value) => qp.setValue("start_date", value)} onEndChange={(value) => qp.setValue("end_date", value)} />
          </>
        }
      />

      {query.isLoading ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : query.data!.items.length ? (
        <div className="table-shell">
          <div className="table-scroll rounded-2xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>扫描编号</TableHead>
                <TableHead>路线</TableHead>
                <TableHead>触发</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>任务</TableHead>
                <TableHead>开始时间</TableHead>
                <TableHead>耗时</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data!.items.map((scan) => (
                <TableRow key={scan.id}>
                  <TableCell className="font-medium">
                    {scan.scan_no}
                    <div className="text-xs text-stone-500">{scan.batch_no || "-"}</div>
                  </TableCell>
                  <TableCell>
                    {scan.from_city && scan.to_city ? <RouteCell from={scan.from_city} to={scan.to_city} /> : <span className="text-stone-500">{scan.monitor_name || "全部路线"}</span>}
                  </TableCell>
                  <TableCell>{scan.trigger_type === "SCHEDULED" ? "定时" : "手动"}</TableCell>
                  <TableCell><StatusBadge status={scan.status} /></TableCell>
                  <TableCell>{scan.success_task_count}/{scan.total_task_count} · failed {scan.failed_task_count}</TableCell>
                  <TableCell>{formatDateTime(scan.start_time || scan.create_time)}</TableCell>
                  <TableCell>{formatDuration(scan.duration_seconds)}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <Button asChild size="sm" variant="secondary"><Link to={`/scans/${scan.id}`}>详情</Link></Button>
                      <Button asChild size="sm" variant="secondary"><Link to={`/tasks?scan_id=${scan.id}`}>任务</Link></Button>
                      {scan.report_id ? <Button asChild size="sm" variant="secondary"><Link to={`/reports/${scan.report_id}`}>报告</Link></Button> : null}
                      {["QUEUED", "RUNNING", "CANCEL_REQUESTED"].includes(scan.status) ? (
                        <Button size="sm" variant="outline" onClick={() => cancelScan.mutate(scan.id)} disabled={cancelScan.isPending}>停止</Button>
                      ) : null}
                      {["FAILED", "CANCELLED", "PARTIAL_SUCCESS"].includes(scan.status) ? (
                        <Button size="sm" variant="outline" onClick={() => restartScan.mutate(scan.id)} disabled={restartScan.isPending}>重新开始</Button>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
          <div className="p-4">
            <DataPagination page={qp.page} pageSize={qp.pageSize} total={query.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
          </div>
        </div>
      ) : (
        <EmptyState title="暂无扫描记录" description="在关注路线中点击立即扫描，或开启路线定时扫描后会出现在这里。" />
      )}
    </>
  );
}
