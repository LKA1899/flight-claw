import { useMemo, useState } from "react";
import { Check, ChevronsUpDown, Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { monitorApi } from "@/api/monitorApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type MonitorFilterSelectProps = {
  value?: string;
  onChange: (value: string) => void;
  className?: string;
};

export function MonitorFilterSelect({ value, onChange, className }: MonitorFilterSelectProps) {
  const [open, setOpen] = useState(false);
  const [keyword, setKeyword] = useState("");
  const query = useQuery({
    queryKey: ["monitor-filter-options"],
    queryFn: () => monitorApi.list({ page: 1, page_size: 100 }),
  });

  const monitors = query.data?.items || [];
  const selected = monitors.find((monitor) => String(monitor.id) === value);
  const selectedLabel = selected
    ? selected.monitor_name || `${selected.from_city} -> ${selected.to_city}`
    : "全部路线";
  const normalizedKeyword = keyword.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!normalizedKeyword) return monitors;
    return monitors.filter((monitor) => {
      const haystack = [
        monitor.monitor_name,
        monitor.from_city,
        monitor.to_city,
        monitor.from_airports,
        monitor.to_airports,
        `${monitor.from_city}${monitor.to_city}`,
        `${monitor.from_city}->${monitor.to_city}`,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedKeyword);
    });
  }, [monitors, normalizedKeyword]);

  function selectMonitor(next: string) {
    onChange(next === "all" ? "" : next);
    setOpen(false);
    setKeyword("");
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="secondary"
          className={cn("h-10 w-60 shrink-0 justify-between rounded-xl px-3 font-normal", className)}
          disabled={query.isLoading}
        >
          <span className="truncate">{query.isLoading ? "加载路线..." : selectedLabel}</span>
          <ChevronsUpDown className="h-4 w-4 text-stone-400" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-2" align="start">
        <div className="relative mb-2">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
          <Input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索路线"
            className="h-9 pl-9"
          />
        </div>
        <div className="max-h-72 overflow-y-auto">
          <button
            type="button"
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-muted"
            onClick={() => selectMonitor("all")}
          >
            <span>全部路线</span>
            {!value ? <Check className="h-4 w-4 text-coral" /> : null}
          </button>
          {filtered.map((monitor) => {
            const monitorValue = String(monitor.id);
            const label = monitor.monitor_name || `${monitor.from_city} -> ${monitor.to_city}`;
            return (
              <button
                type="button"
                key={monitor.id}
                className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-muted"
                onClick={() => selectMonitor(monitorValue)}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-ink">{label}</span>
                  <span className="block truncate text-xs text-stone-500">{monitor.from_city} {"->"} {monitor.to_city}</span>
                </span>
                {value === monitorValue ? <Check className="h-4 w-4 shrink-0 text-coral" /> : null}
              </button>
            );
          })}
          {!filtered.length ? <div className="px-3 py-6 text-center text-sm text-stone-500">没有匹配路线</div> : null}
        </div>
      </PopoverContent>
    </Popover>
  );
}
