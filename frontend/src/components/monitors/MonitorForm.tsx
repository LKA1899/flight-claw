import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AppSelect } from "@/components/common/AppSelect";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { Monitor, MonitorPayload } from "@/types/monitor";

const initial: MonitorPayload = {
  monitor_name: "",
  from_city: "",
  from_airports: "",
  to_city: "",
  to_airports: "",
  platform: "CTRIP",
  trip_type: "ONE_WAY",
  allow_direct: true,
  allow_transfer: false,
  allow_train_positioning: false,
  allow_hidden_city: false,
  max_transfer_count: undefined,
  max_total_hours: undefined,
  max_price: undefined,
  roundtrip_data_level: "OUTBOUND_ONLY",
  roundtrip_expand_return: false,
  roundtrip_outbound_expand_mode: "NONE",
  roundtrip_expand_top_n: 3,
  roundtrip_expand_ranks: "",
  roundtrip_return_fetch_limit: 10,
  roundtrip_return_sort_strategy: "LOW_PRICE",
  roundtrip_save_all_outbounds: true,
  roundtrip_expand_only_priced: true,
  roundtrip_skip_expand_over_budget: false,
  continue_on_expand_failed: true,
  save_step_snapshot: true,
  enabled: true,
  remark: "",
};

export function MonitorForm({
  value,
  onSubmit,
  submitting,
  formId,
  hideActions,
}: {
  value?: Monitor;
  onSubmit: (payload: MonitorPayload) => void;
  submitting?: boolean;
  formId?: string;
  hideActions?: boolean;
}) {
  const [form, setForm] = useState<MonitorPayload>(value ? { ...initial, ...value } : initial);
  const set = (key: keyof MonitorPayload, next: string | boolean | number | undefined) => setForm((current) => ({ ...current, [key]: next }));
  const collectionMode = form.roundtrip_expand_return ? "DEEP" : "LIGHT";
  const collectionHelp = form.roundtrip_expand_return
    ? "深度扫描：会按策略点开部分去程，采集返程列表和完整组合价格，可用于生成完整往返推荐。"
    : "轻量扫描：只采集去程列表和页面展示的往返起价，不采集返程航班明细，不能生成完整购票推荐。";

  const submit = () => {
    const payload: MonitorPayload = {
      ...form,
      roundtrip_expand_return: form.trip_type === "ROUND_TRIP" ? form.roundtrip_expand_return : false,
      roundtrip_data_level: form.trip_type === "ROUND_TRIP" && form.roundtrip_expand_return ? "FULL_COMBINATION" : "OUTBOUND_ONLY",
      roundtrip_outbound_expand_mode: form.trip_type === "ROUND_TRIP" && form.roundtrip_expand_return ? form.roundtrip_outbound_expand_mode : "NONE",
    };
    onSubmit(payload);
  };

  return (
    <form id={formId} className="space-y-5" onSubmit={(event) => { event.preventDefault(); submit(); }}>
      <Card>
        <CardHeader><CardTitle>路线信息</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="名称"><Input value={form.monitor_name} onChange={(event) => set("monitor_name", event.target.value)} required /></Field>
          <Field label="平台"><AppSelect value={form.platform} onValueChange={(value) => set("platform", value)} options={[{ value: "CTRIP", label: "CTRIP" }]} placeholder="选择平台" /></Field>
          <Field label="行程类型">
            <AppSelect value={form.trip_type} onValueChange={(value) => set("trip_type", value)} options={[{ value: "ONE_WAY", label: "单程" }, { value: "ROUND_TRIP", label: "往返" }]} placeholder="选择行程类型" />
          </Field>
          <Field label="出发城市"><Input value={form.from_city} onChange={(event) => set("from_city", event.target.value)} required /></Field>
          <Field label="到达城市"><Input value={form.to_city} onChange={(event) => set("to_city", event.target.value)} required /></Field>
          <Field label="出发机场"><Input value={form.from_airports || ""} onChange={(event) => set("from_airports", event.target.value)} placeholder="PEK,PKX" /></Field>
          <Field label="到达机场"><Input value={form.to_airports || ""} onChange={(event) => set("to_airports", event.target.value)} placeholder="TBS" /></Field>
        </CardContent>
      </Card>

      {form.trip_type === "ROUND_TRIP" ? (
        <Card>
          <CardHeader><CardTitle>往返采集方式</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label="采集方式">
              <AppSelect
                value={collectionMode}
                onValueChange={(value) => {
                  const deep = value === "DEEP";
                  set("roundtrip_expand_return", deep);
                  set("roundtrip_data_level", deep ? "FULL_COMBINATION" : "OUTBOUND_ONLY");
                  set("roundtrip_outbound_expand_mode", deep ? "LOWEST_TOP_N" : "NONE");
                }}
                options={[
                  { value: "LIGHT", label: "轻量扫描", description: "只采集去程列表和往返起价" },
                  { value: "DEEP", label: "深度扫描", description: "展开返程并生成完整组合价格" },
                ]}
                placeholder="选择采集方式"
              />
            </Field>
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              {collectionHelp}
            </div>
            {form.roundtrip_expand_return ? (
              <>
                <Field label="展开去程方式">
                  <AppSelect
                    value={form.roundtrip_outbound_expand_mode}
                    onValueChange={(value) => set("roundtrip_outbound_expand_mode", value)}
                    options={[
                      { value: "LOWEST_TOP_N", label: "最低价前 N 个" },
                      { value: "SPECIFIC_RANKS", label: "指定排名" },
                      { value: "ALL", label: "全部，不推荐" },
                    ]}
                    placeholder="选择展开方式"
                  />
                </Field>
                <Field label="最低价前 N 个"><Input type="number" min={1} max={20} value={form.roundtrip_expand_top_n} onChange={(event) => set("roundtrip_expand_top_n", Number(event.target.value))} /></Field>
                <Field label="指定排名"><Input value={form.roundtrip_expand_ranks || ""} onChange={(event) => set("roundtrip_expand_ranks", event.target.value)} placeholder="1,2,5" /></Field>
                <Field label="每个去程采集返程数量"><Input type="number" min={1} max={50} value={form.roundtrip_return_fetch_limit} onChange={(event) => set("roundtrip_return_fetch_limit", Number(event.target.value))} /></Field>
                <Toggle label="保存步骤快照" checked={form.save_step_snapshot} onChange={(v) => set("save_step_snapshot", v)} />
                <Toggle label="展开失败后继续" checked={form.continue_on_expand_failed} onChange={(v) => set("continue_on_expand_failed", v)} />
              </>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader><CardTitle>查询策略</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Toggle label="直飞" checked={form.allow_direct} onChange={(v) => set("allow_direct", v)} />
          <Toggle label="中转" checked={form.allow_transfer} onChange={(v) => set("allow_transfer", v)} />
          <Toggle label="火车/高铁接驳" checked={form.allow_train_positioning} onChange={(v) => set("allow_train_positioning", v)} />
          <Toggle label="甩尾方案" checked={form.allow_hidden_city} onChange={(v) => set("allow_hidden_city", v)} />
          {form.trip_type === "ROUND_TRIP" ? (
            <Alert className="md:col-span-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>往返第一版范围</AlertTitle>
              <AlertDescription>往返任务会先按基础直达路线生成；中转和接驳策略暂不混入往返任务。</AlertDescription>
            </Alert>
          ) : null}
          {form.allow_hidden_city ? (
            <Alert className="md:col-span-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>高风险提醒</AlertTitle>
              <AlertDescription>甩尾方案可能存在无托运行李、航线变更和航司规则风险，仅作为个人决策参考。</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>预算与限制</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <Field label="最高价格"><Input type="number" value={form.max_price || ""} onChange={(event) => set("max_price", event.target.value ? Number(event.target.value) : undefined)} /></Field>
          <Field label="最大总时长"><Input type="number" value={form.max_total_hours || ""} onChange={(event) => set("max_total_hours", event.target.value ? Number(event.target.value) : undefined)} /></Field>
          <Field label="最大中转次数"><Input type="number" value={form.max_transfer_count ?? ""} onChange={(event) => set("max_transfer_count", event.target.value ? Number(event.target.value) : undefined)} /></Field>
          <div className="md:col-span-3"><Field label="备注"><Textarea value={form.remark || ""} onChange={(event) => set("remark", event.target.value)} /></Field></div>
          <Toggle label="启用路线" checked={form.enabled} onChange={(v) => set("enabled", v)} />
        </CardContent>
      </Card>

      {!hideActions ? (
        <div className="sticky bottom-4 flex justify-end gap-2 rounded-2xl border border-border bg-white/90 p-3 shadow-soft backdrop-blur">
          <Button type="button" variant="secondary" onClick={() => history.back()}>取消</Button>
          <Button type="submit" disabled={submitting}>{submitting ? "保存中..." : "保存"}</Button>
        </div>
      ) : null}
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="space-y-2"><Label>{label}</Label>{children}</label>;
}

function Toggle({ label, checked, onChange }: { label: string; checked?: boolean; onChange: (checked: boolean) => void }) {
  return <div className="flex items-center justify-between rounded-xl border border-border bg-white p-3"><span className="text-sm font-medium text-ink">{label}</span><Switch checked={checked} onCheckedChange={onChange} /></div>;
}
