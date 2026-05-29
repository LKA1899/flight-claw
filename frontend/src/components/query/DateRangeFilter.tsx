import { DateRangeField } from "@/components/common/DateRangeField";

export function DateRangeFilter({ start, end, onStartChange, onEndChange }: { start?: string; end?: string; onStartChange: (value: string) => void; onEndChange: (value: string) => void }) {
  return <DateRangeField compact start={start || ""} end={end || ""} onStartChange={onStartChange} onEndChange={onEndChange} />;
}
