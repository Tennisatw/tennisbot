import asyncio
import json
import os
import time
import uuid
from typing import Any

import dotenv
from agents import Runner, SQLiteSession
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents
from src.settings import settings
from src.logger import logger


dotenv.load_dotenv()
global WEBUI
WEBUI = True

logger.setup()
logger.log("webui.app.start")

app = FastAPI(title="Tennisbot Web UI")


def _extract_text(message_data: dict[str, Any]) -> str:
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


@app.get("/api/messages")
async def get_messages(limit: int = 50) -> dict[str, Any]:
    """Return recent chat messages from the single session store."""

    limit = max(1, min(int(limit), 200))

    import sqlite3

    conn = sqlite3.connect("data/sessions/1.db", timeout=0.2)
    try:
        rows = conn.execute(
            "SELECT id, message_data FROM agent_messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            ("1", limit),
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
                "text": _extract_text(data),
            }
        )

    return {"messages": items}


base_agent = load_main_agent()
base_agent_handoff_obj = create_handoff_obj(base_agent)
sub_agents = load_sub_agents(handoffs=[base_agent_handoff_obj])
base_agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in sub_agents]

session = SQLiteSession("1", db_path="data/sessions/1.db")
current_agent = base_agent
run_lock = asyncio.Lock()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    """WebSocket placeholder.

    MVP behavior:
    - Accept JSON messages.
    If message type is "user_message", run the agent and return the response.
    - Send back JSON messages.
    """

    await ws.accept()
    lock = asyncio.Lock()

    async def send(payload: dict[str, Any]) -> None:
        async with lock:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))

    while True:
        try:
            raw = await ws.receive_text()
        except Exception:
            return

        try:
            msg = json.loads(raw)
        except Exception:
            await send({"type": "error", "message": "invalid_json"})
            continue

        msg_type = msg.get("type")
        if msg_type != "user_message":
            await send({"type": "error", "message": "unsupported_type"})
            continue

        message_id = msg.get("message_id")
        print(f"[ws] recv user_message id={message_id}")
        logger.log("chat role=user input=" + msg.get("text", "").replace("\n", "\\n"))
        await send({"type": "ack", "message_id": message_id, "queue_pos": 0})

        user_text = msg.get("text", "")
        try:
            global current_agent
            async with run_lock:
                t0 = time.time()
                print(f"[ws] runner.start id={message_id} agent={getattr(current_agent, 'name', None)} model={getattr(current_agent, 'model', None)} key_set={bool(os.getenv('OPENAI_API_KEY'))}")
                result = await Runner.run(
                    current_agent,
                    user_text,
                    session=session,
                    max_turns=settings.default_max_turns,
                )
                dt_ms = int((time.time() - t0) * 1000)
                print(f"[ws] runner.done id={message_id} ms={dt_ms}")

                last_agent = getattr(result, "last_agent", None)
                if last_agent is not None:
                    current_agent = last_agent

                assistant_text = str(getattr(result, "final_output", ""))
                logger.log("chat role=assistant name=" + getattr(current_agent, "name", "Agent") + " output=" + assistant_text.replace("\n", "\\n"))
        except Exception as e:
            print(f"[ws] runner.error id={message_id} err={e!r}")
            await send({"type": "error", "message": "runner_failed", "detail": repr(e)})
            continue

        assistant_id = str(uuid.uuid4())
        await send(
            {
                "type": "assistant_message",
                "message_id": assistant_id,
                "parent_id": message_id,
                "text": assistant_text,
            }
        )
        print(f"[ws] sent assistant_message id={assistant_id} parent_id={message_id}")
