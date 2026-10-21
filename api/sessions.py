"""Per-visitor state for the web API, kept in server memory only (never on disk).

Each browser gets a random, HttpOnly session cookie. A session holds what Streamlit kept in
st.session_state for one visitor: the Challenge round and the Ask AIDA conversation.
Idle sessions expire; the store is capped so it cannot grow without limit.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field

COOKIE = "aida_session"
IDLE_SECONDS = 2 * 60 * 60
MAX_SESSIONS = 5000


@dataclass
class Session:
    lock: threading.RLock = field(default_factory=threading.RLock)
    round: dict | None = None          # the Challenge round (see api.main)
    chat_history: list = field(default_factory=list)  # role/content pairs sent to the live model
    transcript: list = field(default_factory=list)    # what the chat panel shows
    seen: float = field(default_factory=time.monotonic)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, sid: str | None) -> tuple[str, Session]:
        """The visitor's session, or a new one (with a new id) if it is missing or expired."""
        now = time.monotonic()
        with self._lock:
            self._expire(now)
            session = self._sessions.get(sid) if sid else None
            if session is None:
                sid = secrets.token_urlsafe(24)
                session = self._sessions[sid] = Session()
                if len(self._sessions) > MAX_SESSIONS:  # drop the least recently seen
                    oldest = min(self._sessions, key=lambda key: self._sessions[key].seen)
                    del self._sessions[oldest]
            session.seen = now
            return sid, session

    def _expire(self, now: float) -> None:
        for key in [key for key, session in self._sessions.items() if now - session.seen > IDLE_SECONDS]:
            del self._sessions[key]

    def __len__(self) -> int:
        return len(self._sessions)
