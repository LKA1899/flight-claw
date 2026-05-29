import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { settingsApi, type SettingsData } from "@/api/settingsApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });
  const updateMutation = useMutation({
    mutationFn: (payload: { headless: boolean }) => settingsApi.update(payload),
    onSuccess: () => {
      toast.success("设置已保存");
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  if (query.isLoading) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} />;
  const data = query.data!;

  return (
    <>
      <PageHeader title="设置" description="浏览器模式、通知和 LLM 配置。" />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Browser</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-xl bg-[#fbf8f4] p-3">
              <div>
                <div className="font-medium text-ink">无头模式</div>
                <div className="text-xs text-stone-500">{data.browser.headless ? "后台静默运行" : "显示浏览器窗口"}</div>
              </div>
              <Switch
                checked={Boolean(data.browser.headless)}
                onCheckedChange={(checked) => updateMutation.mutate({ headless: checked })}
              />
            </div>
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">Profile</span>
              <span className="ml-3 font-medium text-ink">{String(data.browser.profile_path)}</span>
            </div>
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">Query Interval</span>
              <span className="ml-3 font-medium text-ink">{String(data.browser.query_interval)}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Storage</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(data.storage).map(([key, value]) => (
              <div key={key} className="rounded-xl bg-[#fbf8f4] p-3 text-sm"><span className="text-stone-500">{key}</span><span className="ml-3 font-medium text-ink break-all">{String(value)}</span></div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Notification</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">PushPlus</span>
              <span className="ml-3 font-medium">{data.notification.pushplus_configured ? "已配置" : "未配置"}</span>
            </div>
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">企业微信</span>
              <span className="ml-3 font-medium">{data.notification.wecom_configured ? "已配置" : "未配置"}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>LLM</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">状态</span>
              <span className="ml-3 font-medium">{data.llm.configured ? "已配置" : "未配置"}</span>
            </div>
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">Base URL</span>
              <span className="ml-3 font-medium text-ink">{String(data.llm.base_url)}</span>
            </div>
            <div className="rounded-xl bg-[#fbf8f4] p-3 text-sm">
              <span className="text-stone-500">Model</span>
              <span className="ml-3 font-medium text-ink">{String(data.llm.model)}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Safety Policy</CardTitle></CardHeader>
          <CardContent className="grid gap-2 md:grid-cols-2">
            {data.safety_policy.map((item: string) => (
              <div key={item} className="rounded-2xl bg-[#fbf8f4] p-3 text-sm text-stone-700">{item}</div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
