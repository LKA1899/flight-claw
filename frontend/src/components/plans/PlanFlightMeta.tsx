interface PlanFlightMetaProps {
  label: string;
  airline?: string | null;
  flightNo?: string | null;
  departTime?: string | null;
  arriveTime?: string | null;
  departAirport?: string | null;
  arriveAirport?: string | null;
}

export function PlanFlightMeta({
  label,
  airline,
  flightNo,
  departTime,
  arriveTime,
  departAirport,
  arriveAirport,
}: PlanFlightMetaProps) {
  const flightText = [airline, flightNo].filter(Boolean).join(" ");
  const timeText = [departTime, arriveTime].filter(Boolean).join(" -> ");
  const airportText = [departAirport, arriveAirport].filter(Boolean).join(" -> ");

  if (!flightText && !timeText && !airportText) return null;

  return (
    <div className="rounded-xl border border-border bg-[#fbf8f4] p-3">
      <div className="text-xs text-stone-400">{label}</div>
      {flightText ? <div className="mt-1 text-sm font-medium text-ink">{flightText}</div> : null}
      {timeText ? <div className="mt-1 text-sm text-stone-700">起飞/到达 {timeText}</div> : null}
      {airportText ? <div className="mt-1 text-xs text-stone-500">{airportText}</div> : null}
    </div>
  );
}
