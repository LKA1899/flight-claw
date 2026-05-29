import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { MonitorForm } from "@/components/monitors/MonitorForm";
import { MonitorDateManager } from "@/components/monitors/MonitorDateManager";
import { Button } from "@/components/ui/button";
import type { MonitorPayload } from "@/types/monitor";

export function MonitorEditPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["monitor", id], queryFn: () => monitorApi.get(id) });
  const mutation = useMutation({ mutationFn: (payload: MonitorPayload) => monitorApi.update(id, payload), onSuccess: () => { toast.success("关注路线已保存"); navigate("/monitors"); }, onError: (error) => toast.error(error instanceof Error ? error.message : "保存失败") });
  if (query.isLoading) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} />;
  const formId = `monitor-form-${id}`;
  return (
    <>
      <PageHeader title="维护关注路线" description="调整路线基础信息、预算限制、往返策略和扫描日期。" />
      <div className="space-y-8">
        <MonitorForm formId={formId} hideActions value={query.data} onSubmit={(payload) => mutation.mutate(payload)} submitting={mutation.isPending} />
        <MonitorDateManager monitor={query.data!} />
        <div className="flex justify-end gap-2 rounded-2xl border border-border bg-white p-3 shadow-soft">
          <Button type="button" variant="secondary" onClick={() => history.back()}>取消</Button>
          <Button type="submit" form={formId} disabled={mutation.isPending}>{mutation.isPending ? "保存中..." : "保存"}</Button>
        </div>
      </div>
    </>
  );
}
