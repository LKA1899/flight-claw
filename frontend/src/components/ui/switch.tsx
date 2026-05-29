import * as React from "react";
import { cn } from "@/lib/utils";

export function Switch({ checked, onCheckedChange, className }: { checked?: boolean; onCheckedChange?: (checked: boolean) => void; className?: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onCheckedChange?.(!checked)} className={cn("relative h-6 w-11 rounded-full transition", checked ? "bg-coral" : "bg-stone-300", className)}>
      <span className={cn("absolute top-1 h-4 w-4 rounded-full bg-white transition", checked ? "left-6" : "left-1")} />
    </button>
  );
}
