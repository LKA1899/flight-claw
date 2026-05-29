import json
import os
from urllib import request
from urllib.error import URLError

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    CHANNEL_NONE,
    CHANNEL_PUSHPLUS,
    CHANNEL_WEWORK,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
)
from app.db import SessionLocal
from app.models import FlightNotificationLog

load_dotenv()


def _post_json(url: str, payload: dict, timeout: int = 15) -> tuple[bool, str | None]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if 200 <= resp.status < 300:
                return True, body
            return False, f"HTTP {resp.status}: {body}"
    except URLError as exc:
        return False, str(exc)


def _send_pushplus(token: str, title: str, content: str) -> tuple[str, str, str | None]:
    ok, error = _post_json(
        "https://www.pushplus.plus/send",
        {"token": token, "title": title, "content": content, "template": "markdown"},
    )
    return CHANNEL_PUSHPLUS, STATUS_SUCCESS if ok else STATUS_FAILED, None if ok else error


def _send_wework(webhook_url: str, title: str, content: str) -> tuple[str, str, str | None]:
    ok, error = _post_json(
        webhook_url,
        {"msgtype": "markdown", "markdown": {"content": f"**{title}**\n\n{content}"}},
    )
    return CHANNEL_WEWORK, STATUS_SUCCESS if ok else STATUS_FAILED, None if ok else error


def write_notification_log(
    db: Session,
    title: str,
    content: str,
    channel: str,
    status: str,
    batch_no: str | None = None,
    error_message: str | None = None,
) -> FlightNotificationLog:
    row = FlightNotificationLog(
        batch_no=batch_no,
        channel=channel,
        title=title,
        content=content,
        status=status,
        error_message=error_message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def send_notification(title: str, content: str) -> dict:
    pushplus_token = os.getenv("PUSHPLUS_TOKEN", "").strip()
    wework_webhook_url = os.getenv("WEWORK_WEBHOOK_URL", "").strip()
    results = []

    if pushplus_token:
        channel, status, error = _send_pushplus(pushplus_token, title, content)
        results.append({"channel": channel, "status": status, "error_message": error})
    if wework_webhook_url:
        channel, status, error = _send_wework(wework_webhook_url, title, content)
        results.append({"channel": channel, "status": status, "error_message": error})

    if not results:
        print(f"[FlightClaw][Notify] skipped: {title}\n{content}", flush=True)
        return {"channel": CHANNEL_NONE, "status": STATUS_SKIPPED, "error_message": None}

    if any(item["status"] == STATUS_SUCCESS for item in results):
        return {"channel": ",".join(item["channel"] for item in results), "status": STATUS_SUCCESS, "results": results}

    return {
        "channel": ",".join(item["channel"] for item in results),
        "status": STATUS_FAILED,
        "error_message": "; ".join(str(item.get("error_message")) for item in results if item.get("error_message")),
        "results": results,
    }


def send_and_log_notification(
    title: str,
    content: str,
    batch_no: str | None = None,
) -> FlightNotificationLog:
    result = send_notification(title, content)
    with SessionLocal() as db:
        return write_notification_log(
            db,
            title=title,
            content=content,
            channel=result.get("channel") or CHANNEL_NONE,
            status=result.get("status") or STATUS_SKIPPED,
            batch_no=batch_no,
            error_message=result.get("error_message"),
        )


def list_notification_logs(db: Session, batch_no: str | None = None) -> list[FlightNotificationLog]:
    stmt = select(FlightNotificationLog).order_by(FlightNotificationLog.id.desc())
    if batch_no:
        stmt = stmt.where(FlightNotificationLog.batch_no == batch_no)
    return list(db.scalars(stmt))
