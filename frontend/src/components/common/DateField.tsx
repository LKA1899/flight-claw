import { useState } from "react";
import { CalendarDays, X } from "lucide-react";
import { CalendarGrid, formatDateDisplay, parseDateValue } from "@/components/common/CalendarGrid";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type DateFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
  required?: boolean;
  placeholder?: string;
};

export function DateField({ label, value, onChange, className, required, placeholder = "选择日期" }: DateFieldProps) {
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState(parseDateValue(value) || new Date());

  const selectDate = (next: string) => {
    onChange(next);
    setMonth(parseDateValue(next) || new Date());
    setOpen(false);
  };

  return (
    <div className={cn("space-y-2", className)}>
      <Label className="text-sm font-medium text-neutral-700">{label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-required={required}
            className={cn(
              "flex h-11 w-full items-center gap-3 rounded-xl border border-neutral-200 bg-white px-3 text-left text-sm shadow-sm transition hover:border-neutral-300 focus:border-coral/60 focus:outline-none focus:ring-2 focus:ring-coral/15",
              !value && "text-stone-400",
            )}
          >
            <CalendarDays className="h-4 w-4 shrink-0 text-stone-400" />
            <span className="min-w-0 flex-1 truncate">{value ? formatDateDisplay(value) : placeholder}</span>
            {value ? (
              <span
                role="button"
                tabIndex={-1}
                className="rounded-full p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-600"
                onClick={(event) => {
                  event.stopPropagation();
                  onChange("");
                }}
              >
                <X className="h-3.5 w-3.5" />
              </span>
            ) : null}
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-auto p-3">
          <CalendarGrid month={month} onMonthChange={setMonth} selectedStart={value} onSelect={selectDate} />
        </PopoverContent>
      </Popover>
    </div>
  );
}
