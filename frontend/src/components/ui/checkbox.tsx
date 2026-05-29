import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function Checkbox({ checked, onCheckedChange, className }: { checked?: boolean; onCheckedChange?: (checked: boolean) => void; className?: string }) {
  return (
    <button type="button" onClick={() => onCheckedChange?.(!checked)} className={cn("flex h-5 w-5 items-center justify-center rounded-md border border-border bg-white", checked && "border-coral bg-coral text-white", className)}>
      {checked ? <Check className="h-3.5 w-3.5" /> : null}
    </button>
  );
}
