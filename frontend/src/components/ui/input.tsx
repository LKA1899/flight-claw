import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn("h-10 w-full rounded-xl border border-border bg-white px-3 text-sm outline-none transition placeholder:text-stone-400 focus:border-coral focus:ring-2 focus:ring-coral/15", className)} {...props} />
));
Input.displayName = "Input";
