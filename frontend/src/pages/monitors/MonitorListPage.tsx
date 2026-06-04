import { Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { RouteCard } from "@/components/monitors/RouteCard";
import { ListToolbar } from "@/components/query/ListToolbar";
import { FilterSelect } from "@/components/query/FilterSelect";
import { DataPagination } from "@/components/query/DataPagination";
import { Button } from "@/components/ui/button";
import { ENABLED_OPTIONS, PLATFORM_OPTIONS, STRATEGY_OPTIONS } from "@/lib/constants";
import { usePagedParams } from "@/lib/queryParams";

export function MonitorListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const qp = usePagedParams(12);
  const query = useQuery({ queryKey: ["monitors", qp.params], queryFn: () => monitorApi.list(qp.params) });
  const remove = useMutation({ mutationFn: monitorApi.remove, onSuccess: () => { toast.success("关注路线已删除"); queryClient.invalidateQueries({ queryKey: ["monitors"] }); } });
  const toggle = useMutation({ mutationFn: monitorApi.toggle, onSuccess: () => { toast.success("状态已更新"); queryClient.invalidateQueries({ queryKey: ["monitors"] }); } });
  const scanNow = useMutation({
    mutationFn: monitorApi.scanNow,
    onSuccess: (data) => {
      toast.success("扫描已启动");
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
      navigate(`/scans/${data.scan_id}`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "启动扫描失败"),
  });
  const cancelScan = useMutation({
    mutationFn: monitorApi.cancelRunningScan,
    onSuccess: () => {
      toast.success("已请求停止扫描");
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "停止扫描失败"),
  });

  return (
    <>
      <PageHeader title="关注路线" description="维护路线、日期和扫描策略。每条路线可以立即扫描，也可以配置独立定时扫描。" actions={<Button asChild><Link to="/monitors/new"><Plus className="h-4 w-4" />新建关注路线</Link></Button>} />
      <ListToolbar
        keyword={String(qp.params.keyword || "")}
        onKeywordChange={(value) => qp.setValue("keyword", value)}
        onReset={qp.reset}
        onRefresh={() => query.refetch()}
        filters={
          <>
            <FilterSelect value={String(qp.params.enabled || "")} onChange={(value) => qp.setValue("enabled", value)} options={ENABLED_OPTIONS} placeholder="启用状态" />
            <FilterSelect value={String(qp.params.platform || "")} onChange={(value) => qp.setValue("platform", value)} options={PLATFORM_OPTIONS} placeholder="平台" />
            <FilterSelect value={String(qp.params.strategy || "")} onChange={(value) => qp.setValue("strategy", value)} options={STRATEGY_OPTIONS} placeholder="策略" />
          </>
        }
      />
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : query.data!.items.length ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {query.data!.items.map((monitor) => (
              <ConfirmDialog key={monitor.id} title="删除关注路线？" description="删除后相关日期配置会一起删除。" onConfirm={() => remove.mutate(monitor.id)}>
                {(open) => (
                  <RouteCard
                    monitor={monitor}
                    onDelete={open}
                    onToggle={() => toggle.mutate(monitor.id)}
                    onScan={() => scanNow.mutate(monitor.id)}
                    onCancelScan={() => cancelScan.mutate(monitor.id)}
                    scanning={scanNow.isPending}
                  />
                )}
              </ConfirmDialog>
            ))}
          </div>
          <DataPagination page={qp.page} pageSize={qp.pageSize} total={query.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
        </>
      ) : <EmptyState title="还没有关注路线" description="创建第一条路线后，FlightScan 会按日期生成本地浏览器查询任务。" />}
    </>
  );
}
