import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { reportApi } from "@/api/reportApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { MarkdownView } from "@/components/common/MarkdownView";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDateTime } from "@/lib/format";

export function ReportDetailPage() {
  const { id = "" } = useParams();
  const query = useQuery({ queryKey: ["report", id], queryFn: () => reportApi.get(id) });
  if (query.isLoading) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} />;
  const report = query.data!;

  return (
    <>
      <PageHeader
        title={report.title}
        description={`生成时间 ${formatDateTime(report.create_time)}`}
        actions={
          <>
            {report.scan_id ? <Button asChild variant="secondary"><Link to={`/scans/${report.scan_id}`}>查看扫描</Link></Button> : null}
            <Button asChild variant="secondary"><Link to={`/tasks?batch_no=${report.batch_no}`}>查看任务</Link></Button>
            <Button disabled>发送通知</Button>
          </>
        }
      />
      <div className="grid gap-5 xl:grid-cols-[.45fr_1fr]">
        <Card>
          <CardContent className="space-y-3 p-5 text-sm">
            <div>Batch: {report.batch_no || "-"}</div>
            <div>Scan: {report.scan_id || "-"}</div>
            <div>Monitor: {report.monitor_id || "-"}</div>
            <div>LLM: {report.llm_enabled ? "enabled" : "disabled"}</div>
            {report.llm_error_message ? <div className="rounded-xl bg-amber-50 p-3 text-amber-800">{report.llm_error_message}</div> : null}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-8"><MarkdownView content={report.llm_content_md || report.content_md} /></CardContent>
        </Card>
      </div>
    </>
  );
}
