import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import type { MonitorSchedulePayload } from "@/types/monitor";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";

const initial: MonitorSchedulePayload = {
  schedule_enabled: false,
  schedule_cron: "0 9 * * *",
  schedule_timezone: "Asia/Shanghai",
  schedule_remark: "",
};

export function MonitorSchedulePage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const monitorQuery = useQuery({ queryKey: ["monitor", id], queryFn: () => monitorApi.get(id) });
  const [form, setForm] = useState<MonitorSchedulePayload>(initial);

  useEffect(() => {
    if (!monitorQuery.data) return;
    setForm({
      schedule_enabled: Boolean(monitorQuery.data.schedule_enabled),
      schedule_cron: monitorQuery.data.schedule_cron || "0 9 * * *",
      schedule_timezone: monitorQuery.data.schedule_timezone || "Asia/Shanghai",
      schedule_remark: monitorQuery.data.schedule_remark || "",
    });
  }, [monitorQuery.data]);

  const save = useMutation({
    mutationFn: () => monitorApi.updateSchedule(id, form),
    onSuccess: () => {
      toast.success("定时扫描已保存");
      queryClient.invalidateQueries({ queryKey: ["monitor", id] });
      navigate(`/monitors/${id}`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "保存失败"),
  });

  if (monitorQuery.isLoading) return <LoadingState />;
  if (monitorQuery.isError) return <ErrorState error={monitorQuery.error} />;

  const monitor = monitorQuery.data!;

  return (
    <>
      <PageHeader title="定时扫描" description={`${monitor.monitor_name} 的路线级扫描计划。`} actions={<Button asChild variant="secondary"><Link to={`/monitors/${id}`}>返回路线</Link></Button>} />
      <div className="grid gap-5 lg:grid-cols-[1fr_.75fr]">
        <Card>
          <CardHeader><CardTitle>计划配置</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between rounded-xl border border-border bg-white p-4">
              <div>
                <Label>启用定时扫描</Label>
                <div className="mt-1 text-sm text-stone-500">开启后，后端服务启动时会注册这条路线的定时任务。</div>
              </div>
              <Switch checked={form.schedule_enabled} onCheckedChange={(checked) => setForm((current) => ({ ...current, schedule_enabled: checked }))} />
            </div>

            <div className="space-y-2">
              <Label>Cron 表达式</Label>
              <Input value={form.schedule_cron || ""} onChange={(event) => setForm((current) => ({ ...current, schedule_cron: event.target.value }))} placeholder="0 9 * * *" />
              <div className="flex flex-wrap gap-2 pt-1">
                <Button type="button" variant="secondary" size="sm" onClick={() => setForm((current) => ({ ...current, schedule_cron: "0 9 * * *" }))}>每天 09:00</Button>
                <Button type="button" variant="secondary" size="sm" onClick={() => setForm((current) => ({ ...current, schedule_cron: "0 18 * * *" }))}>每天 18:00</Button>
                <Button type="button" variant="secondary" size="sm" onClick={() => setForm((current) => ({ ...current, schedule_cron: "0 9 * * 5" }))}>每周五 09:00</Button>
                <Button type="button" variant="secondary" size="sm" onClick={() => setForm((current) => ({ ...current, schedule_cron: "0 */3 * * *" }))}>每 3 小时</Button>
                <Button type="button" variant="secondary" size="sm" onClick={() => setForm((current) => ({ ...current, schedule_cron: "0 */6 * * *" }))}>每 6 小时</Button>
                <Button type="button" variant="secondary" size="sm" onClick={() => setForm((current) => ({ ...current, schedule_cron: "0 */12 * * *" }))}>每 12 小时</Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label>时区</Label>
              <Input value={form.schedule_timezone || ""} onChange={(event) => setForm((current) => ({ ...current, schedule_timezone: event.target.value }))} placeholder="Asia/Shanghai" />
            </div>

            <div className="space-y-2">
              <Label>备注</Label>
              <Textarea value={form.schedule_remark || ""} onChange={(event) => setForm((current) => ({ ...current, schedule_remark: event.target.value }))} placeholder="例如：每天早上看一次国庆价格" />
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              本地定时任务需要后端服务保持运行；电脑休眠或服务关闭时不会执行。不建议设置高频扫描，个人使用建议每天 1-2 次。
            </div>

            <Button onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending ? "保存中" : "保存定时扫描"}</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>运行状态</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-stone-500">最近扫描</span><span>{formatDateTime(monitor.last_scan_time)}</span></div>
            <div className="flex justify-between"><span className="text-stone-500">最近状态</span><span>{monitor.last_scan_status || "-"}</span></div>
            <div className="flex justify-between"><span className="text-stone-500">下次扫描</span><span>{formatDateTime(monitor.next_scan_time)}</span></div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
