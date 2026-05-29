import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function compactParams(params: Record<string, unknown>) {
  const output: Record<string, string> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      output[key] = String(value);
    }
  });
  return output;
}

export function progressPercent(success = 0, failed = 0, total = 0) {
  return total > 0 ? Math.round(((success + failed) / total) * 100) : 0;
}
