from __future__ import annotations

import re
import csv
import io
from urllib.request import urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import PLATFORM_CTRIP
from app.db import SessionLocal
from app.models import FlightCityCode


DEFAULT_CTRIP_CITY_CODES: list[dict[str, str]] = [
    {"city_name": "北京", "city_code": "bjs", "aliases": "北京市,BJS,PEK,PKX", "country": "中国"},
    {"city_name": "Beijing", "city_code": "bjs", "aliases": "北京,北京市,BJS,PEK,PKX", "country": "CN"},
    {"city_name": "上海", "city_code": "sha", "aliases": "上海市,SHA,PVG,Hongqiao,虹桥", "country": "中国"},
    {"city_name": "Shanghai", "city_code": "sha", "aliases": "上海,上海市,SHA,PVG,SHA", "country": "CN"},
    {"city_name": "广州", "city_code": "can", "aliases": "广州市,CAN", "country": "中国"},
    {"city_name": "Guangzhou", "city_code": "can", "aliases": "广州,广州市,CAN", "country": "CN"},
    {"city_name": "深圳", "city_code": "szx", "aliases": "深圳市,SZX", "country": "中国"},
    {"city_name": "Shenzhen", "city_code": "szx", "aliases": "深圳,深圳市,SZX", "country": "CN"},
    {"city_name": "成都", "city_code": "ctu", "aliases": "成都市,CTU,TFU", "country": "中国"},
    {"city_name": "Chengdu", "city_code": "ctu", "aliases": "成都,成都市,CTU,TFU", "country": "CN"},
    {"city_name": "昆明", "city_code": "kmg", "aliases": "昆明市,KMG", "country": "中国"},
    {"city_name": "Kunming", "city_code": "kmg", "aliases": "昆明,昆明市,KMG", "country": "CN"},
    {"city_name": "喀什", "city_code": "khg", "aliases": "喀什市,KHG", "country": "中国"},
    {"city_name": "Kashgar", "city_code": "khg", "aliases": "喀什,喀什市,KHG", "country": "CN"},
    {"city_name": "第比利斯", "city_code": "tbs", "aliases": "Tbilisi,TBS", "country": "格鲁吉亚"},
    {"city_name": "Tbilisi", "city_code": "tbs", "aliases": "第比利斯,TBS", "country": "GE"},
    {"city_name": "东京", "city_code": "tyo", "aliases": "Tokyo,TYO,NRT,HND", "country": "日本"},
    {"city_name": "Tokyo", "city_code": "tyo", "aliases": "东京,TYO,NRT,HND", "country": "JP"},
    {"city_name": "曼谷", "city_code": "bkk", "aliases": "Bangkok,BKK,DMK", "country": "泰国"},
    {"city_name": "Bangkok", "city_code": "bkk", "aliases": "曼谷,BKK,DMK", "country": "TH"},
]

OURAIRPORTS_AIRPORTS_CSV_URL = "https://ourairports.com/data/airports.csv"


def normalize_code(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    return re.sub(r"[^A-Za-z0-9]", "", value).lower()


def first_airport_code(airports: str | None) -> str | None:
    if not airports:
        return None
    for part in airports.split(","):
        code = normalize_code(part)
        if code:
            return code
    return None


def seed_default_city_codes(db: Session) -> int:
    inserted = 0
    for item in DEFAULT_CTRIP_CITY_CODES:
        existing = db.scalar(
            select(FlightCityCode).where(
                FlightCityCode.platform == PLATFORM_CTRIP,
                FlightCityCode.city_name == item["city_name"],
            )
        )
        if existing:
            if (existing.remark or "").startswith("synced from OurAirports") or (existing.remark or "") == "default seed":
                existing.city_code = item["city_code"].lower()
                existing.aliases = _merge_aliases(existing.aliases, item.get("aliases"), item["city_code"].upper())
                existing.country = item.get("country") or existing.country
                existing.remark = "default seed"
            continue
        db.add(
            FlightCityCode(
                platform=PLATFORM_CTRIP,
                city_name=item["city_name"],
                city_code=item["city_code"],
                aliases=item.get("aliases"),
                country=item.get("country"),
                enabled=True,
                remark="default seed",
            )
        )
        inserted += 1
    if inserted:
        db.commit()
    return inserted


def _merge_aliases(*values: str | None) -> str | None:
    merged: list[str] = []
    for value in values:
        for part in (value or "").split(","):
            text = part.strip()
            if text and text not in merged:
                merged.append(text)
    return ",".join(merged) if merged else None


def _upsert_city_code(
    db: Session,
    *,
    platform: str,
    city_name: str,
    city_code: str,
    aliases: str | None,
    country: str | None,
    remark: str,
) -> str:
    existing = db.scalar(
        select(FlightCityCode).where(
            FlightCityCode.platform == platform,
            FlightCityCode.city_name == city_name,
        )
    )
    if existing:
        existing.aliases = _merge_aliases(existing.aliases, aliases, city_code.upper())
        if not existing.country and country:
            existing.country = country
        if not existing.remark:
            existing.remark = remark
        return "updated"

    db.add(
        FlightCityCode(
            platform=platform,
            city_name=city_name,
            city_code=city_code.lower(),
            aliases=_merge_aliases(aliases, city_code.upper()),
            country=country,
            enabled=True,
            remark=remark,
        )
    )
    db.flush()
    return "inserted"


def sync_ourairports_city_codes(
    db: Session,
    url: str = OURAIRPORTS_AIRPORTS_CSV_URL,
    platform: str = PLATFORM_CTRIP,
    limit: int | None = None,
) -> dict[str, int | str]:
    with urlopen(url, timeout=60) as response:
        raw = response.read().decode("utf-8-sig", errors="replace")

    inserted = 0
    updated = 0
    skipped = 0
    processed = 0
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        if limit is not None and processed >= limit:
            break
        iata = normalize_code(row.get("iata_code"))
        municipality = (row.get("municipality") or "").strip()
        if not iata or len(iata) != 3 or not municipality:
            skipped += 1
            continue
        airport_type = (row.get("type") or "").strip()
        if airport_type in {"closed", "heliport", "seaplane_base", "balloonport"}:
            skipped += 1
            continue
        processed += 1
        country = (row.get("iso_country") or "").strip() or None
        airport_name = (row.get("name") or "").strip()
        aliases = _merge_aliases(airport_name, row.get("keywords"), iata.upper(), row.get("ident"))
        existing = db.scalar(
            select(FlightCityCode).where(
                FlightCityCode.platform == platform,
                FlightCityCode.city_name == municipality,
            )
        )
        city_name = municipality
        if existing and existing.country and country and existing.country != country and existing.city_code.lower() != iata:
            city_name = f"{municipality} ({country})"
            aliases = _merge_aliases(aliases, municipality)
        result = _upsert_city_code(
            db,
            platform=platform,
            city_name=city_name,
            city_code=iata,
            aliases=aliases,
            country=country,
            remark="synced from OurAirports airports.csv",
        )
        if result == "inserted":
            inserted += 1
        else:
            updated += 1

    db.commit()
    return {
        "source": url,
        "processed": processed,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


def _aliases(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def resolve_city_code(
    city: str,
    airports: str | None = None,
    platform: str = PLATFORM_CTRIP,
    db: Session | None = None,
) -> str:
    airport_code = first_airport_code(airports)
    if airport_code:
        return airport_code

    city_name = city.strip()
    if not city_name:
        raise ValueError("City name is empty")

    inline_code = normalize_code(city_name)
    if inline_code and inline_code == city_name.lower() and len(inline_code) <= 4:
        return inline_code

    owns_session = db is None
    session = db or SessionLocal()
    try:
        exact = session.scalar(
            select(FlightCityCode).where(
                FlightCityCode.platform == platform,
                FlightCityCode.enabled.is_(True),
                FlightCityCode.city_name == city_name,
            )
        )
        if exact:
            return exact.city_code.lower()

        rows = session.scalars(
            select(FlightCityCode).where(
                FlightCityCode.platform == platform,
                FlightCityCode.enabled.is_(True),
            )
        ).all()
        normalized_city = city_name.lower()
        for row in rows:
            aliases = _aliases(row.aliases)
            if city_name in aliases or normalized_city in {alias.lower() for alias in aliases}:
                return row.city_code.lower()
    finally:
        if owns_session:
            session.close()

    raise ValueError(f"No {platform} city code mapping for city: {city_name}. Add it to flight_city_code first.")
