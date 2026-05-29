import { useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { DateField } from "@/components/common/DateField";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DateBatchForm } from "@/components/monitors/DateBatchForm";
import { DataPagination } from "@/components/query/DataPagination";
import { FilterSelect } from "@/components/query/FilterSelect";
import { ListToolbar } from "@/components/query/ListToolbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ENABLED_OPTIONS } from "@/lib/constants";
import { formatDateTime } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";
import type { Monitor } from "@/types/monitor";

export function MonitorDateManager({ monitor }: { monitor: Monitor }) {
  const id = String(monitor.id);
  const [departDate, setDepartDate] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const queryClient = useQueryClient();
  const qp = usePagedParams(20);
  const dates = useQuery({
    queryKey: ["monitor-dates", id, qp.params],
    queryFn: () => monitorApi.dates(id, qp.params),
    placeholderData: keepPreviousData,
  });
  const isRoundTrip = monitor.trip_type === "ROUND_TRIP";
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["monitor-dates"] });
    queryClient.invalidateQueries({ queryKey: ["monitor", id] });
  };

  const handleAdd = () => {
    if (isRoundTrip && !returnDate) {
      toast.error("往返路线必须选择返程日期");
      return;
    }
    add.mutate();
  };
  const add = useMutation({
    mutationFn: () => monitorApi.addDate(id, { depart_date: departDate, return_date: isRoundTrip ? returnDate : undefined }),
    onSuccess: () => {
      toast.success("日期已添加");
      setDepartDate("");
      setReturnDate("");
      invalidate();
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "添加失败"),
  });
  const batch = useMutation({
    mutationFn: (payload: { start_date: string; end_date: string; return_start_date?: string; return_end_date?: string; weekdays: number[] }) => monitorApi.batchDates(id, payload),
    onSuccess: () => {
      toast.success("扫描日期已生成");
      invalidate();
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "生成失败"),
  });
  const toggle = useMutation({ mutationFn: monitorApi.toggleDate, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: monitorApi.removeDate, onSuccess: invalidate });

  return (
    <section id="dates" className="space-y-4">
      <DateBatchForm roundTrip={isRoundTrip} pending={batch.isPending} onGenerate={(payload) => batch.mutate(payload)} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,400px)_1fr]">
        <Card className="border-neutral-200">
          <CardHeader className="p-4">
            <CardTitle className="text-sm">补充单个日期</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-4 pb-4 pt-0">
            <div className={isRoundTrip ? "grid gap-2.5 sm:grid-cols-2" : "grid gap-2.5"}>
              <DateField label="去程日期" placeholder="选择去程日期" value={departDate} onChange={setDepartDate} />
              {isRoundTrip ? <DateField label="返程日期" placeholder="选择返程日期" value={returnDate} onChange={setReturnDate} /> : null}
            </div>
            <Button size="sm" disabled={!departDate || add.isPending} onClick={handleAdd}>
              {add.isPending ? "添加中" : "添加日期"}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-neutral-200">
          <CardHeader className="p-4">
            <CardTitle className="text-sm">已维护日期</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-4 pb-4 pt-0">
            <ListToolbar
              onReset={qp.reset}
              onRefresh={() => dates.refetch()}
              filters={
                <>
                  <FilterSelect value={String(qp.params.enabled || "")} onChange={(v) => qp.setValue("enabled", v)} options={ENABLED_OPTIONS} placeholder="启用状态" />
                </>
              }
            />
            {dates.isLoading ? <LoadingState /> : dates.isError ? <ErrorState error={dates.error} /> : dates.data!.items.length ? (
              <div className="table-shell">
                <div className="table-scroll rounded-2xl">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>去程日期</TableHead>
                      {isRoundTrip ? <TableHead>返程日期</TableHead> : null}
                      <TableHead>状态</TableHead>
                      <TableHead>备注</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dates.data!.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>{item.depart_date}</TableCell>
                        {isRoundTrip ? <TableCell>{item.return_date || "-"}</TableCell> : null}
                        <TableCell><StatusBadge status={item.enabled} /></TableCell>
                        <TableCell>{item.remark || "-"}</TableCell>
                        <TableCell>{formatDateTime(item.create_time)}</TableCell>
                        <TableCell className="space-x-2">
                          <Button size="sm" variant="secondary" onClick={() => toggle.mutate(item.id)}>{item.enabled ? "停用" : "启用"}</Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => remove.mutate(item.id)}>删除</Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
                <div className="p-4">
                  <DataPagination page={qp.page} pageSize={qp.pageSize} total={dates.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
                </div>
              </div>
            ) : <EmptyState title="还没有扫描日期" description="先用上方时间段生成，或补充单个日期。" />}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
