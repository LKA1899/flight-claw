import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { planApi } from "@/api/planApi";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ListToolbar } from "@/components/query/ListToolbar";
import { DataPagination } from "@/components/query/DataPagination";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { usePagedParams } from "@/lib/queryParams";
import { PlanCard } from "@/components/plans/PlanCard";
import { RoundTripClueCard } from "@/components/plans/RoundTripClueCard";
import { RoundTripPlanCard } from "@/components/plans/RoundTripPlanCard";
import type { PlanResult } from "@/types/plan";

const TAB_ONEWAY = "oneway";
const TAB_ROUNDTRIP = "roundtrip";
const TAB_CLUE = "clue";

export function PlanListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || TAB_ONEWAY;
  const qp = usePagedParams(20);

  const setTab = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", value);
    next.delete("page");
    setSearchParams(next);
  };

  const apiParams: Record<string, unknown> = {
    ...qp.params,
  };
  if (apiParams.monitor_id && !/^\d+$/.test(String(apiParams.monitor_id))) {
    delete apiParams.monitor_id;
  }
  if (tab === TAB_ONEWAY) {
    apiParams.source_type = "ONE_WAY_PLAN";
  }
  if (tab === TAB_ROUNDTRIP) {
    apiParams.include_roundtrip_plans = true;
    apiParams.source_type = "ROUNDTRIP_PLAN";
  }
  if (tab === TAB_CLUE) {
    apiParams.source_type = "ROUNDTRIP_CLUE";
  }

  const query = useQuery({
    queryKey: ["plans", apiParams],
    queryFn: () => planApi.list(apiParams as Record<string, string | number | boolean>),
  });

  function renderCard(plan: PlanResult) {
    if (plan.source_type === "ROUNDTRIP_CLUE") {
      return <RoundTripClueCard key={`clue-${plan.id}`} plan={plan} />;
    }
    if (plan.source_type === "ROUNDTRIP_PLAN") {
      return <RoundTripPlanCard key={`rtp-${plan.id}`} plan={plan} />;
    }
    return <PlanCard key={`plan-${plan.id}`} plan={plan} />;
  }

  return (
    <>
      <PageHeader title="候选方案" description="由价格快照生成的单程方案、往返线索和完整往返组合，用于后续筛选今日机会。" />
      <Tabs value={tab} onValueChange={setTab} className="space-y-5">
        <TabsList>
          <TabsTrigger value={TAB_ONEWAY}>单程</TabsTrigger>
          <TabsTrigger value={TAB_ROUNDTRIP}>往返</TabsTrigger>
          <TabsTrigger value={TAB_CLUE}>往返线索</TabsTrigger>
        </TabsList>

        <ListToolbar onReset={qp.reset} onRefresh={() => query.refetch()} filters={
          <>
            <Input placeholder="batch_no" value={String(qp.params.batch_no || "")} onChange={(e) => qp.setValue("batch_no", e.target.value)} className="w-56" />
            <Input type="number" placeholder="monitor_id" value={String(qp.params.monitor_id || "")} onChange={(e) => qp.setValue("monitor_id", e.target.value)} className="w-32" />
            <Input type="date" value={String(qp.params.depart_date || "")} onChange={(e) => qp.setValue("depart_date", e.target.value)} className="w-40" />
          </>
        } />

        <TabsContent value={TAB_ONEWAY}>
          {renderContent()}
        </TabsContent>
        <TabsContent value={TAB_ROUNDTRIP}>
          {renderContent()}
        </TabsContent>
        <TabsContent value={TAB_CLUE}>
          {renderContent()}
        </TabsContent>
      </Tabs>
    </>
  );

  function renderContent() {
    if (query.isLoading) return <LoadingState />;
    if (query.isError) return <ErrorState error={query.error} />;
    if (!query.data?.items.length) {
      const emptyDesc = tab === TAB_ONEWAY ? "暂无单程候选方案。" : tab === TAB_ROUNDTRIP ? "暂无完整往返组合，深度扫描展开返程后会在这里生成。" : "轻量扫描或展开失败的去程会显示往返起价线索。";
      return <EmptyState title="暂无候选方案" description={emptyDesc} />;
    }
    return (
      <>
        <div className="grid gap-4 lg:grid-cols-2">
          {query.data.items.map((plan) => renderCard(plan))}
        </div>
        <DataPagination page={qp.page} pageSize={qp.pageSize} total={query.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
      </>
    );
  }
}
