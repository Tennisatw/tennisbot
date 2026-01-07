from __future__ import annotations

from typing import Any
from pathlib import Path
import time
import asyncio

from agents import Agent, Runner

from src.session_history import get_recent_messages
from src.sessions_index import SESSIONS_DIR, list_session_ids, rebuild_sessions_index, set_active_session_id


async def summerize_session(messages: list[dict[str, Any]], session_id: str) -> None:

    transcript_lines: list[str] = []
    for m in messages:
        role = m.get("role")
        text = (m.get("text") or "").strip()
        if role in ("user", "assistant") and text:
            transcript_lines.append(f"{role}: {text}")

    prompt = (
        "请用中文，用一句话总结此会话。:\n"
        + "\n".join(transcript_lines)
    )

    summarizer = Agent(
        name="SessionSummarizer",
        instructions="用中文输出简洁、准确的会话总结。重点关注用户输入和结果。如没有聊天记录，输出空格。用户是Tennisatw，AI助理是Tennisbot",
        model="gpt-5-mini",
        tools=[],
    )

    result = Runner.run_sync(summarizer, prompt)
    summary_md = str(getattr(result, "final_output", "")).strip() or "(empty summary)"

    out_dir = Path("data/session_summaries")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{session_id}.md"
    out_path.write_text(summary_md, encoding="utf-8")


def archive_session_store(*, session_id: str) -> dict[str, Any]:
    """Archive a session.

    Behavior:
        - Summarize the session content via a lightweight summarizer agent.
        - Persist summary as a markdown file under `data/session_summaries/`.
        - Delete the session store file (.jsonl or legacy .db).
        - Rebuild sessions index.
        - If the deleted session was active, switch active to the newest remaining session.

    Notes:
        - On Windows, deleting an open SQLite file may raise WinError 32.
          JsonlSession does not keep the file open, but we keep retries anyway.

    Returns:
        Dict with ok flag and updated active_session_id.
    """

    if not session_id.isdigit():
        return {"ok": False, "error": "invalid_session_id"}
    
    messages = get_recent_messages(session_id=session_id, limit=200)
    if asyncio.get_running_loop().is_running():
        asyncio.create_task(summerize_session(messages=messages, session_id=session_id))
    else:
        asyncio.run(summerize_session(messages=messages, session_id=session_id))

    db_path = SESSIONS_DIR / f"{session_id}.jsonl"
    if not db_path.exists():
        return {"ok": False, "error": "session_store_missing"}

    # Best-effort: Windows may keep the file locked briefly.
    last_err: Exception | None = None
    for _ in range(20):
        try:
            db_path.unlink()
            last_err = None
            break
        except PermissionError as e:
            last_err = e
            time.sleep(0.1)
            print(f"archive_session_store: retry deleting {db_path} due to {repr(e)}")

    if last_err is not None and db_path.exists():
        print(f"archive_session_store: failed to delete {db_path}: {repr(last_err)}")
        return {"ok": False, "error": "session_store_busy", "detail": repr(last_err)}

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
    }