from __future__ import annotations

from typing import Any

from src.sessions_index import SESSIONS_DIR, list_session_ids, rebuild_sessions_index, set_active_session_id


def archive_session_store(*, session_id: str) -> dict[str, Any]:
    """Archive a session.

    This function is intentionally a placeholder.

    Intended behavior (TODO):
        - Summarize the session content.
        - Persist summary as a text file.
        - Delete the session db.

    Current behavior:
        - Delete `data/sessions/{session_id}.db`.
        - Rebuild sessions index.
        - If the deleted session was active, switch active to the newest remaining session.

    Returns:
        Dict with ok flag and updated active_session_id.
    """

    if not session_id.isdigit():
        return {"ok": False, "error": "invalid_session_id"}

    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        return {"ok": False, "error": "session_db_missing"}

    # TODO: summarize + write text file.
    db_path.unlink()

    index = rebuild_sessions_index()

    # Ensure active_session_id is not pointing to a deleted session.
    if index.get("active_session_id") == session_id:
        remaining = list_session_ids()
        if remaining:
            index = set_active_session_id(remaining[0])
        else:
            index["active_session_id"] = None

    return {
        "ok": True,
        "archived_session_id": session_id,
        "active_session_id": index.get("active_session_id"),
    }
