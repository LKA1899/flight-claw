import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { batchApi } from "@/api/batchApi";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ListToolbar } from "@/components/query/ListToolbar";
import { FilterSelect } from "@/components/query/FilterSelect";
import { DataPagination } from "@/components/query/DataPagination";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { STATUS_OPTIONS } from "@/lib/constants";
import { formatDateTime, formatDuration } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";

export function BatchListPage() {
  const qp = usePagedParams(20);
  const query = useQuery({ queryKey: ["batches", qp.params], queryFn: () => batchApi.list(qp.params) });
  return <><PageHeader title="查询批次" description="每次路线扫描生成的任务批次，连接扫描记录与查询任务。" /><ListToolbar keyword={String(qp.params.keyword || "")} onKeywordChange={(v) => qp.setValue("keyword", v)} onReset={qp.reset} onRefresh={() => query.refetch()} filters={<><FilterSelect value={String(qp.params.status || "")} onChange={(v) => qp.setValue("status", v)} options={STATUS_OPTIONS.map((x) => ({ value: x, label: x }))} placeholder="状态" /><FilterSelect value={String(qp.params.trigger_type || "")} onChange={(v) => qp.setValue("trigger_type", v)} options={[{ value: "MANUAL", label: "MANUAL" }, { value: "SCHEDULED", label: "SCHEDULED" }]} placeholder="触发方式" /></>} />{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data!.items.length ? <div className="table-shell"><div className="table-scroll rounded-2xl"><Table><TableHeader><TableRow><TableHead>Batch</TableHead><TableHead>触发</TableHead><TableHead>状态</TableHead><TableHead>任务</TableHead><TableHead>开始</TableHead><TableHead>结束</TableHead><TableHead>耗时</TableHead><TableHead>操作</TableHead></TableRow></TableHeader><TableBody>{query.data!.items.map((batch) => <TableRow key={batch.id}><TableCell className="font-medium">{batch.batch_no}</TableCell><TableCell>{batch.trigger_type}</TableCell><TableCell><StatusBadge status={batch.status} /></TableCell><TableCell>{batch.success_task_count}/{batch.total_task_count} · failed {batch.failed_task_count}</TableCell><TableCell>{formatDateTime(batch.start_time)}</TableCell><TableCell>{formatDateTime(batch.end_time)}</TableCell><TableCell>{formatDuration(batch.duration_seconds)}</TableCell><TableCell><Button asChild size="sm" variant="secondary"><Link to={`/tasks?batch_no=${batch.batch_no}`}>查看任务</Link></Button></TableCell></TableRow>)}</TableBody></Table></div><div className="p-4"><DataPagination page={qp.page} pageSize={qp.pageSize} total={query.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} /></div></div> : <EmptyState title="暂无查询批次" />}</>;
}
