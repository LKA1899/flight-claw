from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FlightReport


def list_reports(db: Session) -> list[FlightReport]:
    return list(db.scalars(select(FlightReport).order_by(FlightReport.id.desc())))


def get_report(db: Session, report_id: int) -> FlightReport:
    report = db.get(FlightReport, report_id)
    if not report:
        raise ValueError("Report not found")
    return report
