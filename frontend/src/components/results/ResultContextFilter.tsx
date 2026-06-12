import { AppSelect } from "@/components/common/AppSelect";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { Monitor } from "@/types/monitor";
import type { ScanOption } from "@/types/scan";

type ResultContextFilterProps = {
  monitors: Monitor[];
  scans: ScanOption[];
  monitorId?: string;
  scanId?: string;
  departDate?: string;
  loadingScans?: boolean;
  onMonitorChange: (value: string) => void;
  onScanChange: (value: string) => void;
  onDepartDateChange?: (value: string) => void;
  onRefresh?: () => void;
};

export function ResultContextFilter({
  monitors,
  scans,
  monitorId,
  scanId,
  departDate,
  loadingScans,
  onMonitorChange,
  onScanChange,
  onDepartDateChange,
  onRefresh,
}: ResultContextFilterProps) {
  const monitorOptions = monitors.map((monitor) => ({
    value: String(monitor.id),
    label: monitor.monitor_name || `${monitor.from_city} -> ${monitor.to_city}`,
    description: `${monitor.from_city} -> ${monitor.to_city}`,
  }));
  const scanOptions = scans.map((scan) => ({
    value: String(scan.scan_id),
    label: scan.label,
    description: scan.route_label,
  }));

  return (
    <Card className="mb-5 flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <AppSelect
          value={monitorId}
          onValueChange={onMonitorChange}
          options={monitorOptions}
          placeholder="选择扫描路线"
          className="w-72 shrink-0"
        />
        <AppSelect
          value={scanId}
          onValueChange={onScanChange}
          options={scanOptions}
          placeholder={loadingScans ? "加载扫描记录..." : "选择扫描记录"}
          disabled={!monitorId || loadingScans || !scanOptions.length}
          className="w-80 shrink-0"
        />
        {onDepartDateChange ? (
          <Input
            type="date"
            value={departDate || ""}
            onChange={(event) => onDepartDateChange(event.target.value)}
            className="w-40 shrink-0"
          />
        ) : null}
      </div>
      {onRefresh ? (
        <Button variant="secondary" onClick={onRefresh}>
          刷新
        </Button>
      ) : null}
    </Card>
  );
}
