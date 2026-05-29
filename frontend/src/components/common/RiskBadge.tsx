import { Badge } from "@/components/ui/badge";

const labels: Record<string, string> = { LOW: "低风险", MEDIUM: "中风险", HIGH: "高风险" };
const styles: Record<string, string> = {
  LOW: "border-green-200 bg-green-50 text-green-700",
  MEDIUM: "border-orange-200 bg-orange-50 text-orange-700",
  HIGH: "border-red-200 bg-red-50 text-red-700",
};

export function RiskBadge({ risk }: { risk?: string | null }) {
  const value = risk || "LOW";
  return <Badge className={styles[value] || styles.LOW}>{labels[value] || value}</Badge>;
}
