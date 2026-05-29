interface OutboundFlightInfoProps {
  detailJson?: string | null;
}

export function OutboundFlightInfo({ detailJson }: OutboundFlightInfoProps) {
  if (!detailJson) return null;
  let detail: Record<string, unknown> = {};
  try { detail = JSON.parse(detailJson); } catch { return null; }

  const flightParts = [
    detail.airline,
    detail.flight_no,
    detail.depart_time && detail.arrive_time ? `${detail.depart_time}-${detail.arrive_time}` : null,
  ].filter(Boolean).join(' ');

  const completeness = detail.data_completeness as string | undefined;
  const isPartial = completeness === 'OUTBOUND_WITH_STARTING_PRICE' || completeness === 'OUTBOUND_ONLY';

  return (
    <div className="mt-2 rounded-lg bg-blue-50/60 p-2.5 text-xs">
      <div className="font-medium text-blue-800">
        去程: {flightParts || '未知'}
      </div>
      {detail.depart_airport ? (
        <div className="mt-0.5 text-blue-700">
          {String(detail.depart_airport)} &rarr; {String(detail.arrive_airport || '')}
        </div>
      ) : null}
      {isPartial ? (
        <div className="mt-1 text-amber-600">* 返程未展开，价格为往返起价</div>
      ) : null}
      {detail.return_detail_status === 'NOT_EXPANDED' ? (
        <div className="mt-0.5 text-stone-400">返程状态: 未展开</div>
      ) : null}
    </div>
  );
}
