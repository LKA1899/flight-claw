import { ExternalLink } from "lucide-react";
import { taskApi } from "@/api/taskApi";
import { getToken } from "@/api/authApi";

export function SnapshotLinks({
  taskId,
  screenshot,
}: {
  taskId: number;
  screenshot?: boolean | string | null;
}) {
  const token = getToken();

  return (
    <div className="flex flex-nowrap items-center gap-2 text-xs">
      {screenshot ? (
        <a
          className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-coral hover:underline"
          href={`${taskApi.screenshotUrl(taskId)}?token=${token}`}
          target="_blank"
          rel="noreferrer"
        >
          截图 <ExternalLink className="h-3 w-3" />
        </a>
      ) : (
        <span className="text-stone-400">-</span>
      )}
    </div>
  );
}
