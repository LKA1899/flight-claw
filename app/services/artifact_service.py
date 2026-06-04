import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FlightTaskArtifact


def create_task_artifact(
    db: Session,
    *,
    task_id: int,
    stage: str,
    artifact_type: str,
    path: str | Path,
    label: str | None = None,
    meta: dict[str, Any] | None = None,
) -> FlightTaskArtifact:
    row = FlightTaskArtifact(
        task_id=task_id,
        stage=stage,
        artifact_type=artifact_type,
        path=str(path),
        label=label,
        meta_json=json.dumps(meta or {}, ensure_ascii=False, sort_keys=True),
        create_time=datetime.now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_task_artifact_path(
    db: Session,
    *,
    task_id: int,
    artifact_type: str,
    stage: str | None = None,
) -> str | None:
    stmt = select(FlightTaskArtifact).where(
        FlightTaskArtifact.task_id == task_id,
        FlightTaskArtifact.artifact_type == artifact_type,
    )
    if stage:
        stmt = stmt.where(FlightTaskArtifact.stage == stage)
    row = db.scalar(stmt.order_by(FlightTaskArtifact.id.desc()))
    return row.path if row else None
