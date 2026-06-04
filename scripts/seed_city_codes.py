"""Seed and sync flight city codes for flight-scan.

Run from project root or inside the backend container:
    python scripts/seed_city_codes.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, create_all  # noqa: E402
from app.services.city_code_service import seed_default_city_codes, sync_ourairports_city_codes  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed flight city codes into SQLite")
    parser.add_argument("--skip-ourairports", action="store_true", help="Only write built-in curated city mappings")
    parser.add_argument("--limit", type=int, default=None, help="Limit OurAirports processed rows for testing")
    args = parser.parse_args()

    create_all()
    with SessionLocal() as db:
        inserted = seed_default_city_codes(db)
        print(f"[city-codes] curated seed inserted={inserted}")
        if not args.skip_ourairports:
            result = sync_ourairports_city_codes(db, limit=args.limit)
            print(f"[city-codes] ourairports sync={result}")


if __name__ == "__main__":
    main()
