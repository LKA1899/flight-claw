import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { reportApi } from "@/api/reportApi";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ListToolbar } from "@/components/query/ListToolbar";
import { DataPagination } from "@/components/query/DataPagination";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatDateTime } from "@/lib/format";
import { usePagedParams } from "@/lib/queryParams";

export function ReportListPage() {
  const qp = usePagedParams(20);
  const query = useQuery({ queryKey: ["reports", qp.params], queryFn: () => reportApi.list(qp.params) });

  return (
    <>
      <PageHeader title="旅行报告" description="每次扫描后的 Markdown 分析报告和通知入口。" />
      <ListToolbar
        keyword={String(qp.params.keyword || "")}
        onKeywordChange={(value) => qp.setValue("keyword", value)}
        onReset={qp.reset}
        onRefresh={() => query.refetch()}
        filters={<Input placeholder="batch_no" value={String(qp.params.batch_no || "")} onChange={(event) => qp.setValue("batch_no", event.target.value)} className="w-40 shrink-0" />}
      />
      {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState error={query.error} /> : query.data!.items.length ? (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {query.data!.items.map((report) => (
              <Card key={report.id} className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-ink">{report.title}</div>
                    <div className="mt-2 text-sm text-stone-500">Batch {report.batch_no || "-"} · Scan #{report.scan_id || "-"}</div>
                    <div className="mt-1 text-xs text-stone-400">{formatDateTime(report.create_time)}</div>
                  </div>
                  <Button asChild variant="secondary"><Link to={`/reports/${report.id}`}>查看</Link></Button>
                </div>
              </Card>
            ))}
          </div>
          <DataPagination page={qp.page} pageSize={qp.pageSize} total={query.data!.total} onPageChange={qp.setPage} onPageSizeChange={qp.setPageSize} />
        </>
      ) : <EmptyState title="暂无旅行报告" />}
    </>
  );
}
