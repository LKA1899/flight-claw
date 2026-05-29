import { AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Card className="flex items-center justify-between gap-4 border-red-200 bg-red-50 p-5">
      <div className="flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-red-600" />
        <div>
          <div className="font-medium text-red-800">加载失败</div>
          <div className="text-sm text-red-700">{error instanceof Error ? error.message : "请求失败"}</div>
        </div>
      </div>
      {onRetry ? <Button variant="secondary" onClick={onRetry}>重试</Button> : null}
    </Card>
  );
}
