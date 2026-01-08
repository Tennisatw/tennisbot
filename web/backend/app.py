import asyncio
import json
import os
import time
import uuid
from typing import Any
import base64
from dataclasses import dataclass, field
import subprocess
import tempfile

from faster_whisper import WhisperModel

import dotenv
from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent


from src.jsonl_session import JsonlSession
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents
from src.session_history import get_recent_messages, push_session_history
from src.sessions_index import SESSIONS_DIR, create_session as create_session_store, ensure_session_db, load_sessions_index, rebuild_sessions_index, set_active_session_id
from src.settings import settings
from src.logger import current_session_id, logger
from src.session_archive import archive_session_store

TTS_FAKE_AUDIO_PATH="data/temp/y2294.mp3"
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
        # Map websocket -> bound session_id (or None for broadcast).
        self._clients: dict[WebSocket, str | None] = {}
        self._lock = asyncio.Lock()

    async def publish(self, payload: dict[str, Any]) -> None:
        await self._queue.put(payload)

    async def add(self, ws: WebSocket, *, session_id: str | None) -> None:
        async with self._lock:
            self._clients[ws] = session_id

    async def remove(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.pop(ws, None)

    async def run(self) -> None:
        """Broadcast loop."""

        while True:
            payload = await self._queue.get()
            data = json.dumps(payload, ensure_ascii=False)
            payload_session_id = payload.get("session_id")

            async with self._lock:
                clients = list(self._clients.items())

            if not clients:
                continue

            dead: list[WebSocket] = []
            for ws, ws_session_id in clients:
                if isinstance(payload_session_id, str) and ws_session_id != payload_session_id:
                    continue

                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)

            if dead:
                async with self._lock:
                    for ws in dead:
                        self._clients.pop(ws, None)

event_bus = EventBus()


async def _emit(payload: dict[str, Any]) -> None:
    """Emit server-side events to websocket clients.

    Notes:
        - Auto-inject session_id from ContextVar for tool/handoff events.
        - Keep the logger.emit contract: async and accepts a dict payload.
    """

    sid = current_session_id.get()
    if isinstance(sid, str) and sid and "session_id" not in payload:
        payload = {**payload, "session_id": sid}

    await event_bus.publish(payload)


logger.emit = _emit
@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(event_bus.run())
    # Ensure sessions index exists.
    load_sessions_index()

@app.get("/api/sessions")
async def list_sessions() -> dict[str, Any]:
    """List available sessions.

    Notes:
        - Source of truth is `data/sessions/*.jsonl`.
        - Index is rebuilt on demand.
    """

    index = rebuild_sessions_index()
    return {"sessions": index.get("sessions", []), "active_session_id": index.get("active_session_id")}


@app.put("/api/sessions/{session_id}/active")
async def set_active_session(session_id: str) -> dict[str, Any]:
    """Set active session.

    Notes:
        - Active session is persisted in `data/sessions/index.json`.
        - If the jsonl file is missing, this returns an error.
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
        - Ensure no active SQLiteSession is holding the jsonl file.
    """

    # Drop in-memory agent bundle for this session.
    agents_by_session.pop(session_id, None)
    # Best-effort cleanup for per-session run lock.
    run_locks_by_session.pop(session_id, None)

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

def _get_run_lock(session_id: str) -> asyncio.Lock:
    """Get per-session run lock.

    Notes:
        - Avoid global serialization across sessions.
        - Keep per-session agent state mutation serialized.
    """

    lock = run_locks_by_session.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        run_locks_by_session[session_id] = lock
    return lock


run_locks_by_session: dict[str, asyncio.Lock] = {}
agents_by_session: dict[str, Any] = {}

# --- Voice output (TTS) session state (Phase 1/2)
# Note: actual TTS synthesis is implemented in next step. For now we only
# persist the toggle state and define outgoing event types.
voice_output_enabled_by_session: dict[str, bool] = {}



@dataclass
class TtsSessionState:
    enabled: bool = False
    seq: int = 0
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=200))
    tail_buffer: str = ""
    cancel_gen: int = 0
    worker_task: asyncio.Task | None = None
    reply_to: str | None = None


tts_state_by_session: dict[str, TtsSessionState] = {}


def _get_tts_state(session_id: str) -> TtsSessionState:
    st = tts_state_by_session.get(session_id)
    if st is None:
        st = TtsSessionState(enabled=bool(voice_output_enabled_by_session.get(session_id, False)))
        tts_state_by_session[session_id] = st
    return st


def _tts_split_flushable_segments(*, buf: str, min_chars: int = 16) -> tuple[list[str], str]:
    """Split buffer into flushable segments.

    Delimiters: 。！？\n
    Returns: (segments_to_flush, remaining_buf)

    Rule:
      - Emit a segment only when a delimiter is seen AND the candidate segment length >= min_chars.
      - Otherwise keep buffering (short sentence merge).
    """

    delims = set(["。", "！", "？", "\n"])
    out: list[str] = []
    last_cut = 0

    for i, ch in enumerate(buf):
        if ch not in delims:
            continue

        cand = buf[last_cut : i + 1]
        if len(cand.strip()) < min_chars:
            continue

        out.append(cand.strip())
        last_cut = i + 1

    rest = buf[last_cut:]
    return out, rest


def _tts_maybe_start_worker(*, session_id: str) -> None:
    st = _get_tts_state(session_id)
    if st.worker_task is not None and not st.worker_task.done():
        return

    async def _worker(gen: int) -> None:
        while True:
            seg = await st.queue.get()

            # canceled or disabled: drop.
            if gen != st.cancel_gen or not st.enabled:
                continue

            st.seq += 1
            seq = st.seq
            reply_to = st.reply_to

            global _tts_fake_audio_b64
            audio_b64 = ""
            if TTS_FAKE_AUDIO_PATH:
                try:
                    if _tts_fake_audio_b64 is None:
                        with open(TTS_FAKE_AUDIO_PATH, "rb") as f:
                            _tts_fake_audio_b64 = base64.b64encode(f.read()).decode("ascii")
                    audio_b64 = _tts_fake_audio_b64 or ""
                except Exception as e:
                    logger.log(f"tts.fake_audio_load_failed path={TTS_FAKE_AUDIO_PATH} err={e!r}")

            # Fake TTS for now: send empty audio payload.
            await _ws_publish(
                session_id,
                {
                    "type": "tts_audio_segment",
                    "reply_to": reply_to,
                    "seq": seq,
                    "text": seg,
                    "audio_b64": audio_b64,
                    "mime": "audio/mpeg",
                },
            )

    st.worker_task = asyncio.create_task(_worker(st.cancel_gen))


def _tts_reset_session(*, session_id: str) -> None:
    st = _get_tts_state(session_id)
    st.cancel_gen += 1
    st.tail_buffer = ""
    st.reply_to = None
    # best-effort drain queue
    try:
        while not st.queue.empty():
            st.queue.get_nowait()
    except Exception:
        pass


async def _tts_enqueue_text(*, session_id: str, reply_to: str, text_delta: str) -> None:
    """Delta-driven segmenter + enqueue with waterline/tail_buffer."""

    st = _get_tts_state(session_id)
    if not st.enabled:
        return

    if st.reply_to != reply_to:
        # New turn: reset seq/buffers for clarity.
        st.seq = 0
        st.tail_buffer = ""
        st.reply_to = reply_to

    buf = st.tail_buffer + text_delta
    segs, rest = _tts_split_flushable_segments(buf=buf, min_chars=16)

    # Waterline: allow at most 5 frozen segments in queue.
    for seg in segs:
        if st.queue.qsize() >= 5:
            st.tail_buffer = rest
            st.tail_buffer += seg
            return
        await st.queue.put(seg)

    st.tail_buffer = rest
    _tts_maybe_start_worker(session_id=session_id)


async def _tts_finalize_reply(*, session_id: str, reply_to: str) -> None:
    st = _get_tts_state(session_id)
    if not st.enabled:
        return

    # Flush tail_buffer even if short.
    if st.reply_to == reply_to and st.tail_buffer.strip():
        if st.queue.qsize() < 5:
            await st.queue.put(st.tail_buffer.strip())
        st.tail_buffer = ""

    await _ws_publish(session_id, {"type": "tts_done", "reply_to": reply_to})



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


async def _ws_publish(session_id: str, payload: dict[str, Any]) -> None:
    """Publish a websocket event scoped to a session."""

    payload.setdefault("session_id", session_id)
    await event_bus.publish(payload)


VOICE_INPUT_MAX_BYTES = 20 * 1024 * 1024
VOICE_STT_MODEL_SIZE = "medium"
VOICE_DEBUG_DUMP_DIR = "data/voice_debug"

# Voice output (TTS) debug: if set, server will send this mp3 payload for every tts_audio_segment.
# Example: TTS_FAKE_AUDIO_PATH=data/temp/y2294.mp3
_tts_fake_audio_b64: str | None = None

_stt_model: WhisperModel | None = None
_stt_model_lock = asyncio.Lock()


async def _get_stt_model() -> WhisperModel:
    """Get singleton WhisperModel.

    Notes:
        - Model load is heavy; keep one instance per process.
        - Use a lock to avoid concurrent loads.
    """

    global _stt_model
    if _stt_model is not None:
        return _stt_model

    async with _stt_model_lock:
        if _stt_model is not None:
            return _stt_model

        # device/compute_type are intentionally simple defaults.
        # If you have NVIDIA GPU, faster-whisper will use CUDA when available.
        _stt_model = WhisperModel(
            VOICE_STT_MODEL_SIZE,
            device="cuda",
            compute_type="float16",
        )
        logger.log(f"stt.model_loaded size={VOICE_STT_MODEL_SIZE} device=cuda compute_type=float16")
        return _stt_model


def _transcode_to_wav_16k_mono(*, audio_bytes: bytes, mime: str) -> bytes:
    """Transcode arbitrary audio bytes to wav(16kHz, mono, s16le) via ffmpeg.

    Notes:
        - Use temp files for simplicity.
        - Requires `ffmpeg` in PATH.
    """

    # Best-effort extension hint for ffmpeg.
    ext = "bin"
    if "webm" in mime:
        ext = "webm"
    elif "ogg" in mime:
        ext = "ogg"
    elif "wav" in mime:
        ext = "wav"
    elif "mpeg" in mime or "mp3" in mime:
        ext = "mp3"
    elif "mp4" in mime:
        ext = "mp4"

    with tempfile.TemporaryDirectory() as td:
        in_path = os.path.join(td, f"in.{ext}")
        out_path = os.path.join(td, "out.wav")

        with open(in_path, "wb") as f:
            f.write(audio_bytes)

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            in_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            out_path,
        ]
        subprocess.run(cmd, check=True)

        with open(out_path, "rb") as f:
            return f.read()


def _stt_transcribe_sync(*, wav_bytes: bytes) -> str:
    """Run STT sync in a worker thread."""

    # faster-whisper can take a file path; keep it simple.
    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "audio.wav")
        with open(wav_path, "wb") as f:
            f.write(wav_bytes)

        # Lazy-load model in this thread via event loop helper.
        # We can't await here; model is global and created once.
        model = _stt_model
        if model is None:
            # Fallback: create model sync if called before async getter.
            model = WhisperModel(
                VOICE_STT_MODEL_SIZE,
                device="cuda",
                compute_type="float16",
            )
            globals()["_stt_model"] = model

        segments, _info = model.transcribe(wav_path)
        parts: list[str] = []
        for s in segments:
            t = (s.text or "").strip()
            if t:
                parts.append(t)
        return " ".join(parts).strip()


def _b64decode_audio(*, audio_b64: str) -> bytes:
    """Decode base64 audio payload.

    Notes:
        - Expects raw base64 without data URL prefix.
        - Enforces a hard size limit to avoid memory blowups.
    """

    if len(audio_b64) > (VOICE_INPUT_MAX_BYTES * 4 // 3) + 16:
        raise ValueError("audio_too_large")

    try:
        data = base64.b64decode(audio_b64, validate=True)
    except Exception as e:
        raise ValueError("invalid_audio_b64") from e

    if len(data) > VOICE_INPUT_MAX_BYTES:
        raise ValueError("audio_too_large")

    return data



async def _run_agent_for_user_text(*, session_id: str, message_id: str, user_text: str) -> str:
    """Run agent for a user text and return assistant final text.

    Notes:
        - Serialized by per-session lock to avoid concurrent mutation.
        - Persists last_agent back to agents_by_session.
    """

    async with _get_run_lock(session_id):
        current_agent = agents_by_session.get(session_id)
        if current_agent is None:
            current_agent = _new_session_agent()
            agents_by_session[session_id] = current_agent

        t0 = time.time()
        logger.log(
            "ws.runner.start "
            + f"id={message_id} agent={getattr(current_agent, 'name', None)} "
            + f"model={getattr(current_agent, 'model', None)} key_set={bool(os.getenv('OPENAI_API_KEY'))}"
        )

        session = JsonlSession(session_id, path=str(SESSIONS_DIR / f"{session_id}.jsonl"))
        result = await Runner.run(
            current_agent,
            user_text,
            session=session,  # type: ignore
            max_turns=settings.default_max_turns,
        )
        dt_ms = int((time.time() - t0) * 1000)
        logger.log(f"ws.runner.done id={message_id} ms={dt_ms}")

        last_agent = getattr(result, "last_agent", None)
        if last_agent is not None:
            agents_by_session[session_id] = last_agent

        assistant_text = str(getattr(result, "final_output", ""))
        logger.log(
            "chat role=assistant name="
            + getattr(agents_by_session[session_id], "name", "Agent")
            + " output="
            + assistant_text.replace("\\n", "\\\\n")
        )
        return assistant_text


async def _run_agent_streaming_for_user_text(
    *,
    session_id: str,
    reply_to_message_id: str,
    user_text: str,
) -> tuple[str, str]:
    """Run agent in streaming mode.

    Emits:
        - assistant_text_delta events during generation.

    Returns:
        (assistant_message_id, final_text)

    Notes:
        - Serialized by per-session lock to avoid concurrent mutation.
        - Updates `agents_by_session[session_id]` with `result.last_agent`.
    """

    async with _get_run_lock(session_id):
        current_agent = agents_by_session.get(session_id)
        if current_agent is None:
            current_agent = _new_session_agent()
            agents_by_session[session_id] = current_agent

        message_id = reply_to_message_id
        t0 = time.time()
        logger.log(
            "ws.runner.stream.start "
            + f"id={message_id} agent={getattr(current_agent, 'name', None)} "
            + f"model={getattr(current_agent, 'model', None)} key_set={bool(os.getenv('OPENAI_API_KEY'))}"
        )

        session = JsonlSession(session_id, path=str(SESSIONS_DIR / f"{session_id}.jsonl"))

        streamed = Runner.run_streamed(
            current_agent,
            user_text,
            session=session,  # type: ignore
            max_turns=settings.default_max_turns,
        )

        delta_parts: list[str] = []
        async for event in streamed.stream_events():
            # The SDK exposes model streaming via raw response events.
            if getattr(event, "type", None) != "raw_response_event":
                continue

            data = getattr(event, "data", None)
            if isinstance(data, ResponseTextDeltaEvent):
                delta = str(getattr(data, "delta", "") or "")
                if not delta:
                    continue

                delta_parts.append(delta)
                await _ws_publish(
                    session_id,
                    {
                        "type": "assistant_text_delta",
                        "reply_to": reply_to_message_id,
                        "delta": delta,
                    },
                )

                # Feed delta into TTS segmenter (Phase 2). Uses fake audio for now.
                try:
                    st = _get_tts_state(session_id)
                    if st.enabled:
                        await _tts_enqueue_text(session_id=session_id, reply_to=reply_to_message_id, text_delta=delta)
                except Exception as e:
                    logger.log(f"tts.enqueue_failed session_id={session_id} err={e!r}")

        result = streamed.final_output

        dt_ms = int((time.time() - t0) * 1000)
        logger.log(f"ws.runner.stream.done id={message_id} ms={dt_ms}")

        last_agent = getattr(result, "last_agent", None)
        if last_agent is not None:
            agents_by_session[session_id] = last_agent

        final_text = str(getattr(result, "final_output", "") or "")
        if not final_text:
            final_text = "".join(delta_parts)

        assistant_message_id = str(uuid.uuid4())
        logger.log(
            "chat role=assistant name="
            + getattr(agents_by_session[session_id], "name", "Agent")
            + " output="
            + final_text.replace("\\n", "\\\\n")
        )


        # Flush final tail buffer and notify client that TTS for this reply is done.
        try:
            st = _get_tts_state(session_id)
            if st.enabled:
                await _tts_finalize_reply(session_id=session_id, reply_to=reply_to_message_id)
        except Exception as e:
            logger.log(f"tts.finalize_failed session_id={session_id} err={e!r}")
        return assistant_message_id, final_text


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint.

    Protocol:
        - Client -> server: {"type": "user_message", "message_id": str, "text": str}
        - Server -> client: events published via EventBus.
    """

    await ws.accept()

    # Resolve session_id before registering ws.
    session_id = ensure_session_db(ws.query_params.get("session_id"))

    # Bind confirmation for frontend.
    # Frontend uses this to avoid session switch race conditions.
    await _ws_publish(session_id, {"type": "meta", "event": "ws_bound", "session_id": session_id})
    # Frontend uses this to confirm the websocket is bound to the expected session.

    await event_bus.add(ws, session_id=session_id)

    token = current_session_id.set(session_id)

    try:
        await push_session_history(ws, session_id=session_id, limit=200)
    except Exception:
        pass

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
            await _ws_publish(session_id, {"type": "error", "message": "invalid_json"})
            continue

        msg_type = msg.get("type")

        if msg_type == "voice_output_toggle":
            # Client -> Server: voice_output_toggle {session_id, enabled}
            client_session_id = msg.get("session_id")
            enabled = msg.get("enabled")

            if client_session_id != session_id:
                await _ws_publish(
                    session_id,
                    {
                        "type": "error",
                        "message": "session_mismatch",
                        "expected_session_id": session_id,
                        "got_session_id": client_session_id,
                    },
                )
                continue

            if not isinstance(enabled, bool):
                await _ws_publish(session_id, {"type": "error", "message": "invalid_enabled"})
                continue

            voice_output_enabled_by_session[session_id] = enabled

            st = _get_tts_state(session_id)
            st.enabled = enabled

            if not enabled:
                _tts_reset_session(session_id=session_id)
            else:
                _tts_maybe_start_worker(session_id=session_id)

            # Optional ack/meta so frontend can reflect server truth.
            await _ws_publish(session_id, {"type": "meta", "event": "voice_output", "enabled": enabled})
            logger.log(f"ws.voice_output_toggle enabled={enabled} session_id={session_id}")
            continue


        if msg_type == "voice_input":
            message_id = msg.get("message_id")
            logger.log(f"ws.recv voice_input id={message_id}")

            # Protocol (Phase 1):
            # Client -> Server: voice_input {session_id, message_id, audio_b64, mime}
            # Server -> Client: transcript_final {session_id, message_id, text}
            client_session_id = msg.get("session_id")
            if client_session_id != session_id:
                await _ws_publish(
                    session_id,
                    {
                        "type": "error",
                        "message": "session_mismatch",
                        "expected_session_id": session_id,
                        "got_session_id": client_session_id,
                    },
                )
                continue

            audio_b64 = msg.get("audio_b64")
            mime = msg.get("mime")
            if not isinstance(message_id, str) or not message_id:
                await _ws_publish(session_id, {"type": "error", "message": "invalid_message_id"})
                continue
            if not isinstance(audio_b64, str) or not audio_b64:
                await _ws_publish(session_id, {"type": "error", "message": "invalid_audio_b64"})
                continue
            if not isinstance(mime, str) or not mime:
                await _ws_publish(session_id, {"type": "error", "message": "invalid_mime"})
                continue

            try:
                audio_bytes = _b64decode_audio(audio_b64=audio_b64)
            except ValueError as e:
                await _ws_publish(session_id, {"type": "error", "message": str(e)})
                continue

            logger.log(f"ws.voice_input audio_bytes={len(audio_bytes)} mime={mime}")

            # Debug: dump raw browser audio payload for inspection.
            # try:
            #     os.makedirs(VOICE_DEBUG_DUMP_DIR, exist_ok=True)
            #     raw_path = os.path.join(VOICE_DEBUG_DUMP_DIR, f"{message_id}.input")
            #     meta_path = os.path.join(VOICE_DEBUG_DUMP_DIR, f"{message_id}.meta.txt")
            #     with open(raw_path, "wb") as f:
            #         f.write(audio_bytes)
            #     with open(meta_path, "w", encoding="utf-8") as f:
            #         f.write(f"mime={mime}\n")
            #         f.write(f"bytes={len(audio_bytes)}\n")
            #     logger.log(f"ws.voice_input.dumped path={raw_path}")
            # except Exception as e:
            #     logger.log(f"ws.voice_input.dump_failed id={message_id} err={e!r}")

            try:
                # Ensure model is loaded (async-safe) before running heavy work.
                await _get_stt_model()

                wav_bytes = await asyncio.to_thread(
                    _transcode_to_wav_16k_mono,
                    audio_bytes=audio_bytes,
                    mime=mime,
                )
                transcript = await asyncio.to_thread(_stt_transcribe_sync, wav_bytes=wav_bytes)
            except subprocess.CalledProcessError as e:
                logger.log(f"ws.voice_input.ffmpeg_failed id={message_id} err={e!r}")
                await _ws_publish(session_id, {"type": "error", "message": "ffmpeg_failed", "detail": repr(e)})
                continue
            except Exception as e:
                logger.log(f"ws.voice_input.stt_failed id={message_id} err={e!r}")
                await _ws_publish(session_id, {"type": "error", "message": "stt_failed", "detail": repr(e)})
                continue

            if not transcript:
                transcript = "(no speech detected)"

            await _ws_publish(
                session_id,
                {
                    "type": "transcript_final",
                    "message_id": message_id,
                    "text": transcript,
                },
            )
            logger.log(f"ws.sent transcript_final reply_to={message_id}")

            # Enter normal chat flow using the transcript as user input.
            try:
                await _ws_publish(session_id, {"type": "ack", "message_id": message_id, "queue_pos": 0})

                assistant_id, assistant_text = await _run_agent_streaming_for_user_text(
                    session_id=session_id,
                    reply_to_message_id=message_id,
                    user_text=transcript,
                )
            except Exception as e:
                logger.log(f"ws.runner.error id={message_id} err={e!r}")
                await _ws_publish(session_id, {"type": "error", "message": "runner_failed", "detail": repr(e)})
                continue

            await _ws_publish(
                session_id,
                {
                    "type": "assistant_message",
                    "message_id": assistant_id,
                    "reply_to": message_id,
                    "text": assistant_text,
                },
            )
            logger.log(f"ws.sent assistant_message id={assistant_id} reply_to={message_id}")
            continue


        if msg_type != "user_message":
            await _ws_publish(session_id, {"type": "error", "message": "unsupported_type"})
            continue

        message_id = msg.get("message_id")
        logger.log(f"ws.recv user_message id={message_id}")
        logger.log("chat role=user input=" + msg.get("text", "").replace("\\n", "\\\\n"))
        await _ws_publish(session_id, {"type": "ack", "message_id": message_id, "queue_pos": 0})

        user_text = msg.get("text", "")
        try:
            assistant_id, assistant_text = await _run_agent_streaming_for_user_text(
                session_id=session_id,
                reply_to_message_id=message_id,
                user_text=user_text,
            )
        except Exception as e:
            logger.log(f"ws.runner.error id={message_id} err={e!r}")
            await _ws_publish(session_id, {"type": "error", "message": "runner_failed", "detail": repr(e)})
            continue

        await _ws_publish(
            session_id,
            {
                "type": "assistant_message",
                # Link this assistant message to the triggering user message.
                # Frontend uses this to clear precise pending state.
                "message_id": assistant_id,
                "reply_to": message_id,
                "text": assistant_text,
            },
        )
        logger.log(f"ws.sent assistant_message id={assistant_id} reply_to={message_id}")

