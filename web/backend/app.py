import asyncio
import json
import os
import time
import uuid
from typing import Any
from pathlib import Path

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


SESSIONS_DIR = Path("data/sessions")
SESSIONS_INDEX_PATH = SESSIONS_DIR / "index.json"


def _rebuild_sessions_index() -> dict[str, Any]:
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


def _load_sessions_index() -> dict[str, Any]:
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
        return _rebuild_sessions_index()


class EventBus:
    """Async event bus for pushing server-side events to WebSocket clients."""

    def __init__(self, *, maxsize: int = 2000):
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._clients: set[WebSocket] = set()
        self._session_by_client: dict[WebSocket, str | None] = {}
        self._lock = asyncio.Lock()

    def publish(self, payload: dict[str, Any]) -> None:
        """Publish an event.

        Notes:
            - Non-blocking. Drops events when queue is full.
        """

        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            return

    async def add(self, ws: WebSocket, *, session_id: str | None) -> None:
        async with self._lock:
            self._clients.add(ws)
            self._session_by_client[ws] = session_id

    async def remove(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
            self._session_by_client.pop(ws, None)

    async def run(self) -> None:
        """Broadcast loop."""

        while True:
            payload = await self._queue.get()
            data = json.dumps(payload, ensure_ascii=False)
            payload_session_id = payload.get("session_id")

            async with self._lock:
                clients = list(self._clients)

            if not clients:
                continue

            dead: list[WebSocket] = []
            for ws in clients:
                if isinstance(payload_session_id, str) and payload_session_id.isdigit():
                    async with self._lock:
                        ws_session_id = self._session_by_client.get(ws)
                    if ws_session_id != payload_session_id:
                        continue

                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)

            if dead:
                async with self._lock:
                    for ws in dead:
                        self._clients.discard(ws)
                        self._session_by_client.pop(ws, None)

event_bus = EventBus()
logger.emit = event_bus.publish


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(event_bus.run())
    # Ensure sessions index exists.
    # This also repairs it after manual deletion of db files.
    _load_sessions_index()


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


def _history_events_from_session(*, session_id: str, limit: int = 200) -> list[dict[str, Any]]:
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
            text = _extract_text(data)
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


async def push_session_history(ws: WebSocket, *, session_id: str, limit: int = 200) -> None:
    """Push session history to a connected WebSocket client."""

    for ev in _history_events_from_session(session_id=session_id, limit=limit):
        await ws.send_text(json.dumps(ev, ensure_ascii=False))


@app.get("/api/sessions")
async def list_sessions() -> dict[str, Any]:
    """List available sessions.

    Notes:
        - Source of truth is `data/sessions/*.db`.
        - Index is rebuilt on demand.
    """

    index = _rebuild_sessions_index()
    return {"sessions": index.get("sessions", []), "active_session_id": index.get("active_session_id")}


@app.put("/api/sessions/{session_id}/active")
async def set_active_session(session_id: str) -> dict[str, Any]:
    """Set active session.

    Notes:
        - Active session is persisted in `data/sessions/index.json`.
        - If the db file is missing, this returns an error.
    """

    if not session_id.isdigit():
        return {"ok": False, "error": "invalid_session_id"}

    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        return {"ok": False, "error": "session_db_missing"}

    index = _rebuild_sessions_index()
    index["active_session_id"] = session_id
    tmp_path = SESSIONS_INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(SESSIONS_INDEX_PATH)
    return {"ok": True, "active_session_id": session_id}


@app.post("/api/sessions")
async def create_session() -> dict[str, Any]:
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

    index = _rebuild_sessions_index()
    index["active_session_id"] = session_id
    tmp_path = SESSIONS_INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(SESSIONS_INDEX_PATH)

    # Pre-warm agent bundle for the new session.
    agents_by_session[session_id] = _new_session_agent()

    return {"session_id": session_id, "db_path": str(db_path)}


@app.get("/api/messages")
async def get_messages(limit: int = 50, session_id: str | None = None) -> dict[str, Any]:
    """Return recent chat messages from a session store."""

    limit = max(1, min(int(limit), 200))

    if session_id is None:
        session_id = _load_sessions_index().get("active_session_id")
    if not isinstance(session_id, str) or not session_id.isdigit():
        return {"messages": []}

    db_path = SESSIONS_DIR / f"{session_id}.db"
    if not db_path.exists():
        return {"messages": []}

    import sqlite3

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
                "text": _extract_text(data),
            }
        )

    return {"messages": items}


# base_agent = load_main_agent()
# base_agent_handoff_obj = create_handoff_obj(base_agent)
# sub_agents = load_sub_agents(handoffs=[base_agent_handoff_obj])
# base_agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in sub_agents]

# session = SQLiteSession("1", db_path="data/sessions/1.db")
# current_agent = base_agent
run_lock = asyncio.Lock()

def _new_session_agent():
    """Create a fresh agent bundle for a new session."""

    agent = load_main_agent()
    agent_handoff_obj = create_handoff_obj(agent)
    subs = load_sub_agents(handoffs=[agent_handoff_obj])
    agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in subs]
    return agent

agents_by_session: dict[str, Any] = {}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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

    # Resolve session_id before registering ws.
    session_id = ws.query_params.get("session_id")
    if not isinstance(session_id, str) or not session_id.isdigit():
        session_id = _load_sessions_index().get("active_session_id")
    if not isinstance(session_id, str) or not session_id.isdigit():
        session_id = str(int(time.time() * 1000))
        (SESSIONS_DIR / f"{session_id}.db").write_bytes(b"")
        _rebuild_sessions_index()

    await event_bus.add(ws, session_id=session_id)
    lock = asyncio.Lock()

    # Scope logger.emit to this session.
    _old_emit = logger.emit
    logger.emit = lambda p: _old_emit({**p, "session_id": session_id})

    # Send history for newly opened pages.
    if not isinstance(session_id, str) or not session_id.isdigit():
        session_id = _load_sessions_index().get("active_session_id")
    if not isinstance(session_id, str) or not session_id.isdigit():
        session_id = str(int(time.time() * 1000))
        (SESSIONS_DIR / f"{session_id}.db").write_bytes(b"")
        _rebuild_sessions_index()

    try:
        await push_session_history(ws, session_id=session_id, limit=200)
    except Exception:
        pass

    async def send(payload: dict[str, Any]) -> None:
        async with lock:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))

    while True:
        try:
            raw = await ws.receive_text()
        except Exception:
            await event_bus.remove(ws)
            logger.emit = _old_emit
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
            async with run_lock:
                current_agent = agents_by_session.get(session_id)
                if current_agent is None:
                    current_agent = _new_session_agent()
                    agents_by_session[session_id] = current_agent

                t0 = time.time()
                print(
                    f"[ws] runner.start id={message_id} agent={getattr(current_agent, 'name', None)} "
                    f"model={getattr(current_agent, 'model', None)} key_set={bool(os.getenv('OPENAI_API_KEY'))}"
                )
                session = SQLiteSession(session_id, db_path=str(SESSIONS_DIR / f"{session_id}.db"))
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
                    agents_by_session[session_id] = last_agent

                assistant_text = str(getattr(result, "final_output", ""))
                logger.log(
                    "chat role=assistant name="
                    + getattr(agents_by_session[session_id], "name", "Agent")
                    + " output="
                    + assistant_text.replace("\n", "\\n")
                )
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
