import { StatusBadge } from "@/components/common/StatusBadge";

export function TaskStatusPill({ status }: { status?: string | null }) {
  return <StatusBadge status={status} />;
}
