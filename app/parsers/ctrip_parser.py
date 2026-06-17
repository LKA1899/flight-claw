import re
from html.parser import HTMLParser

from app.parsers.base import FlightPriceItem

PRICE_RE = re.compile(r"(?:¥|￥|CNY\s*)\s*(\d{2,6})(?:\.\d+)?|(\d{2,6})\s*(?:元|块)")
FLIGHT_ROW_PRICE_RE = re.compile(r"(?:¥|￥|CNY\s*)\s*(\d{2,6})(?:\.\d+)?\s*(?:起)?[\u4e00-\u9fa5A-Za-z0-9\.\s]{0,80}?(?:含税价|订票|往返总价|选为去程)")
FLIGHT_NO_RE = re.compile(r"\b((?=[A-Z0-9]{2}\d{2,4}\b)[A-Z0-9]*[A-Z][A-Z0-9]*\d{2,4})\b")
TIME_RE = re.compile(r"\b([01]\d|2[0-3]):([0-5]\d)\b")
AIRLINE_RE = re.compile(r"([A-Z][A-Za-z ]{2,32}(?:Air|Airlines)|[\u4e00-\u9fa5]{2,12}(?:航空|航司|快线|国航))")
AIRPORT_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9]{2,30}机场(?:\s*T\d)?)")
TRANSFER_RE = re.compile(r"转\s*(?:机)?\s*([\u4e00-\u9fa5A-Za-z]+)\s*\d+\s*h")
TRANSFER_COUNT_RE = re.compile(r"转\s*(\d+)\s*次|中转\s*(\d+)\s*次")
TRANSFER_HINT_RE = re.compile(r"(?:中转|转机)\s*\d+\s*(?:小时|h)|转\s*[\u4e00-\u9fa5A-Za-z]+\s*\d+\s*h")
DURATION_RE = re.compile(r"(?:(\d+)\s*天)?\s*(?:(\d+)\s*(?:小时|h))?\s*(?:(\d+)\s*(?:分|分钟|m|min))?")
RESULT_START_MARKERS = [
    "仅支持携程APP扫码",
    "低价提醒",
    "更多排序",
    "耗时短优先",
]
RESULT_END_MARKERS = [
    "在线客服",
    "机票价格受季节性需求",
    "旅游资讯",
    "Copyright",
]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_to_visible_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    return parser.text()


def _price_value(match: re.Match) -> float | None:
    value = match.group(1) or match.group(2)
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _window(text: str, start: int, end: int, radius: int = 260) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def _duration_minutes(raw: str) -> int | None:
    raw = re.sub(r"\+\s*\d+\s*天", " ", raw)
    candidates: list[int] = []
    for match in DURATION_RE.finditer(raw):
        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)
        total = days * 1440 + hours * 60 + minutes
        if total:
            candidates.append(total)
    return max(candidates) if candidates else None


def _transfer_count(raw: str) -> int:
    match = TRANSFER_COUNT_RE.search(raw)
    if match:
        return int(match.group(1) or match.group(2) or 0)
    if TRANSFER_HINT_RE.search(raw):
        return 1
    return 0


def _first(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1) if match else None


def _times(text: str) -> tuple[str | None, str | None]:
    values = [match.group(0) for match in TIME_RE.finditer(text)]
    if len(values) >= 2:
        return values[0], values[1]
    if len(values) == 1:
        return values[0], None
    return None, None


def _airports(text: str) -> tuple[str | None, str | None]:
    values = [match.group(1) for match in AIRPORT_RE.finditer(text)]
    deduped = list(dict.fromkeys(values))
    if len(deduped) >= 2:
        return deduped[0], deduped[1]
    if len(deduped) == 1:
        return deduped[0], None
    return None, None


def _flight_numbers(text: str) -> list[str]:
    values = []
    for value in FLIGHT_NO_RE.findall(text):
        if value not in values:
            values.append(value)
    return values


def _transfer_city(text: str) -> str | None:
    match = TRANSFER_RE.search(text)
    return match.group(1) if match else None


def _result_text(text: str) -> str:
    start = 0
    for marker in RESULT_START_MARKERS:
        index = text.find(marker)
        if index != -1:
            start = max(start, index + len(marker))
    end = len(text)
    for marker in RESULT_END_MARKERS:
        index = text.find(marker, start)
        if index != -1:
            end = min(end, index)
    return text[start:end]


def _flight_rows(text: str) -> list[tuple[float, str]]:
    result_text = _result_text(text)
    matches = list(FLIGHT_ROW_PRICE_RE.finditer(result_text))
    rows: list[tuple[float, str]] = []
    previous_end = 0
    for match in matches:
        price = _price_value(match)
        if price is None:
            previous_end = match.end()
            continue
        raw = normalize_text(result_text[previous_end : match.end()])
        previous_end = match.end()
        if _looks_like_flight_row(raw):
            rows.append((price, raw))
    return rows


def _looks_like_flight_row(text: str) -> bool:
    if not _flight_numbers(text) and not _first(AIRLINE_RE, text):
        return False
    if "机场" not in text:
        return False
    if len([match.group(0) for match in TIME_RE.finditer(text)]) < 2:
        return False
    if any(marker in text for marker in ["更多日期", "出发日期", "乘客类型", "旅游资讯", "低价提醒 Hi"]):
        return False
    return True


def _cabin(text: str) -> str | None:
    for keyword in ["经济舱", "公务舱", "商务舱", "头等舱", "超级经济舱"]:
        if keyword in text:
            return keyword
    return None


def _baggage(text: str) -> str | None:
    if "无免费托运行李" in text:
        return "无免费托运行李"
    match = re.search(r"(\d+\s*KG|\d+\s*kg|托运行李[^，。；\s]{0,20})", text)
    return match.group(1) if match else None


def parse_ctrip_html(html: str) -> list[FlightPriceItem]:
    return parse_ctrip_text(html_to_visible_text(html))


def parse_ctrip_text(visible_text: str) -> list[FlightPriceItem]:
    try:
        if not visible_text:
            return []

        items: list[FlightPriceItem] = []
        seen: set[tuple[str | None, str | None, str | None, float]] = set()
        for price, raw in _flight_rows(visible_text):
            flight_numbers = _flight_numbers(raw)
            flight_no = "/".join(flight_numbers) if flight_numbers else None
            depart_time, arrive_time = _times(raw)
            depart_airport, arrive_airport = _airports(raw)
            key = (flight_no, depart_time, arrive_time, price)
            if key in seen:
                continue
            seen.add(key)
            transfer_count = _transfer_count(raw)
            items.append(
                FlightPriceItem(
                    airline=_first(AIRLINE_RE, raw),
                    flight_no=flight_no,
                    depart_time=depart_time,
                    arrive_time=arrive_time,
                    depart_airport=depart_airport,
                    arrive_airport=arrive_airport,
                    duration_minutes=_duration_minutes(raw),
                    transfer_count=transfer_count,
                    transfer_city=_transfer_city(raw) if transfer_count else None,
                    cabin_info=_cabin(raw),
                    baggage_info=_baggage(raw),
                    price=price,
                    currency="CNY",
                    raw_text=raw[:1200],
                    raw_json={
                        "parser": "ctrip_flight_row_regex_v3",
                        "has_flight_no": bool(flight_no),
                        "has_time": bool(depart_time),
                        "valid_flight_row": True,
                    },
                )
            )
        return items
    except Exception:
        return []
