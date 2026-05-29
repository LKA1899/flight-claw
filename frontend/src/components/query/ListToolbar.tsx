import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SearchInput } from "@/components/query/SearchInput";

export function ListToolbar({ keyword, onKeywordChange, onReset, onRefresh, filters, action }: { keyword?: string; onKeywordChange?: (value: string) => void; onReset: () => void; onRefresh?: () => void; filters?: ReactNode; action?: ReactNode }) {
  return (
    <Card className="mb-5 flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        {onKeywordChange ? <SearchInput value={keyword} onChange={onKeywordChange} placeholder="搜索关键词" /> : null}
        {filters}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" onClick={onReset}>重置</Button>
        {onRefresh ? <Button variant="secondary" onClick={onRefresh}><RotateCcw className="h-4 w-4" />刷新</Button> : null}
        {action}
      </div>
    </Card>
  );
}
