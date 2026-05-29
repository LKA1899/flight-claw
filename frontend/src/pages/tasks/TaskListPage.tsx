import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { taskApi } from "@/api/taskApi";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RouteCell } from "@/components/common/RouteCell";
import { SnapshotLinks } from "@/components/common/SnapshotLinks";
import { StatusBadge } from "@/components/common/StatusBadge";
import { TaskActionMenu } from "@/components/tasks/TaskActionMenu";
import { ListToolbar } from "@/components/query/ListToolbar";
import { FilterSelect } from "@/components/query/FilterSelect";
import { DataPagination } from "@/components/query/DataPagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { STATUS_OPTIONS, PLATFORM_OPTIONS } from "@/lib/constants";
import { formatDateTime } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";

export function TaskListPage() {
  const qp = usePagedParams(20);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["tasks", qp.params], queryFn: () => taskApi.list(qp.params) });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["tasks"] });
  const run = useMutation({ mutationFn: taskApi.run, onSuccess: () => { toast.success("任务已执行"); invalidate(); }, onError: (error) => toast.error(error instanceof Error ? error.message : "执行失败") });
  const reset = useMutation({ mutationFn: taskApi.reset, onSuccess: () => { toast.success("任务已重置"); invalidate(); } });
  const parse = useMutation({ mutationFn: taskApi.parsePrice, onSuccess: () => toast.success("解析完成"), onError: (error) => toast.error(error instanceof Error ? error.message : "解析失败") });

  return (
    <>
      <PageHeader title="查询任务" description="本地浏览器低频查询 OTA，保存截图和解析文本用于追踪。" />
      <Alert className="mb-5">
        <AlertDescription>往返任务会区分去程候选、返程候选和完整组合。未展开返程的往返起价不会进入最终推荐。</AlertDescription>
      </Alert>
      <ListToolbar
        onReset={qp.reset}
        onRefresh={() => query.refetch()}
        filters={
          <>
            <Input placeholder="scan_id" value={String(qp.params.scan_id || "")} onChange={(event) => qp.setValue("scan_id", event.target.value)} className="w-28 shrink-0" />
            <Input placeholder="batch_no" value={String(qp.params.batch_no || "")} onChange={(event) => qp.setValue("batch_no", event.target.value)} className="w-40 shrink-0" />
            <Input placeholder="monitor_id" value={String(qp.params.monitor_id || "")} onChange={(event) => qp.setValue("monitor_id", event.target.value)} className="w-28 shrink-0" />
            <FilterSelect value={String(qp.params.trip_type || "")} onChange={(value) => qp.setValue("trip_type", value)} options={[{ value: "ONE_WAY", label: "单程" }, { value: "ROUND_TRIP", label: "往返" }]} placeholder="行程类型" />
            <FilterSelect value={String(qp.params.status || "")} onChange={(value) => qp.setValue("status", value)} options={STATUS_OPTIONS.map((item) => ({ value: item, label: item }))} placeholder="状态" />
            <FilterSelect value={String(qp.params.platform || "")} onChange={(value) => qp.setValue("platform", value)} options={PLATFORM_OPTIONS} placeholder="平台" />
            <Input type="date" value={String(qp.params.depart_date || "")} onChange={(event) => qp.setValue("depart_date", event.target.value)} className="w-40 shrink-0" />
          </>
        }
      />
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data!.items.length ? (
        <div className="table-shell">
          <div className="table-scroll rounded-2xl">
          <Table className="whitespace-nowrap">
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Completeness</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Snapshot</TableHead>
                <TableHead>Error</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data!.items.map((task) => (
                <TableRow key={task.id} className={task.status === "FAILED" ? "bg-red-50/40" : ""}>
                  <TableCell className="font-medium">
                    #{task.id}
                    <div className="text-xs text-stone-500">{task.batch_no}</div>
                    {task.scan_id ? <div className="text-xs text-stone-500">Scan #{task.scan_id}</div> : null}
                  </TableCell>
                  <TableCell><RouteCell from={task.from_city} to={task.to_city} /></TableCell>
                  <TableCell>{task.depart_date}{task.return_date ? <div className="text-xs text-stone-500">返程 {task.return_date}</div> : null}</TableCell>
                  <TableCell>{task.trip_type === "ROUND_TRIP" ? "往返" : "单程"}<div className="text-xs text-stone-500">{task.query_type}</div></TableCell>
                  <TableCell>{task.data_completeness || "-"}{task.roundtrip_stage ? <div className="text-xs text-stone-500">{task.roundtrip_stage}</div> : null}</TableCell>
                  <TableCell><StatusBadge status={task.status} /></TableCell>
                  <TableCell><SnapshotLinks taskId={task.id} screenshot={task.screenshot_path} /></TableCell>
                  <TableCell className="max-w-48 truncate text-red-600">{task.error_message || task.parse_error_message || "-"}</TableCell>
                  <TableCell>{formatDateTime(task.create_time)}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      {task.trip_type === "ROUND_TRIP" ? (
                        <>
                          <Button asChild size="sm" variant="secondary"><Link to={`/round-trips?task_id=${task.id}&tab=outbounds`}>去程候选</Link></Button>
                          <Button asChild size="sm" variant="secondary"><Link to={`/round-trips?task_id=${task.id}&tab=plans`}>完整组合</Link></Button>
                        </>
                      ) : null}
                      <TaskActionMenu task={task} onRun={() => run.mutate(task.id)} onParse={() => parse.mutate(task.id)} onReset={() => reset.mutate(task.id)} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
          <div className="p-4"><DataPagination page={qp.page} pageSize={qp.pageSize} total={query.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} /></div>
        </div>
      ) : <EmptyState title="暂无查询任务" />}
    </>
  );
}
