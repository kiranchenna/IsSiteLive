import asyncio
import logging
import secrets
from typing import Optional

from app.recorder.session import RecordingSession

logger = logging.getLogger("issitelive.recorder")

_sessions: dict[str, RecordingSession] = {}
_sweeper_task: Optional[asyncio.Task] = None
SWEEP_INTERVAL_SECONDS = 60


async def create_session(username: str, password: str, start_url: str) -> RecordingSession:
    session_id = secrets.token_urlsafe(16)
    session = RecordingSession(session_id, username=username, password=password)
    try:
        await session.start()
        _sessions[session_id] = session
        await session.navigate(start_url)
    except Exception:
        # start()/navigate() can fail after the browser process is already launched
        # (e.g. the target site times out) -- without this, that browser is orphaned
        # forever since nothing else references it.
        _sessions.pop(session_id, None)
        await session.stop()
        raise
    return session


def get_session(session_id: str) -> Optional[RecordingSession]:
    return _sessions.get(session_id)


async def remove_session(session_id: str) -> None:
    session = _sessions.pop(session_id, None)
    if session:
        await session.stop()


async def _sweep_loop() -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        idle_ids = [sid for sid, s in _sessions.items() if s.is_idle()]
        for sid in idle_ids:
            logger.info("Closing idle recording session %s", sid)
            await remove_session(sid)


def start_sweeper() -> None:
    global _sweeper_task
    _sweeper_task = asyncio.create_task(_sweep_loop())


def stop_sweeper() -> None:
    if _sweeper_task:
        _sweeper_task.cancel()
