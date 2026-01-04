import json
from typing import Any

from src.sessions_index import SESSIONS_DIR


def extract_text(message_data: dict[str, Any]) -> str:
    """Extract plain text from a stored agent message."""

    content = message_data.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)

    return ""


def history_events_from_session(*, session_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Build frontend-compatible events from stored session messages.

    Notes:
        - Reads from the same SQLite db used by the WebUI session.
        - Converts stored agent_messages rows into frontend-compatible WS events.
        - Includes user/assistant chat, tool calls, and agent handoffs.
    """

    limit = max(1, min(int(limit), 2000))

    import sqlite3

    conn = sqlite3.connect(str(SESSIONS_DIR / f"{session_id}.db"), timeout=0.2)
    try:
        rows = conn.execute(
            "SELECT id, message_data FROM agent_messages WHERE session_id=? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    finally:
        conn.close()

    events: list[dict[str, Any]] = []
    last_tool_name: str | None = None

    for _id, message_data in rows:
        try:
            data = json.loads(message_data)
        except Exception:
            continue

        role = data.get("role")
        if role in ("user", "assistant"):
            text = extract_text(data)
            if not text:
                continue
            events.append({"type": "assistant_message" if role == "assistant" else "user_message", "text": text})
            continue

        msg_type = data.get("type")
        if msg_type == "function_call":
            last_tool_name = str(data.get("name") or "tool")
            events.append({"type": "tool_call", "name": last_tool_name, "phase": "start"})
            continue

        if msg_type == "function_call_output":
            events.append({"type": "tool_call", "name": last_tool_name or "tool", "phase": "end"})
            last_tool_name = None
            continue

        # Agent SDK currently emits handoffs via logger.emit; keep this for future compatibility.
        if msg_type == "agent_handoff":
            to_agent = data.get("to_agent")
            if isinstance(to_agent, str) and to_agent:
                events.append({"type": "agent_handoff", "to_agent": to_agent})
            continue

    return events


async def push_session_history(ws: Any, *, session_id: str, limit: int = 200) -> None:
    """Push session history to a connected WebSocket client."""

    for ev in history_events_from_session(session_id=session_id, limit=limit):
        await ws.send_text(json.dumps(ev, ensure_ascii=False))


def get_recent_messages(*, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent chat messages from a session store."""

    limit = max(1, min(int(limit), 200))

    import sqlite3

    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path), timeout=0.2)
    try:
        rows = conn.execute(
            "SELECT id, message_data FROM agent_messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    finally:
        conn.close()

    items: list[dict[str, Any]] = []
    for _id, message_data in reversed(rows):
        try:
            data = json.loads(message_data)
        except Exception:
            continue

        role = data.get("role")
        if role not in ("user", "assistant"):
            continue

        items.append(
            {
                "id": str(data.get("id") or _id),
                "role": role,
                "text": extract_text(data),
            }
        )

    return items
