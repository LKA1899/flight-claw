import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { roundtripApi } from "@/api/roundtripApi";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { PriceText } from "@/components/common/PriceText";
import { RouteCell } from "@/components/common/RouteCell";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataPagination } from "@/components/query/DataPagination";
import { ListToolbar } from "@/components/query/ListToolbar";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMinutes } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";

export function RoundTripResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "plans" ? "plans" : "outbounds";
  const qp = usePagedParams(20);
  const params = { ...qp.params, task_id: searchParams.get("task_id") || qp.params.task_id };
  const outbounds = useQuery({ queryKey: ["roundtrip-outbounds", params], queryFn: () => roundtripApi.outbounds(params) });
  const plans = useQuery({ queryKey: ["roundtrip-plans", params], queryFn: () => roundtripApi.plans(params) });

  const setTab = (value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", value);
    setSearchParams(next);
  };

  return (
    <>
      <PageHeader title="往返结果" description="区分去程候选、往返起价和完整组合，避免把不完整数据作为最终推荐。" />
      <Tabs value={tab} onValueChange={setTab} className="space-y-5">
        <TabsList><TabsTrigger value="outbounds">去程候选</TabsTrigger><TabsTrigger value="plans">完整组合</TabsTrigger></TabsList>
        <ListToolbar onReset={qp.reset} onRefresh={() => tab === "outbounds" ? outbounds.refetch() : plans.refetch()} filters={<><Input placeholder="task_id" value={String(params.task_id || "")} onChange={(e) => qp.setValue("task_id", e.target.value)} className="w-36" /><Input placeholder="monitor_id" value={String(qp.params.monitor_id || "")} onChange={(e) => qp.setValue("monitor_id", e.target.value)} className="w-36" /><Input placeholder="batch_no" value={String(qp.params.batch_no || "")} onChange={(e) => qp.setValue("batch_no", e.target.value)} className="w-56" /></>} />
        <TabsContent value="outbounds">
          {outbounds.isLoading ? <LoadingState /> : outbounds.isError ? <ErrorState error={outbounds.error} /> : outbounds.data!.items.length ? (
            <div className="table-shell">
              <div className="table-scroll rounded-2xl">
              <Table>
                <TableHeader><TableRow><TableHead>路线</TableHead><TableHead>日期</TableHead><TableHead>航班</TableHead><TableHead>时间</TableHead><TableHead>耗时</TableHead><TableHead>往返起价</TableHead><TableHead>返程状态</TableHead><TableHead>完整度</TableHead></TableRow></TableHeader>
                <TableBody>{outbounds.data!.items.map((item) => <TableRow key={item.id}><TableCell><RouteCell from={item.from_city} to={item.to_city} /></TableCell><TableCell>{item.depart_date}<div className="text-xs text-stone-500">返程 {item.return_date}</div></TableCell><TableCell>{item.airline || "-"}<div className="text-xs text-stone-500">{item.flight_no || "-"}</div></TableCell><TableCell>{item.depart_time || "-"}{" -> "}{item.arrive_time || "-"}</TableCell><TableCell>{formatMinutes(item.duration_minutes)}</TableCell><TableCell><div className="text-xs text-stone-500">往返起价</div><PriceText value={item.display_total_price} /></TableCell><TableCell><StatusBadge status={item.return_detail_status} /></TableCell><TableCell>{item.data_completeness}</TableCell></TableRow>)}</TableBody>
              </Table>
              </div>
              <div className="p-4"><DataPagination page={qp.page} pageSize={qp.pageSize} total={outbounds.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} /></div>
            </div>
          ) : <EmptyState title="暂无去程候选" description="轻量扫描完成后会显示往返起价线索。" />}
        </TabsContent>
        <TabsContent value="plans">
          {plans.isLoading ? <LoadingState /> : plans.isError ? <ErrorState error={plans.error} /> : plans.data!.items.length ? (
            <div className="table-shell">
              <div className="table-scroll rounded-2xl">
              <Table>
                <TableHeader><TableRow><TableHead>总价</TableHead><TableHead>日期</TableHead><TableHead>去程摘要</TableHead><TableHead>返程摘要</TableHead><TableHead>总耗时</TableHead><TableHead>中转</TableHead><TableHead>风险</TableHead><TableHead>评分</TableHead><TableHead>推荐理由</TableHead></TableRow></TableHeader>
                <TableBody>{plans.data!.items.map((item) => <TableRow key={item.id}><TableCell><PriceText value={item.total_price} /></TableCell><TableCell>{item.depart_date}<div className="text-xs text-stone-500">返程 {item.return_date}</div></TableCell><TableCell>{item.outbound_summary || "-"}</TableCell><TableCell>{item.return_summary || "-"}</TableCell><TableCell>{formatMinutes(item.total_duration_minutes)}</TableCell><TableCell>{item.total_transfer_count ?? "-"}</TableCell><TableCell>{item.risk_level ? <StatusBadge status={item.risk_level} /> : "-"}</TableCell><TableCell>{item.score ?? "-"}</TableCell><TableCell>{item.reason || "-"}</TableCell></TableRow>)}</TableBody>
              </Table>
              </div>
              <div className="p-4"><DataPagination page={qp.page} pageSize={qp.pageSize} total={plans.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} /></div>
            </div>
          ) : <EmptyState title="暂无完整组合" description="只有展开返程并拿到完整组合总价后才会生成正式方案。" />}
        </TabsContent>
      </Tabs>
    </>
  );
}
