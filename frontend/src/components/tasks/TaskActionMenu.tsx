import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import type { QueryTask } from "@/types/task";

export function TaskActionMenu({ task, onRun, onParse, onReset }: { task: QueryTask; onRun: () => void; onParse: () => void; onReset: () => void }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="secondary" size="sm"><MoreHorizontal className="h-4 w-4" />操作</Button></DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {["PENDING", "FAILED"].includes(task.status) ? <DropdownMenuItem onSelect={onRun}>Run</DropdownMenuItem> : null}
        <DropdownMenuItem onSelect={onParse}>Parse Price</DropdownMenuItem>
        <DropdownMenuItem onSelect={onReset}>Reset</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
