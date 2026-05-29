import { useState } from "react";
import { CalendarRange, X } from "lucide-react";
import { CalendarGrid, formatDateDisplay, parseDateValue } from "@/components/common/CalendarGrid";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type DateRangeFieldProps = {
  label?: string;
  start: string;
  end: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  className?: string;
  compact?: boolean;
  placeholder?: string;
  allowClear?: boolean;
};

export function DateRangeField({ label, start, end, onStartChange, onEndChange, className, compact, placeholder = "选择日期范围", allowClear = true }: DateRangeFieldProps) {
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState(parseDateValue(start) || new Date());
  const hasValue = Boolean(start || end);

  const clear = () => {
    onStartChange("");
    onEndChange("");
  };

  const selectDate = (value: string) => {
    if (!start || (start && end)) {
      onStartChange(value);
      onEndChange("");
      setMonth(parseDateValue(value) || new Date());
      return;
    }
    if (value < start) {
      onStartChange(value);
      onEndChange("");
      setMonth(parseDateValue(value) || new Date());
      return;
    }
    onEndChange(value);
    setOpen(false);
  };

  const displayText = !start ? placeholder : start && !end ? `${formatDateDisplay(start)} - 选择结束日期` : `${formatDateDisplay(start)} - ${formatDateDisplay(end)}`;

  return (
    <div className={cn("space-y-2", className)}>
      {label ? <Label className="text-sm font-medium text-neutral-700">{label}</Label> : null}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className={cn(
              "flex w-full items-center gap-3 border border-neutral-200 bg-white text-left shadow-sm transition hover:border-neutral-300 focus:border-coral/60 focus:outline-none focus:ring-2 focus:ring-coral/15",
              compact ? "h-11 min-w-0 rounded-xl px-3" : "h-12 rounded-2xl px-4",
            )}
          >
            <CalendarRange className={cn("shrink-0 text-stone-400", compact ? "h-4 w-4" : "h-5 w-5")} />
            <span className={cn("min-w-0 flex-1 truncate text-sm", !start ? "text-stone-400" : "text-ink font-medium")}>{displayText}</span>
            {hasValue && allowClear ? (
              <span
                role="button"
                tabIndex={-1}
                className="rounded-full p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-600"
                onClick={(event) => {
                  event.stopPropagation();
                  clear();
                }}
              >
                <X className="h-4 w-4" />
              </span>
            ) : null}
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-auto p-3">
          <div className="mb-3 rounded-xl bg-[#fbf8f4] px-3 py-2 text-xs text-stone-500">
            {!start || end ? "请选择开始日期。" : "请选择结束日期。"}
          </div>
          <CalendarGrid month={month} onMonthChange={setMonth} selectedStart={start} selectedEnd={end} onSelect={selectDate} />
        </PopoverContent>
      </Popover>
    </div>
  );
}
