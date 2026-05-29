import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const WEEK_LABELS = ["一", "二", "三", "四", "五", "六", "日"];

export function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseDateValue(value?: string) {
  if (!value) return undefined;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return undefined;
  return new Date(year, month - 1, day);
}

export function formatDateDisplay(value?: string) {
  if (!value) return "";
  const date = parseDateValue(value);
  if (!date) return value;
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
}

export function addMonths(date: Date, amount: number) {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1);
}

function monthTitle(date: Date) {
  return `${date.getFullYear()}年${String(date.getMonth() + 1).padStart(2, "0")}月`;
}

function startOfCalendar(month: Date) {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const mondayOffset = (first.getDay() + 6) % 7;
  const start = new Date(first);
  start.setDate(first.getDate() - mondayOffset);
  return start;
}

type CalendarGridProps = {
  month: Date;
  onMonthChange: (date: Date) => void;
  selectedStart?: string;
  selectedEnd?: string;
  onSelect: (value: string) => void;
};

export function CalendarGrid({ month, onMonthChange, selectedStart, selectedEnd, onSelect }: CalendarGridProps) {
  const today = toDateInputValue(new Date());
  const startValue = selectedStart || "";
  const endValue = selectedEnd || "";
  const gridStart = startOfCalendar(month);
  const days = Array.from({ length: 42 }, (_, index) => {
    const date = new Date(gridStart);
    date.setDate(gridStart.getDate() + index);
    return date;
  });

  return (
    <div className="w-[320px] rounded-2xl bg-white">
      <div className="mb-4 flex items-center justify-between">
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={() => onMonthChange(addMonths(month, -1))}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="text-sm font-semibold text-ink">{monthTitle(month)}</div>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={() => onMonthChange(addMonths(month, 1))}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="mb-2 grid grid-cols-7 text-center text-xs font-medium text-stone-400">
        {WEEK_LABELS.map((label) => <div key={label}>{label}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((date) => {
          const value = toDateInputValue(date);
          const outside = date.getMonth() !== month.getMonth();
          const selected = value === startValue || value === endValue;
          const inRange = startValue && endValue && value > startValue && value < endValue;
          return (
            <button
              key={value}
              type="button"
              onClick={() => onSelect(value)}
              className={cn(
                "h-9 rounded-xl text-sm transition",
                outside ? "text-stone-300" : "text-ink",
                value === today && !selected ? "border border-coral/40 text-coral" : "",
                inRange ? "bg-coral/10 text-coral" : "",
                selected ? "bg-coral text-white shadow-sm" : "hover:bg-[#fbf8f4]",
              )}
            >
              {date.getDate()}
            </button>
          );
        })}
      </div>
    </div>
  );
}
