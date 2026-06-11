import { useQuery } from "@tanstack/react-query";
import { priceApi } from "@/api/priceApi";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { PriceText } from "@/components/common/PriceText";
import { RouteCell } from "@/components/common/RouteCell";
import { SnapshotLinks } from "@/components/common/SnapshotLinks";
import { DataPagination } from "@/components/query/DataPagination";
import { ListToolbar } from "@/components/query/ListToolbar";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, formatMinutes, formatPrice } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";
import type { PriceRaw } from "@/types/price";

export function PriceListPage() {
  const qp = usePagedParams(20);
  const query = useQuery({ queryKey: ["prices", qp.params], queryFn: () => priceApi.list(qp.params) });

  return (
    <>
      <PageHeader title="价格快照" description="从页面可见文本解析出的结构化价格数据，来源保留截图用于追踪。" />
      <ListToolbar
        keyword={String(qp.params.keyword || "")}
        onKeywordChange={(value) => qp.setValue("keyword", value)}
        onReset={qp.reset}
        onRefresh={() => query.refetch()}
        filters={
          <>
            <Input placeholder="batch_no" value={String(qp.params.batch_no || "")} onChange={(event) => qp.setValue("batch_no", event.target.value)} className="w-56" />
            <Input placeholder="monitor_id" value={String(qp.params.monitor_id || "")} onChange={(event) => qp.setValue("monitor_id", event.target.value)} className="w-32" />
            <Input type="date" value={String(qp.params.depart_date || "")} onChange={(event) => qp.setValue("depart_date", event.target.value)} className="w-40" />
            <Input placeholder="min" value={String(qp.params.min_price || "")} onChange={(event) => qp.setValue("min_price", event.target.value)} className="w-24" />
            <Input placeholder="max" value={String(qp.params.max_price || "")} onChange={(event) => qp.setValue("max_price", event.target.value)} className="w-24" />
          </>
        }
      />
      {query.isLoading ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : query.data!.items.length ? (
        <div className="table-shell">
          <div className="table-scroll rounded-2xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>路线</TableHead>
                <TableHead>日期</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>航司</TableHead>
                <TableHead>航班</TableHead>
                <TableHead>出发</TableHead>
                <TableHead>到达</TableHead>
                <TableHead>耗时</TableHead>
                <TableHead>中转</TableHead>
                <TableHead>价格</TableHead>
                <TableHead>行李</TableHead>
                <TableHead>来源</TableHead>
                <TableHead>解析时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.data!.items.map((price) => (
                <TableRow key={price.id}>
                  <TableCell><RouteCell from={price.from_city} to={price.to_city} /></TableCell>
                  <TableCell>{price.depart_date}</TableCell>
                  <TableCell>{price.query_type === "TRANSFER" ? "中转" : "直飞"}</TableCell>
                  <TableCell>{price.airline || "-"}</TableCell>
                  <TableCell>{price.flight_no || "-"}</TableCell>
                  <TableCell>{price.depart_time || "-"}<div className="text-xs text-stone-500">{price.depart_airport}</div></TableCell>
                  <TableCell>{price.arrive_time || "-"}<div className="text-xs text-stone-500">{price.arrive_airport}</div></TableCell>
                  <TableCell>{formatMinutes(price.duration_minutes)}</TableCell>
                  <TableCell>{price.transfer_count ? `${price.transfer_count}${price.transfer_city ? ` · ${price.transfer_city}` : ""}` : "0"}</TableCell>
                  <TableCell>
                    <PriceText value={price.price} />
                    <PriceChange price={price} />
                  </TableCell>
                  <TableCell>{price.baggage_info || "-"}</TableCell>
                  <TableCell><SnapshotLinks taskId={price.task_id} screenshot={price.source_screenshot_path} /></TableCell>
                  <TableCell>{formatDateTime(price.create_time)}</TableCell>
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
        <EmptyState title="暂无价格快照" />
      )}
    </>
  );
}

function PriceChange({ price }: { price: PriceRaw }) {
  if (price.previous_price == null || price.price_delta == null) {
    return <div className="mt-1 text-xs text-stone-400">首次记录</div>;
  }
  if (price.price_delta === 0) {
    return <div className="mt-1 text-xs text-stone-500">较上次持平</div>;
  }
  const dropped = price.price_delta < 0;
  return (
    <div className={dropped ? "mt-1 text-xs text-green-600" : "mt-1 text-xs text-red-600"}>
      较上次{dropped ? "降" : "涨"} {formatPrice(Math.abs(price.price_delta))}
      {price.previous_price_time ? <span className="ml-1 text-stone-400">({formatDateTime(price.previous_price_time)})</span> : null}
    </div>
  );
}
