import base64
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from app.constants import ARTIFACT_XHR
from app.db import DATA_DIR, SessionLocal
from app.services.artifact_service import create_task_artifact


class XhrCapture:
    def __init__(
        self,
        *,
        task_id: int,
        stage: str,
        enabled: bool,
        pattern: str,
        artifact_meta: dict[str, Any] | None = None,
        max_body_bytes: int = 2_000_000,
    ):
        self.task_id = task_id
        self.stage = stage
        self.enabled = enabled and bool(pattern)
        self.pattern = re.compile(pattern, re.IGNORECASE) if pattern else None
        self.artifact_meta = artifact_meta or {}
        self.max_body_bytes = max_body_bytes
        self.path = DATA_DIR / "xhr" / f"task_{task_id}_{stage}.jsonl"
        self.count = 0
        self._lock = threading.Lock()
        self._recorded = False

    def attach(self, page) -> None:
        if not self.enabled:
            return
        page.on("response", self._handle_response)

    def finalize(self) -> str | None:
        if not self.enabled or self.count <= 0 or self._recorded:
            return str(self.path) if self.count > 0 else None
        with SessionLocal() as db:
            create_task_artifact(
                db,
                task_id=self.task_id,
                stage=self.stage,
                artifact_type=ARTIFACT_XHR,
                path=str(self.path),
                label=self.stage,
                meta={
                    "captured_count": self.count,
                    "pattern": self.pattern.pattern if self.pattern else "",
                    **self.artifact_meta,
                },
            )
        self._recorded = True
        return str(self.path)

    def _handle_response(self, response) -> None:
        try:
            request = response.request
            if request.resource_type not in {"xhr", "fetch"}:
                return
            if not self.pattern or not self.pattern.search(response.url):
                return
            body = response.body()
            if len(body) > self.max_body_bytes:
                body = body[: self.max_body_bytes]
                truncated = True
            else:
                truncated = False
            content_type = response.headers.get("content-type", "")
            item = {
                "captured_at": datetime.now().isoformat(timespec="seconds"),
                "url": response.url,
                "status": response.status,
                "method": request.method,
                "resource_type": request.resource_type,
                "content_type": content_type,
                "truncated": truncated,
                "body": _body_payload(body, content_type),
            }
            self._append(item)
        except (PlaywrightError, OSError, ValueError):
            return

    def _append(self, item: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(item, ensure_ascii=False, sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
            self.count += 1


def _body_payload(body: bytes, content_type: str) -> dict[str, Any]:
    if _looks_textual(content_type):
        return {"encoding": "text", "value": body.decode("utf-8", errors="replace")}
    return {"encoding": "base64", "value": base64.b64encode(body).decode("ascii")}


def _looks_textual(content_type: str) -> bool:
    lowered = (content_type or "").lower()
    return any(marker in lowered for marker in ("json", "text", "javascript", "xml"))
