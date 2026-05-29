import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { TransferPayload } from "@/types/monitor";

const initial: TransferPayload = {
  transfer_city: "",
  transfer_airports: "",
  enabled: true,
  sort_no: 100,
  remark: "",
};

export function MonitorTransfersPage() {
  const { id = "" } = useParams();
  const [form, setForm] = useState<TransferPayload>(initial);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["monitor-transfers", id], queryFn: () => monitorApi.transfers(id) });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["monitor-transfers", id] });
  const create = useMutation({
    mutationFn: () => monitorApi.createTransfer(id, form),
    onSuccess: () => {
      toast.success("中转城市已保存");
      setForm(initial);
      invalidate();
    },
  });
  const toggle = useMutation({ mutationFn: monitorApi.toggleTransfer, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: monitorApi.removeTransfer, onSuccess: invalidate });

  return (
    <>
      <PageHeader title="中转城市" description="维护允许的中转城市候选和机场代码。" />
      <Card className="mb-5">
        <CardContent className="grid gap-3 p-5 md:grid-cols-4">
          <Input placeholder="中转城市" value={form.transfer_city} onChange={(e) => setForm((x) => ({ ...x, transfer_city: e.target.value }))} />
          <Input placeholder="机场代码，如 ICN,GMP" value={form.transfer_airports || ""} onChange={(e) => setForm((x) => ({ ...x, transfer_airports: e.target.value }))} />
          <Input type="number" placeholder="排序" value={form.sort_no} onChange={(e) => setForm((x) => ({ ...x, sort_no: Number(e.target.value) }))} />
          <Button disabled={!form.transfer_city || create.isPending} onClick={() => create.mutate()}>保存</Button>
        </CardContent>
      </Card>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data!.length ? (
        <div className="table-shell">
          <div className="table-scroll rounded-2xl">
          <Table>
            <TableHeader><TableRow><TableHead>城市</TableHead><TableHead>机场</TableHead><TableHead>状态</TableHead><TableHead>操作</TableHead></TableRow></TableHeader>
            <TableBody>{query.data!.map((item) => <TableRow key={item.id}><TableCell>{item.transfer_city}</TableCell><TableCell>{item.transfer_airports || "-"}</TableCell><TableCell><StatusBadge status={item.enabled} /></TableCell><TableCell className="space-x-2"><Button size="sm" variant="secondary" onClick={() => toggle.mutate(item.id)}>{item.enabled ? "停用" : "启用"}</Button><Button size="sm" variant="ghost" className="text-red-600" onClick={() => remove.mutate(item.id)}>删除</Button></TableCell></TableRow>)}</TableBody>
          </Table>
          </div>
        </div>
      ) : <EmptyState title="暂无中转城市" description="未配置时会生成通用中转任务，让 OTA 返回中转方案。" />}
    </>
  );
}
