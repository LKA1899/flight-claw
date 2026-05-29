import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type AppSelectOption = {
  label: string;
  value: string;
  description?: string;
};

type AppSelectProps = {
  value?: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  options: AppSelectOption[];
  disabled?: boolean;
  className?: string;
};

export function AppSelect({ value, onValueChange, placeholder, options, disabled, className }: AppSelectProps) {
  const selectedOption = options.find((option) => option.value === value);

  return (
    <Select value={value || undefined} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger className={cn(className)}>
        <SelectValue placeholder={placeholder}>
          {selectedOption ? <span className="truncate">{selectedOption.label}</span> : null}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value} textValue={option.label}>
            <div className="space-y-0.5">
              <div>{option.label}</div>
              {option.description ? <div className="text-xs leading-4 text-stone-500">{option.description}</div> : null}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
