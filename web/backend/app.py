import asyncio
import json
import os
import time
import uuid
from typing import Any

import dotenv
from agents import Runner

from src.jsonl_session import JsonlSession
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents
from src.session_history import get_recent_messages, push_session_history
from src.sessions_index import SESSIONS_DIR, create_session as create_session_store, ensure_session_db, load_sessions_index, rebuild_sessions_index, set_active_session_id
from src.settings import settings
from src.logger import current_session_id, logger
from src.session_archive import archive_session_store


dotenv.load_dotenv()

logger.setup()
logger.log("webui.app.start")

app = FastAPI(title="Tennisbot Web UI")

@app.middleware("http")
async def log_http_requests(request, call_next):
    """Log HTTP request/response for WebUI API.

    Notes:
        - Keep it simple: method/path/query + status + elapsed.
        - Avoid logging large bodies.
    """

    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logger.log(
            "http.error "
            + f"method={request.method} path={request.url.path} query={request.url.query} "
            + f"elapsed_ms={elapsed_ms} err={e!r}"
        )
        raise

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.log(
        "http "
        + f"method={request.method} path={request.url.path} query={request.url.query} "
        + f"status={getattr(response, 'status_code', None)} elapsed_ms={elapsed_ms}"
    )
    return response



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
    load_sessions_index()

@app.get("/api/sessions")
async def list_sessions() -> dict[str, Any]:
    """List available sessions.

    Notes:
        - Source of truth is `data/sessions/*.db`.
        - Index is rebuilt on demand.
    """

    index = rebuild_sessions_index()
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

    try:
        index = set_active_session_id(session_id)
    except FileNotFoundError:
        return {"ok": False, "error": "session_store_missing"}
    return {"ok": True, "active_session_id": index.get("active_session_id")}


@app.post("/api/sessions")
async def create_session() -> dict[str, Any]:
    """Create a new session.

    Requirements:
        - session_id is Unix epoch milliseconds.
        - If called twice within the same millisecond, create only one session.
    """

    created = create_session_store()
    session_id = created["session_id"]

    # Pre-warm agent bundle for the new session.
    agents_by_session[session_id] = _new_session_agent()

    return created


@app.post("/api/sessions/{session_id}/archive")
async def archive_session(session_id: str) -> dict[str, Any]:
    """Archive a session.

    Notes:
        - Triggered by WebUI "End session".
        - Runs the sync archiver in a worker thread (it calls Runner.run_sync).
        - Ensure no active SQLiteSession is holding the db file.
    """

    # Drop in-memory agent bundle for this session.
    agents_by_session.pop(session_id, None)

    # No-op for JsonlSession.

    return await asyncio.to_thread(archive_session_store, session_id=session_id)


@app.get("/api/messages")
async def get_messages(limit: int = 50, session_id: str | None = None) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))

    if session_id is None:
        session_id = load_sessions_index().get("active_session_id")
    if not isinstance(session_id, str) or not session_id.isdigit():
        return {"messages": []}

    return {"messages": get_recent_messages(session_id=session_id, limit=limit)}

def _new_session_agent():
    """Create a fresh agent bundle for a new session."""

    agent = load_main_agent()
    agent_handoff_obj = create_handoff_obj(agent)
    subs = load_sub_agents(handoffs=[agent_handoff_obj])
    agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in subs]
    return agent

run_lock = asyncio.Lock()
agents_by_session: dict[str, Any] = {}


app.add_middleware(
    CORSMiddleware,
        allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.0.0.31:5173",
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
    session_id = ensure_session_db(ws.query_params.get("session_id"))

    # Bind confirmation for frontend.
    # Frontend uses this to avoid session switch race conditions.
    await ws.send_text(
        json.dumps(
            {"type": "meta", "event": "ws_bound", "session_id": session_id},
            ensure_ascii=False,
        )
    )

    await event_bus.add(ws, session_id=session_id)
    lock = asyncio.Lock()

    token = current_session_id.set(session_id)

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
            current_session_id.reset(token)
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
                session = JsonlSession(session_id, path=str(SESSIONS_DIR / f"{session_id}.jsonl"))
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
