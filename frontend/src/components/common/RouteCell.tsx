export function RouteCell({ from, to, fromAirports, toAirports }: { from?: string | null; to?: string | null; fromAirports?: string | null; toAirports?: string | null }) {
  return (
    <div>
      <div className="font-medium text-ink">{from || "—"} → {to || "—"}</div>
      <div className="mt-0.5 text-xs text-stone-500">{fromAirports || "Any"} → {toAirports || "Any"}</div>
    </div>
  );
}
