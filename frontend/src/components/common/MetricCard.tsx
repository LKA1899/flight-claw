import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

export function MetricCard({ title, value, hint, icon }: { title: string; value: ReactNode; hint?: string; icon?: ReactNode }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div className="text-sm text-stone-500">{title}</div>
        <div className="text-stone-400">{icon}</div>
      </div>
      <div className="mt-4 text-3xl font-semibold text-ink">{value}</div>
      {hint ? <div className="mt-2 text-xs text-stone-500">{hint}</div> : null}
    </Card>
  );
}
