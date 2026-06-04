import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const styles: Record<string, string> = {
  SUCCESS: "border-green-200 bg-green-50 text-green-700",
  FAILED: "border-red-200 bg-red-50 text-red-700",
  RUNNING: "border-blue-200 bg-blue-50 text-blue-700",
  QUEUED: "border-sky-200 bg-sky-50 text-sky-700",
  CANCEL_REQUESTED: "border-amber-200 bg-amber-50 text-amber-700",
  CANCELLED: "border-stone-200 bg-stone-50 text-stone-600",
  PENDING: "border-stone-200 bg-stone-100 text-stone-700",
  PARTIAL_SUCCESS: "border-green-200 bg-green-50 text-green-700",
  SKIPPED: "border-stone-200 bg-stone-50 text-stone-500",
  ENABLED: "border-green-200 bg-green-50 text-green-700",
  DISABLED: "border-stone-200 bg-stone-100 text-stone-600",
};

export function StatusBadge({ status, className, children }: { status?: string | boolean | null; className?: string; children?: React.ReactNode }) {
  const value = typeof status === "boolean" ? (status ? "ENABLED" : "DISABLED") : status || "PENDING";
  return <Badge className={cn(styles[value] || styles.PENDING, className)}>{children || value}</Badge>;
}
