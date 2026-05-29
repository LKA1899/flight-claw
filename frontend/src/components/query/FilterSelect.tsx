import { AppSelect, type AppSelectOption } from "@/components/common/AppSelect";

type FilterSelectProps = {
  value?: string;
  onChange: (value: string) => void;
  options: AppSelectOption[];
  placeholder: string;
  className?: string;
};

export function FilterSelect({ value, onChange, options, placeholder, className }: FilterSelectProps) {
  return (
    <AppSelect
      value={value || "all"}
      onValueChange={(next) => onChange(next === "all" ? "" : next)}
      options={[{ value: "all", label: placeholder }, ...options]}
      placeholder={placeholder}
      className={className || "w-40 shrink-0"}
    />
  );
}
