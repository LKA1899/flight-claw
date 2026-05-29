import { Inbox } from "lucide-react";
import { Card } from "@/components/ui/card";

export function EmptyState({ title = "暂无数据", description = "当前筛选条件下没有记录。" }: { title?: string; description?: string }) {
  return (
    <Card className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
      <Inbox className="mb-3 h-9 w-9 text-stone-300" />
      <div className="font-medium text-ink">{title}</div>
      <p className="mt-1 text-sm text-stone-500">{description}</p>
    </Card>
  );
}
