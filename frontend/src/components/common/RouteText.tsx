export function RouteText({ from, to, tripType }: { from?: string | null; to?: string | null; tripType?: string | null }) {
  const arrow = tripType === "ROUND_TRIP" ? " ⇄ " : " → ";
  return <span className="font-medium text-ink">{from || "—"}{arrow}{to || "—"}</span>;
}
