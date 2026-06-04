from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.constants import ARTIFACT_TEXT, ARTIFACT_XHR, PLATFORM_CTRIP
from app.models import FlightQueryTask
from app.parsers.ctrip_parser import FlightPriceItem, html_to_visible_text, parse_ctrip_text
from app.services.artifact_service import latest_task_artifact_path


@dataclass
class ParsePipelineResult:
    items: list[FlightPriceItem]
    source_type: str
    source_path: str | None
    warnings: list[str]


def parse_ctrip_task_items(db: Session, task: FlightQueryTask) -> ParsePipelineResult:
    if task.platform != PLATFORM_CTRIP:
        raise ValueError(f"Unsupported platform: {task.platform}")

    warnings: list[str] = []
    xhr_path = latest_task_artifact_path(db, task_id=task.id, artifact_type=ARTIFACT_XHR)
    if xhr_path:
        warnings.append("XHR artifact captured; JSON parser is not enabled yet, using visible text fallback")

    text_path = task.text_path or latest_task_artifact_path(db, task_id=task.id, artifact_type=ARTIFACT_TEXT)
    visible_text = _load_visible_text(text_path, task.html_path)
    return ParsePipelineResult(
        items=parse_ctrip_text(visible_text),
        source_type="visible_text",
        source_path=text_path or task.html_path,
        warnings=warnings,
    )


def load_text_snapshot(text_path: str) -> str:
    path = Path(text_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        return html_to_visible_text(text)
    return text


def _load_visible_text(text_path: str | None, html_path: str | None) -> str:
    if text_path:
        path = Path(text_path)
        if not path.exists():
            raise FileNotFoundError(f"Text snapshot file not found: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            raise ValueError("Text snapshot file is empty")
        return text

    if not html_path:
        raise ValueError("Text snapshot path is empty")
    path = Path(html_path)
    if not path.exists():
        raise FileNotFoundError(f"HTML file not found: {path}")
    html = path.read_text(encoding="utf-8", errors="replace")
    if not html.strip():
        raise ValueError("HTML file is empty")
    return html_to_visible_text(html)
