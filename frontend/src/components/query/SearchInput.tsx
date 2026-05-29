import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

export function SearchInput({ value, onChange, placeholder = "搜索" }: { value?: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <div className="relative w-64 shrink-0">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
      <Input value={value || ""} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="pl-9" />
    </div>
  );
}
