"""Credential parsing and persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Optional
from urllib.parse import parse_qs

from .config import USER_AGENT


class CredentialError(Exception):
    """Raised when login credentials are missing or malformed."""


def get_header(headers: Optional[Mapping[str, str]], key: str) -> Optional[str]:
    """Return a header value using case-insensitive lookup."""
    if not headers:
        return None
    wanted = key.lower()
    for name, value in headers.items():
        if str(name).lower() == wanted:
            return str(value)
    return None


@dataclass(frozen=True)
class Credentials:
    """Values required to call the elective APIs after a successful login."""

    cookie: str
    token: str
    student_code: str
    elective_batch_code: str
    user_agent: str = USER_AGENT

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "cookie": self.cookie,
            "token": self.token,
        }

    @classmethod
    def from_capture(cls, captured: Mapping[str, object]) -> "Credentials":
        headers = captured.get("request_headers")
        if not isinstance(headers, Mapping):
            headers = {}

        cookie = get_header(headers, "cookie")
        token = get_header(headers, "token")
        missing = [name for name, value in (("cookie", cookie), ("token", token)) if not value]
        if missing:
            available = ", ".join(map(str, headers.keys())) or "(none)"
            raise CredentialError(
                f"Missing required header(s): {', '.join(missing)}. Available: {available}"
            )

        payload = captured.get("request_payload", "") or ""
        params = parse_qs(str(payload))
        student_code = params.get("xh", [None])[0]
        elective_batch_code = params.get("xklcdm", [None])[0]
        if not student_code or not elective_batch_code:
            raise CredentialError("Could not parse xh or xklcdm from captured request payload.")

        user_agent = get_header(headers, "user-agent") or USER_AGENT
        return cls(
            cookie=str(cookie),
            token=str(token),
            student_code=str(student_code),
            elective_batch_code=str(elective_batch_code),
            user_agent=str(user_agent),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Credentials":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        try:
            return cls(**data)
        except TypeError as exc:
            raise CredentialError(f"Invalid credentials file: {path}") from exc

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
