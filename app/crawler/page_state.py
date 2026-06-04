from dataclasses import dataclass
from enum import StrEnum

from app.constants import (
    PAGE_CONTEXT_MISMATCH,
    PAGE_DATE_DRIFT,
    PAGE_LOAD_TIMEOUT,
    PAGE_LOGIN_REQUIRED,
    PAGE_PARSE_ZERO_RESULT,
    PAGE_PROFILE_LOCKED,
    PAGE_STRUCTURE_CHANGED,
    PAGE_UNKNOWN,
    PAGE_VERIFICATION_REQUIRED,
)


class PageState(StrEnum):
    RESULT = "RESULT"
    LOGIN_REQUIRED = PAGE_LOGIN_REQUIRED
    VERIFICATION_REQUIRED = PAGE_VERIFICATION_REQUIRED
    CONTEXT_MISMATCH = PAGE_CONTEXT_MISMATCH
    DATE_DRIFT = PAGE_DATE_DRIFT
    LOAD_TIMEOUT = PAGE_LOAD_TIMEOUT
    PARSE_ZERO_RESULT = PAGE_PARSE_ZERO_RESULT
    PROFILE_LOCKED = PAGE_PROFILE_LOCKED
    STRUCTURE_CHANGED = PAGE_STRUCTURE_CHANGED
    UNKNOWN = PAGE_UNKNOWN


@dataclass
class PageStateFailure(Exception):
    state: PageState
    message: str
    url: str | None = None
    title: str | None = None

    def __str__(self) -> str:
        parts = [self.state.value, self.message]
        if self.url:
            parts.append(f"url={self.url}")
        if self.title:
            parts.append(f"title={self.title}")
        return ": ".join(parts[:2]) + (", " + ", ".join(parts[2:]) if len(parts) > 2 else "")
