import { Badge } from "@/components/ui/badge";

export function StrategyTags({ direct, transfer, train, hidden }: { direct?: boolean; transfer?: boolean; train?: boolean; hidden?: boolean }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {direct ? <Badge className="border-blue-200 bg-blue-50 text-blue-700">直飞</Badge> : null}
      {transfer ? <Badge className="border-violet-200 bg-violet-50 text-violet-700">中转</Badge> : null}
      {train ? <Badge className="border-teal-200 bg-teal-50 text-teal-700">接驳</Badge> : null}
      {hidden ? <Badge className="border-red-200 bg-red-50 text-red-700">甩尾 高风险</Badge> : null}
    </div>
  );
}
