from __future__ import annotations

from typing import Any
from pathlib import Path
import time
import asyncio

from agents import Agent, Runner

from src.session_history import get_recent_messages
from src.sessions_index import SESSIONS_DIR, list_session_ids, rebuild_sessions_index, set_active_session_id


async def summarize_session(messages: list[dict[str, Any]], session_id: str) -> None:
    """Summarize session messages and persist summary as markdown file."""

    if not messages:
        return

    transcript_lines: list[str] = []
    for m in messages:
        role = m.get("role")
        text = (m.get("text") or "").strip()
        if role in ("user", "assistant") and text:
            transcript_lines.append(f"{role}: {text}")

    prompt = "请用中文，用一句话总结此会话。\n" + "\n".join(transcript_lines)

    summarizer = Agent(
        name="SessionSummarizer",
        instructions=(
            "用中文输出简洁、准确的会话总结。重点关注用户输入和结果。"
            "用户是Tennisatw，AI助理是Tennisbot"
        ),
        model="gpt-5-mini",
        tools=[],
    )

    result = await Runner.run(summarizer, prompt)
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
        - Delete the session store file (.jsonl).
        - Rebuild sessions index.

    Returns:
        Dict with ok flag and updated active_session_id.
    """

    if not session_id.isdigit():
        return {"ok": False, "error": "invalid_session_id"}
    
    messages = get_recent_messages(session_id=session_id, limit=200)
    asyncio.run(summarize_session(messages=messages, session_id=session_id))

    db_path = SESSIONS_DIR / f"{session_id}.jsonl"
    if not db_path.exists():
        return {"ok": False, "error": "session_store_missing"}
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
    }