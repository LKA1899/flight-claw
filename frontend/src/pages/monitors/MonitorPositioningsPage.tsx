import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { PageHeader } from "@/components/common/PageHeader";
import { AppSelect } from "@/components/common/AppSelect";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PositioningPayload } from "@/types/monitor";

const initial: PositioningPayload = {
  positioning_city: "",
  positioning_type: "TRAIN",
  estimated_cost: 0,
  estimated_minutes: 0,
  enabled: true,
  sort_no: 100,
  remark: "",
};

export function MonitorPositioningsPage() {
  const { id = "" } = useParams();
  const [form, setForm] = useState<PositioningPayload>(initial);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["monitor-positionings", id], queryFn: () => monitorApi.positionings(id) });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["monitor-positionings", id] });
  const create = useMutation({
    mutationFn: () => monitorApi.createPositioning(id, form),
    onSuccess: () => {
      toast.success("接驳城市已保存");
      setForm(initial);
      invalidate();
    },
  });
  const toggle = useMutation({ mutationFn: monitorApi.togglePositioning, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: monitorApi.removePositioning, onSuccess: invalidate });

  return (
    <>
      <PageHeader title="接驳城市" description="维护火车、高铁、巴士或自助接驳的估算成本和耗时。" />
      <Card className="mb-5">
        <CardContent className="grid gap-3 p-5 md:grid-cols-6">
          <Input placeholder="接驳城市" value={form.positioning_city} onChange={(e) => setForm((x) => ({ ...x, positioning_city: e.target.value }))} />
          <AppSelect value={form.positioning_type} onValueChange={(value) => setForm((x) => ({ ...x, positioning_type: value as PositioningPayload["positioning_type"] }))} options={[{ value: "TRAIN", label: "TRAIN" }, { value: "BUS", label: "BUS" }, { value: "SELF", label: "SELF" }]} />
          <Input type="number" placeholder="估算成本" value={form.estimated_cost} onChange={(e) => setForm((x) => ({ ...x, estimated_cost: Number(e.target.value) }))} />
          <Input type="number" placeholder="估算分钟" value={form.estimated_minutes} onChange={(e) => setForm((x) => ({ ...x, estimated_minutes: Number(e.target.value) }))} />
          <Input type="number" placeholder="排序" value={form.sort_no} onChange={(e) => setForm((x) => ({ ...x, sort_no: Number(e.target.value) }))} />
          <Button disabled={!form.positioning_city || create.isPending} onClick={() => create.mutate()}>保存</Button>
        </CardContent>
      </Card>
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data!.length ? (
        <div className="table-shell">
          <div className="table-scroll rounded-2xl">
          <Table>
            <TableHeader><TableRow><TableHead>城市</TableHead><TableHead>类型</TableHead><TableHead>成本</TableHead><TableHead>耗时</TableHead><TableHead>状态</TableHead><TableHead>操作</TableHead></TableRow></TableHeader>
            <TableBody>{query.data!.map((item) => <TableRow key={item.id}><TableCell>{item.positioning_city}</TableCell><TableCell>{item.positioning_type}</TableCell><TableCell>¥{item.estimated_cost}</TableCell><TableCell>{item.estimated_minutes} 分钟</TableCell><TableCell><StatusBadge status={item.enabled} /></TableCell><TableCell className="space-x-2"><Button size="sm" variant="secondary" onClick={() => toggle.mutate(item.id)}>{item.enabled ? "停用" : "启用"}</Button><Button size="sm" variant="ghost" className="text-red-600" onClick={() => remove.mutate(item.id)}>删除</Button></TableCell></TableRow>)}</TableBody>
          </Table>
          </div>
        </div>
      ) : <EmptyState title="暂无接驳城市" description="启用火车/高铁接驳前，请先配置至少一个接驳城市。" />}
    </>
  );
}
