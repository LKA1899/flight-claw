import { AppSelect } from "@/components/common/AppSelect";

export function PageSizeSelect({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  return (
    <AppSelect
      value={String(value)}
      onValueChange={(next) => onChange(Number(next))}
      options={[10, 20, 50, 100].map((item) => ({ value: String(item), label: `${item} / 页` }))}
      className="w-28"
    />
  );
}
