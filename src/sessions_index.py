import json
import time
from pathlib import Path
from typing import Any


SESSIONS_DIR = Path("data/sessions")
SESSIONS_INDEX_PATH = SESSIONS_DIR / "index.json"


def rebuild_sessions_index() -> dict[str, Any]:
    """Rebuild sessions index from existing db files.

    Notes:
        - Treat `data/sessions/*.db` as the source of truth.
        - Sort sessions by session_id desc (newest first).
        - Preserve active_session_id when possible.
    """

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    prev_active: str | None = None
    try:
        raw = SESSIONS_INDEX_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            active = data.get("active_session_id")
            if isinstance(active, str) and active.isdigit():
                prev_active = active
    except Exception:
        prev_active = None

    session_ids: list[str] = []
    for p in SESSIONS_DIR.glob("*.db"):
        sid = p.stem
        if sid.isdigit():
            session_ids.append(sid)

    session_ids.sort(reverse=True)

    active_session_id: str | None = None
    if prev_active is not None and prev_active in session_ids:
        active_session_id = prev_active
    elif session_ids:
        active_session_id = session_ids[0]

    index: dict[str, Any] = {
        "sessions": [{"session_id": sid} for sid in session_ids],
        "active_session_id": active_session_id,
    }

    tmp_path = SESSIONS_INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(SESSIONS_INDEX_PATH)
    return index


def load_sessions_index() -> dict[str, Any]:
    """Load sessions index, rebuilding it if missing or invalid."""

    try:
        raw = SESSIONS_INDEX_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("index_not_dict")
        if not isinstance(data.get("sessions"), list):
            raise ValueError("sessions_not_list")
        return data
    except Exception:
        return rebuild_sessions_index()


def set_active_session_id(session_id: str) -> dict[str, Any]:
    """Persist active session id.

    Returns:
        The updated index.
    """

    if not session_id.isdigit():
        raise ValueError("invalid_session_id")

    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        raise FileNotFoundError("session_db_missing")

    index = rebuild_sessions_index()
    index["active_session_id"] = session_id
    tmp_path = SESSIONS_INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(SESSIONS_INDEX_PATH)
    return index


def create_session() -> dict[str, Any]:
    """Create a new session.

    Requirements:
        - session_id is Unix epoch milliseconds.
        - If called twice within the same millisecond, create only one session.
    """

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    session_id = str(int(time.time() * 1000))
    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        # Touch the file so it appears in the index immediately.
        # SQLiteSession will create tables lazily on first use.
        db_path.write_bytes(b"")

    index = rebuild_sessions_index()
    index["active_session_id"] = session_id
    tmp_path = SESSIONS_INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(SESSIONS_INDEX_PATH)

    return {"session_id": session_id, "db_path": str(db_path)}


def ensure_session_db(session_id: str | None) -> str:
    """Ensure a valid session db exists and return session_id."""

    if isinstance(session_id, str) and session_id.isdigit():
        db_path = SESSIONS_DIR / f"{session_id}.db"
        if db_path.exists():
            return session_id

    active = load_sessions_index().get("active_session_id")
    if isinstance(active, str) and active.isdigit():
        db_path = SESSIONS_DIR / f"{active}.db"
        if db_path.exists():
            return active

    session_id = str(int(time.time() * 1000))
    (SESSIONS_DIR / f"{session_id}.db").write_bytes(b"")
    rebuild_sessions_index()
    return session_id
