import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { monitorApi } from "@/api/monitorApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MonitorForm } from "@/components/monitors/MonitorForm";
import { MonitorDateManager } from "@/components/monitors/MonitorDateManager";
import { Button } from "@/components/ui/button";
import type { Monitor, MonitorPayload } from "@/types/monitor";

export function MonitorCreatePage() {
  const navigate = useNavigate();
  const [createdMonitor, setCreatedMonitor] = useState<Monitor | null>(null);
  const mutation = useMutation({
    mutationFn: (payload: MonitorPayload) => monitorApi.create(payload),
    onSuccess: (monitor) => {
      toast.success("路线已创建，请配置扫描日期");
      setCreatedMonitor(monitor);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "保存失败"),
  });

  return (
    <>
      <PageHeader title="新建关注路线" description="配置路线基础信息，保存后可继续配置扫描日期。" />
      <div className="space-y-6">
        <MonitorForm hideActions={!!createdMonitor} onSubmit={(payload) => mutation.mutate(payload)} submitting={mutation.isPending} />
        {createdMonitor ? (
          <>
            <MonitorDateManager monitor={createdMonitor} />
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => navigate("/monitors")}>完成</Button>
              <Button onClick={() => navigate(`/monitors/${createdMonitor.id}/edit#dates`)}>后续维护</Button>
            </div>
          </>
        ) : null}
      </div>
    </>
  );
}
