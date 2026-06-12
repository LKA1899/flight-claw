import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { monitorApi } from "@/api/monitorApi";
import { planApi } from "@/api/planApi";
import { priceApi } from "@/api/priceApi";
import { scanApi } from "@/api/scanApi";
import { taskApi } from "@/api/taskApi";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { PriceText } from "@/components/common/PriceText";
import { RouteCell } from "@/components/common/RouteCell";
import { SnapshotLinks } from "@/components/common/SnapshotLinks";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataPagination } from "@/components/query/DataPagination";
import { ResultContextFilter } from "@/components/results/ResultContextFilter";
import { RoundTripClueCard } from "@/components/plans/RoundTripClueCard";
import { RoundTripPlanCard } from "@/components/plans/RoundTripPlanCard";
import { PlanCard } from "@/components/plans/PlanCard";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDateTime, formatMinutes } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";
import type { PlanResult } from "@/types/plan";

const TAB_PLANS = "plans";
const TAB_PRICES = "prices";
const TAB_TASKS = "tasks";

export function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const qp = usePagedParams(20);
  const tab = searchParams.get("tab") || TAB_PLANS;
  const monitorId = searchParams.get("monitor_id") || "";
  const scanId = searchParams.get("scan_id") || "";
  const departDate = searchParams.get("depart_date") || "";

  const monitors = useQuery({ queryKey: ["result-monitors"], queryFn: () => monitorApi.list({ page: 1, page_size: 100 }) });
  const scans = useQuery({
    queryKey: ["result-scan-options", monitorId],
    queryFn: () => scanApi.options(monitorId ? { monitor_id: monitorId } : {}),
    enabled: Boolean(monitorId),
  });
  const selectedScan = scans.data?.find((scan) => String(scan.scan_id) === scanId);
  const batchNo = selectedScan?.batch_no || "";
  const baseParams = {
    page: qp.page,
    page_size: qp.pageSize,
    monitor_id: monitorId,
    batch_no: batchNo,
    ...(departDate ? { depart_date: departDate } : {}),
  };

  const plans = useQuery({
    queryKey: ["result-plans", baseParams],
    queryFn: () => planApi.list({ ...baseParams, latest_scan_only: false }),
    enabled: tab === TAB_PLANS && Boolean(batchNo),
  });
  const prices = useQuery({
    queryKey: ["result-prices", baseParams],
    queryFn: () => priceApi.list(baseParams),
    enabled: tab === TAB_PRICES && Boolean(batchNo),
  });
  const tasks = useQuery({
    queryKey: ["result-tasks", baseParams],
    queryFn: () => taskApi.list(baseParams),
    enabled: tab === TAB_TASKS && Boolean(batchNo),
  });

  useEffect(() => {
    if (!monitorId && monitors.data?.items.length) {
      patchParams({ monitor_id: monitors.data.items[0].id, scan_id: undefined, page: 1 });
    }
  }, [monitorId, monitors.data]);

  useEffect(() => {
    if (monitorId && scans.data?.length && !scanId) {
      patchParams({ scan_id: scans.data[0].scan_id, page: 1 });
    }
  }, [monitorId, scanId, scans.data]);

  const currentRoute = selectedScan?.route_label || monitors.data?.items.find((item) => String(item.id) === monitorId)?.monitor_name;

  return (
    <>
      <PageHeader
        title="扫描结果"
        description={currentRoute && selectedScan ? `${currentRoute} · ${selectedScan.label}` : "选择路线和扫描记录后查看候选方案、价格明细和任务记录。"}
      />

      <ResultContextFilter
        monitors={monitors.data?.items || []}
        scans={scans.data || []}
        monitorId={monitorId}
        scanId={scanId}
        departDate={departDate}
        loadingScans={scans.isLoading}
        onMonitorChange={(value) => patchParams({ monitor_id: value, scan_id: undefined, page: 1 })}
        onScanChange={(value) => patchParams({ scan_id: value, page: 1 })}
        onDepartDateChange={(value) => patchParams({ depart_date: value || undefined, page: 1 })}
        onRefresh={() => {
          monitors.refetch();
          scans.refetch();
          plans.refetch();
          prices.refetch();
          tasks.refetch();
        }}
      />

      {!monitorId ? <EmptyState title="请选择扫描路线" /> : !batchNo ? <EmptyState title="请选择扫描记录" description="当前路线还没有可查看的扫描结果。" /> : (
        <Tabs value={tab} onValueChange={(value) => patchParams({ tab: value, page: 1 })} className="space-y-5">
          <TabsList>
            <TabsTrigger value={TAB_PLANS}>候选方案</TabsTrigger>
            <TabsTrigger value={TAB_PRICES}>价格明细</TabsTrigger>
            <TabsTrigger value={TAB_TASKS}>任务记录</TabsTrigger>
          </TabsList>

          <TabsContent value={TAB_PLANS}>{renderPlans()}</TabsContent>
          <TabsContent value={TAB_PRICES}>{renderPrices()}</TabsContent>
          <TabsContent value={TAB_TASKS}>{renderTasks()}</TabsContent>
        </Tabs>
      )}
    </>
  );

  function patchParams(next: Record<string, unknown>) {
    const params = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    });
    setSearchParams(params);
  }

  function renderPlans() {
    if (plans.isLoading) return <LoadingState />;
    if (plans.isError) return <ErrorState error={plans.error} />;
    if (!plans.data?.items.length) return <EmptyState title="暂无候选方案" />;
    return (
      <>
        <div className="grid gap-4 lg:grid-cols-2">
          {plans.data.items.map((plan) => renderPlanCard(plan))}
        </div>
        <div className="mt-6">
          <DataPagination page={qp.page} pageSize={qp.pageSize} total={plans.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
        </div>
      </>
    );
  }

  function renderPrices() {
    if (prices.isLoading) return <LoadingState />;
    if (prices.isError) return <ErrorState error={prices.error} />;
    if (!prices.data?.items.length) return <EmptyState title="暂无价格明细" />;
    return (
      <div className="table-shell">
        <div className="table-scroll rounded-2xl">
          <Table className="whitespace-nowrap">
            <TableHeader>
              <TableRow>
                <TableHead>路线</TableHead>
                <TableHead>出发日期</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>航班</TableHead>
                <TableHead>出发</TableHead>
                <TableHead>到达</TableHead>
                <TableHead>耗时</TableHead>
                <TableHead>价格</TableHead>
                <TableHead>来源</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {prices.data.items.map((price) => (
                <TableRow key={price.id}>
                  <TableCell><RouteCell from={price.from_city} to={price.to_city} /></TableCell>
                  <TableCell>{price.depart_date}</TableCell>
                  <TableCell>{price.query_type}</TableCell>
                  <TableCell>{price.airline || "-"}<div className="text-xs text-stone-500">{price.flight_no || "-"}</div></TableCell>
                  <TableCell>{price.depart_time || "-"}<div className="text-xs text-stone-500">{price.depart_airport}</div></TableCell>
                  <TableCell>{price.arrive_time || "-"}<div className="text-xs text-stone-500">{price.arrive_airport}</div></TableCell>
                  <TableCell>{formatMinutes(price.duration_minutes)}</TableCell>
                  <TableCell><PriceText value={price.price} /></TableCell>
                  <TableCell><SnapshotLinks taskId={price.task_id} screenshot={price.source_screenshot_path} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="p-4"><DataPagination page={qp.page} pageSize={qp.pageSize} total={prices.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} /></div>
      </div>
    );
  }

  function renderTasks() {
    if (tasks.isLoading) return <LoadingState />;
    if (tasks.isError) return <ErrorState error={tasks.error} />;
    if (!tasks.data?.items.length) return <EmptyState title="暂无任务记录" />;
    return (
      <div className="table-shell">
        <div className="table-scroll rounded-2xl">
          <Table className="whitespace-nowrap">
            <TableHeader>
              <TableRow>
                <TableHead>任务</TableHead>
                <TableHead>路线</TableHead>
                <TableHead>日期</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>截图</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.data.items.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="font-medium">#{task.id}</TableCell>
                  <TableCell><RouteCell from={task.from_city} to={task.to_city} /></TableCell>
                  <TableCell>{task.depart_date}{task.return_date ? <div className="text-xs text-stone-500">返程 {task.return_date}</div> : null}</TableCell>
                  <TableCell>{task.trip_type}<div className="text-xs text-stone-500">{task.query_type}</div></TableCell>
                  <TableCell><StatusBadge status={task.status} /></TableCell>
                  <TableCell><SnapshotLinks taskId={task.id} screenshot={task.screenshot_path} /></TableCell>
                  <TableCell>{formatDateTime(task.create_time)}</TableCell>
                  <TableCell><Button asChild size="sm" variant="secondary"><Link to={`/tasks?scan_id=${task.scan_id || ""}&batch_no=${task.batch_no}`}>诊断</Link></Button></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="p-4"><DataPagination page={qp.page} pageSize={qp.pageSize} total={tasks.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} /></div>
      </div>
    );
  }
}

function renderPlanCard(plan: PlanResult) {
  if (plan.source_type === "ROUNDTRIP_CLUE") {
    return <RoundTripClueCard key={`clue-${plan.id}`} plan={plan} />;
  }
  if (plan.source_type === "ROUNDTRIP_PLAN") {
    return <RoundTripPlanCard key={`rtp-${plan.id}`} plan={plan} />;
  }
  return <PlanCard key={`plan-${plan.id}`} plan={plan} />;
}
