from dataclasses import asdict, dataclass


@dataclass
class FlightPriceItem:
    airline: str | None = None
    flight_no: str | None = None
    depart_time: str | None = None
    arrive_time: str | None = None
    depart_airport: str | None = None
    arrive_airport: str | None = None
    duration_minutes: int | None = None
    transfer_count: int | None = None
    transfer_city: str | None = None
    cabin_info: str | None = None
    baggage_info: str | None = None
    price: float | None = None
    currency: str = "CNY"
    raw_text: str | None = None
    raw_json: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)
