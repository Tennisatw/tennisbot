from __future__ import annotations

from typing import Any

from src.sessions_index import SESSIONS_DIR, list_session_ids, rebuild_sessions_index, set_active_session_id


def archive_session_store(*, session_id: str) -> dict[str, Any]:
    """Archive a session.

    Behavior:
        - Summarize the session content via a lightweight summarizer agent.
        - Persist summary as a markdown file under `data/session_summaries/`.
        - Delete the session db.
        - Rebuild sessions index.
        - If the deleted session was active, switch active to the newest remaining session.

    Notes:
        - On Windows, deleting an open SQLite file raises WinError 32.
          We close our own connections, then retry unlink a few times.

    Returns:
        Dict with ok flag and updated active_session_id.
    """

    if not session_id.isdigit():
        return {"ok": False, "error": "invalid_session_id"}

    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        return {"ok": False, "error": "session_db_missing"}

    from pathlib import Path
    import time

    from agents import Agent, Runner

    from src.session_history import get_recent_messages

    messages = get_recent_messages(session_id=session_id, limit=200)

    transcript_lines: list[str] = []
    for m in messages:
        role = m.get("role")
        text = (m.get("text") or "").strip()
        if role in ("user", "assistant") and text:
            transcript_lines.append(f"{role}: {text}")

    prompt = (
        "请用中文，用一句话总结以下聊天记录。:\n"
        "聊天记录:\n"
        + "\n".join(transcript_lines)
    )

    summarizer = Agent(
        name="SessionSummarizer",
        instructions="你写简洁、准确的会话总结。重点关注用户输入和结果",
        model="gpt-5-mini",
        tools=[],
    )

    result = Runner.run_sync(summarizer, prompt)
    summary_md = str(getattr(result, "final_output", "")).strip() or "(empty summary)"

    out_dir = Path("data/session_summaries")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{session_id}.md"
    out_path.write_text(summary_md, encoding="utf-8")

    # Best-effort: Windows may keep the sqlite file locked briefly.
    last_err: Exception | None = None
    for _ in range(20):
        try:
            db_path.unlink()
            last_err = None
            break
        except PermissionError as e:
            last_err = e
            time.sleep(0.1)

    if last_err is not None and db_path.exists():
        return {"ok": False, "error": "session_db_busy", "detail": repr(last_err)}

    index = rebuild_sessions_index()

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
        "summary_path": str(out_path),
    }

    """Archive a session.

    Behavior:
        - Summarize the session content via a lightweight summarizer agent.
        - Persist summary as a markdown file under `data/session_summaries/`.
        - Delete the session db.
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

    from datetime import datetime
    from pathlib import Path

    from agents import Agent, Runner

    from src.session_history import get_recent_messages

    messages = get_recent_messages(session_id=session_id, limit=200)

    transcript_lines: list[str] = []
    for m in messages:
        role = m.get("role")
        text = (m.get("text") or "").strip()
        if role in ("user", "assistant") and text:
            transcript_lines.append(f"{role}: {text}")

    prompt = (
        "请用中文，用一句话总结以下聊天记录。:\n"
        "聊天记录:\n"
        + "\n".join(transcript_lines)
    )

    summarizer = Agent(
        name="SessionSummarizer",
        instructions="你写简洁、准确的会话总结。重点关注用户输入和结果",
        model="gpt-5-mini",
        tools=[],
    )

    result = Runner.run_sync(summarizer, prompt)
    summary_md = str(getattr(result, "final_output", "")).strip() or "(empty summary)"

    out_dir = Path("data/session_summaries")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{session_id}.md"
    out_path.write_text(summary_md, encoding="utf-8")

    db_path.unlink()

    index = rebuild_sessions_index()

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
        "summary_path": str(out_path),
    }
