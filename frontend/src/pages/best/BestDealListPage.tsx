import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { bestApi } from "@/api/bestApi";
import { planApi } from "@/api/planApi";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PriceText } from "@/components/common/PriceText";
import { RiskBadge } from "@/components/common/RiskBadge";
import { RouteText } from "@/components/common/RouteText";
import { ListToolbar } from "@/components/query/ListToolbar";
import { DataPagination } from "@/components/query/DataPagination";
import { MonitorFilterSelect } from "@/components/query/MonitorFilterSelect";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePagedParams } from "@/lib/queryParams";
import { RoundTripPlanCard } from "@/components/plans/RoundTripPlanCard";
import { RoundTripClueCard } from "@/components/plans/RoundTripClueCard";
import { PlanFlightMeta } from "@/components/plans/PlanFlightMeta";
import type { PlanResult } from "@/types/plan";
import type { ListParams } from "@/types/common";

const TAB_ONEWAY = "oneway";
const TAB_ROUNDTRIP = "roundtrip";
const SUB_PLANS = "plans";
const SUB_CLUES = "clues";

export function BestDealListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === TAB_ROUNDTRIP ? TAB_ROUNDTRIP : TAB_ONEWAY;
  const sub = searchParams.get("sub") === SUB_CLUES ? SUB_CLUES : SUB_PLANS;
  const qp = usePagedParams(20);

  const setTab = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", value);
    next.delete("page");
    next.delete("sub");
    setSearchParams(next);
  };

  const setSub = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("sub", value);
    next.delete("page");
    setSearchParams(next);
  };

  const oneWay = useQuery({
    queryKey: ["best", filteredParams(qp.params)],
    queryFn: () => bestApi.list(filteredParams(qp.params)),
    enabled: tab === TAB_ONEWAY,
  });

  const roundTripPlans = useQuery({
    queryKey: ["best-roundtrip-plans", filteredParams(qp.params)],
    queryFn: () => planApi.list({ ...filteredParams(qp.params), source_type: "ROUNDTRIP_PLAN", include_roundtrip_plans: true }),
    enabled: tab === TAB_ROUNDTRIP && sub === SUB_PLANS,
  });

  const roundTripClues = useQuery({
    queryKey: ["best-roundtrip-clues", filteredParams(qp.params)],
    queryFn: () => planApi.list({ ...filteredParams(qp.params), source_type: "ROUNDTRIP_CLUE" }),
    enabled: tab === TAB_ROUNDTRIP && sub === SUB_CLUES,
  });

  const sharedFilters = (
    <>
      <MonitorFilterSelect value={String(qp.params.monitor_id || "")} onChange={(value) => qp.setValue("monitor_id", value)} />
      <Input placeholder="batch_no" value={String(qp.params.batch_no || "")} onChange={(e) => qp.setValue("batch_no", e.target.value)} className="w-56" />
      <Input type="date" value={String(qp.params.depart_date || "")} onChange={(e) => qp.setValue("depart_date", e.target.value)} className="w-40" />
    </>
  );

  const refreshAll = () => {
    oneWay.refetch();
    roundTripPlans.refetch();
    roundTripClues.refetch();
  };

  return (
    <>
      <PageHeader
        title="今日机会"
        description="分页签展示单程推荐、往返完整组合和潜在低价线索，仅完整方案可进入正式推荐。"
      />

      <Tabs value={tab} onValueChange={setTab} className="space-y-5">
        <TabsList>
          <TabsTrigger value={TAB_ONEWAY}>单程</TabsTrigger>
          <TabsTrigger value={TAB_ROUNDTRIP}>往返</TabsTrigger>
        </TabsList>

        <ListToolbar onReset={qp.reset} onRefresh={refreshAll} filters={sharedFilters} />

        {/* ====== 单程 Tab ====== */}
        <TabsContent value={TAB_ONEWAY}>
          {oneWay.isLoading ? <LoadingState /> : oneWay.isError ? <ErrorState error={oneWay.error} /> : oneWay.data?.items.length ? (
            <>
              <div className="grid gap-4 lg:grid-cols-2">
                {oneWay.data.items.map((item) => (
                  <Card key={`oneway-${item.id}`}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Badge className="border-sky-200 bg-sky-50 text-sky-700">单程</Badge>
                            <span className="text-sm text-stone-500">{item.depart_date}</span>
                          </div>
                          <CardTitle>{item.monitor_name || "单程机会"}</CardTitle>
                          <p className="mt-2 text-sm text-stone-500">
                            {item.summary || "基于当前批次价格快照生成。"}
                          </p>
                        </div>
                        <PriceText value={item.best_price} trend={item.price_trend} />
                      </div>
                    </CardHeader>
                    <CardContent className="grid gap-3 md:grid-cols-2">
                      <Deal label="综合最优" plan={item.best_plan} />
                      <Deal label="今日最低价" plan={item.cheapest_plan} />
                      <Deal label="最稳妥" plan={item.safest_plan} />
                      <Deal label="激进省钱" plan={item.aggressive_plan} />
                    </CardContent>
                  </Card>
                ))}
              </div>
              <div className="mt-6">
                <DataPagination page={qp.page} pageSize={qp.pageSize} total={oneWay.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
              </div>
            </>
          ) : (
            <EmptyState title="暂无单程推荐" description="当前批次未生成单程最佳方案。" />
          )}
        </TabsContent>

        {/* ====== 往返 Tab ====== */}
        <TabsContent value={TAB_ROUNDTRIP}>
          <Tabs value={sub} onValueChange={setSub} className="space-y-5">
            <TabsList>
              <TabsTrigger value={SUB_PLANS}>完整组合</TabsTrigger>
              <TabsTrigger value={SUB_CLUES}>潜在低价线索</TabsTrigger>
            </TabsList>

            {/* 完整组合 */}
            <TabsContent value={SUB_PLANS}>
              {roundTripPlans.isLoading ? <LoadingState /> : roundTripPlans.isError ? <ErrorState error={roundTripPlans.error} /> : roundTripPlans.data?.items.length ? (
                <>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {roundTripPlans.data.items.map((plan) => (
                      <RoundTripPlanCard key={`rtp-${plan.id}`} plan={plan} />
                    ))}
                  </div>
                  <div className="mt-6">
                    <DataPagination page={qp.page} pageSize={qp.pageSize} total={roundTripPlans.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
                  </div>
                </>
              ) : (
                <EmptyState title="暂无完整往返组合" description="深度扫描展开返程后，会在这里生成完整购票方案。" />
              )}
            </TabsContent>

            {/* 潜在低价线索 */}
            <TabsContent value={SUB_CLUES}>
              {roundTripClues.isLoading ? <LoadingState /> : roundTripClues.isError ? <ErrorState error={roundTripClues.error} /> : roundTripClues.data?.items.length ? (
                <>
                  <Alert className="mb-4 border-amber-300 bg-amber-50">
                    <AlertDescription>
                      这些是去程列表上展示的往返起价，未包含明确的返程航班。需要展开返程后才能确认完整往返总价，不能作为最终购票推荐。
                    </AlertDescription>
                  </Alert>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {roundTripClues.data.items.map((plan) => (
                      <RoundTripClueCard key={`clue-${plan.id}`} plan={plan} />
                    ))}
                  </div>
                  <div className="mt-6">
                    <DataPagination page={qp.page} pageSize={qp.pageSize} total={roundTripClues.data.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
                  </div>
                </>
              ) : (
                <EmptyState title="暂无潜在低价线索" description="轻量扫描或展开失败的去程会在这里显示往返起价线索。" />
              )}
            </TabsContent>
          </Tabs>
        </TabsContent>
      </Tabs>
    </>
  );
}

function filteredParams(params: ListParams): ListParams {
  const next = { ...params };
  if (next.monitor_id && !/^\d+$/.test(String(next.monitor_id))) {
    delete next.monitor_id;
  }
  return next;
}

function Deal({ label, plan }: { label: string; plan?: PlanResult | null }) {
  return (
    <div className="rounded-xl border border-border bg-[#fbf8f4] p-3">
      <div className="text-xs text-stone-500">{label}</div>
      {plan ? (
        <>
          <div className="mt-1 text-sm font-medium text-ink">{plan.title}</div>
          <div className="mt-0.5">
            <RouteText from={plan.from_city} to={plan.to_city} tripType={plan.trip_type} />
          </div>
          <div className="mt-2">
            <PlanFlightMeta
              label="航班"
              airline={plan.airline}
              flightNo={plan.flight_no}
              departTime={plan.depart_time}
              arriveTime={plan.arrive_time}
              departAirport={plan.depart_airport}
              arriveAirport={plan.arrive_airport}
            />
          </div>
          <div className="mt-2 flex items-center justify-between">
            <PriceText value={plan.total_price} />
            <RiskBadge risk={plan.risk_level} />
          </div>
        </>
      ) : (
        <div className="mt-2 text-sm text-stone-400">暂无</div>
      )}
    </div>
  );
}
