import { useMemo, useState } from "react";
import { CalendarRange, Info, Sparkles } from "lucide-react";
import { DateRangeField } from "@/components/common/DateRangeField";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const WEEKDAYS = [
  { value: 1, label: "周一" },
  { value: 2, label: "周二" },
  { value: 3, label: "周三" },
  { value: 4, label: "周四" },
  { value: 5, label: "周五" },
  { value: 6, label: "周六" },
  { value: 7, label: "周日" },
];

const QUICK_RANGES = [
  { label: "未来 7 天", days: 7 },
  { label: "未来 30 天", days: 30 },
  { label: "未来 90 天", days: 90 },
];

type DateBatchFormProps = {
  roundTrip?: boolean;
  pending?: boolean;
  onGenerate: (payload: { start_date: string; end_date: string; return_start_date?: string; return_end_date?: string; weekdays: number[] }) => void;
};

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function daysBetween(start: string, end: string, weekdays: number[]): number {
  if (!start || !end) return 0;
  const s = new Date(start);
  const e = new Date(end);
  if (e < s) return 0;
  let count = 0;
  const cur = new Date(s);
  while (cur <= e) {
    if (weekdays.includes(cur.getDay() === 0 ? 7 : cur.getDay())) count++;
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}

export function DateBatchForm({ roundTrip, pending, onGenerate }: DateBatchFormProps) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [returnStart, setReturnStart] = useState("");
  const [returnEnd, setReturnEnd] = useState("");
  const [weekdays, setWeekdays] = useState([1, 2, 3, 4, 5, 6, 7]);
  const invalidRange = Boolean(start && end && end < start);
  const invalidReturnRange = Boolean(returnStart && returnEnd && returnEnd < returnStart);
  const disabled = !start || !end || invalidRange || !weekdays.length || (roundTrip && (!returnStart || !returnEnd || invalidReturnRange)) || pending;

  const applyQuickRange = (days: number) => {
    const today = new Date();
    const last = new Date(today);
    last.setDate(today.getDate() + days - 1);
    setStart(toDateInputValue(today));
    setEnd(toDateInputValue(last));
  };

  const departCount = useMemo(() => daysBetween(start, end, weekdays), [start, end, weekdays]);
  const returnCount = useMemo(() => daysBetween(returnStart, returnEnd, weekdays), [returnStart, returnEnd, weekdays]);
  const totalCount = roundTrip ? departCount * returnCount : departCount;
  const totalDays = useMemo(() => {
    if (!start || !end) return 0;
    const diff = Math.ceil((new Date(end).getTime() - new Date(start).getTime()) / 86400000) + 1;
    return diff;
  }, [start, end]);

  const estimateLabel = useMemo(() => {
    if (!weekdays.length) return { text: "请至少选择一个扫描星期", variant: "warn" as const };
    if (!start || !end) return { text: "请选择去程日期范围", variant: "hint" as const };
    if (roundTrip && (!returnStart || !returnEnd)) return { text: "请继续选择返程日期范围", variant: "hint" as const };
    if (totalDays > 180) return { text: `日期范围 ${totalDays} 天较大，建议分批生成`, variant: "warn" as const };
    if (roundTrip) return { text: `预计生成 ${departCount} × ${returnCount} = ${totalCount} 组往返日期`, variant: "ok" as const };
    return { text: `预计生成 ${departCount} 个日期`, variant: "ok" as const };
  }, [weekdays, start, end, roundTrip, returnStart, returnEnd, totalDays, departCount, returnCount, totalCount]);

  return (
    <div className="rounded-3xl border border-neutral-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-neutral-100 px-6 py-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-rose-50 text-rose-500">
            <CalendarRange className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-ink">生成扫描日期</h3>
            <p className="mt-0.5 text-sm text-stone-500">选择日期范围并按星期筛选，系统会生成符合条件的扫描日期。</p>
          </div>
        </div>
        <div className="flex gap-1.5">
          {QUICK_RANGES.map((item) => (
            <Button key={item.label} type="button" variant="outline" size="sm" className="h-8 rounded-full border-neutral-200 px-3 text-xs text-stone-600 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200" onClick={() => applyQuickRange(item.days)}>
              <Sparkles className="mr-1 h-3 w-3" />
              {item.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="space-y-4 px-6 py-5">
        {/* Date ranges */}
        <div className={cn("grid gap-4", roundTrip ? "lg:grid-cols-2" : "max-w-md")}>
          <DateRangeField label="去程日期范围" placeholder="选择去程日期范围" start={start} end={end} onStartChange={setStart} onEndChange={setEnd} />
          {roundTrip ? (
            <DateRangeField label="返程日期范围" placeholder="选择返程日期范围" start={returnStart} end={returnEnd} onStartChange={setReturnStart} onEndChange={setReturnEnd} />
          ) : null}
        </div>

        {invalidRange ? <p className="text-xs text-red-600">结束日期不能早于开始日期。</p> : null}
        {invalidReturnRange ? <p className="text-xs text-red-600">返程结束日期不能早于开始日期。</p> : null}

        {/* Weekday selector */}
        <div className="max-w-md rounded-2xl border border-neutral-200 bg-[#fbf8f4]/50 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-sm font-medium text-neutral-700">扫描星期</div>
              <div className="mt-0.5 text-xs text-stone-500">只会生成选中星期对应的日期</div>
            </div>
            <div className="flex gap-1">
              {[{ label: "工作日", days: [1, 2, 3, 4, 5] }, { label: "周末", days: [6, 7] }, { label: "全选", days: [1, 2, 3, 4, 5, 6, 7] }, { label: "清空", days: [] }].map((item) => (
                <Button key={item.label} type="button" variant="ghost" size="sm" className="h-7 rounded-full px-2.5 text-xs text-stone-500 hover:bg-white hover:text-ink" onClick={() => setWeekdays(item.days)}>
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map((day) => {
              const active = weekdays.includes(day.value);
              return (
                <button
                  key={day.value}
                  type="button"
                  onClick={() => setWeekdays((current) => (active ? current.filter((item) => item !== day.value) : [...current, day.value].sort()))}
                  className={cn(
                    "h-9 rounded-full border px-4 text-sm transition",
                    active ? "border-rose-200 bg-rose-50 text-rose-700" : "border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50",
                  )}
                >
                  {day.label}
                </button>
              );
            })}
          </div>
          {!weekdays.length ? <p className="mt-3 text-xs text-red-600">至少选择一个星期。</p> : null}
        </div>

        {/* Estimate + action */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className={cn("text-sm", estimateLabel.variant === "warn" && "text-amber-700", estimateLabel.variant === "hint" && "text-stone-500", estimateLabel.variant === "ok" && "text-emerald-700")}>
            {estimateLabel.text}
          </div>
          <Button type="button" disabled={disabled} onClick={() => onGenerate({ start_date: start, end_date: end, return_start_date: roundTrip ? returnStart : undefined, return_end_date: roundTrip ? returnEnd : undefined, weekdays })}>
            {pending ? "生成中..." : "生成扫描日期"}
          </Button>
        </div>
      </div>

      {/* Footer hint */}
      <div className="flex items-center gap-2 rounded-b-3xl bg-[#fbf8f4] px-6 py-3 text-xs text-stone-500">
        <Info className="h-3.5 w-3.5 shrink-0" />
        重复日期会自动跳过，生成后会出现在已维护日期列表中。
      </div>
    </div>
  );
}
