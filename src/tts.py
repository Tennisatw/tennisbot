import asyncio
import base64
import os
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from openai import OpenAI

from src.logger import logger

# publish(session_id, payload) -> awaitable
PublishFn = Callable[[str, dict], Awaitable[None]]

# Voice output (TTS) debug: if set, server will send this mp3 payload for every tts_audio_segment.
# Example: TTS_FAKE_AUDIO_PATH=data/temp/y2294.mp3
TTS_FAKE_AUDIO_PATH = os.getenv("TTS_FAKE_AUDIO_PATH", "")
_tts_fake_audio_b64: str | None = None


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
voice_output_enabled_by_session: dict[str, bool] = {}


def get_tts_state(session_id: str) -> TtsSessionState:
    st = tts_state_by_session.get(session_id)
    if st is None:
        st = TtsSessionState(enabled=bool(voice_output_enabled_by_session.get(session_id, False)))
        tts_state_by_session[session_id] = st
    return st


def tts_sanitize(t: str) -> str:
    import re

    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", t)
    t = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


_tts_client: OpenAI | None = None
_tts_client_lock = asyncio.Lock()


async def get_tts_client() -> OpenAI:
    global _tts_client
    if _tts_client is not None:
        return _tts_client

    async with _tts_client_lock:
        if _tts_client is not None:
            return _tts_client
        _tts_client = OpenAI()
        return _tts_client


def tts_synthesize_mp3_bytes_sync(*, client: OpenAI, text: str) -> bytes:
    t = (text or "").strip()
    if not t:
        return b""

    audio = client.audio.speech.create(
        model=os.getenv("TTS_MODEL", "gpt-4o-mini-tts"),
        voice=os.getenv("TTS_VOICE", "marin"),
        input=tts_sanitize(t),
        response_format="mp3",
        speed=1.15,
    )

    if hasattr(audio, "read"):
        return audio.read()
    if hasattr(audio, "content"):
        return audio.content  # type: ignore

    try:
        return bytes(audio)  # type: ignore
    except Exception:
        return b""


def tts_split_flushable_segments(*, buf: str, min_chars: int = 16) -> tuple[list[str], str]:
    delims = {"。", "！", "？", "\n"}
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


def tts_maybe_start_worker(*, session_id: str, publish: PublishFn) -> None:
    st = get_tts_state(session_id)
    if st.worker_task is not None and not st.worker_task.done():
        return

    async def _worker(gen: int) -> None:
        while True:
            seg = await st.queue.get()

            # Debug: log the exact segment that will be synthesized by the TTS worker.
            print("tts.worker_input seg=", (seg or "").replace("\n", "\\n"))

            # canceled or disabled: drop.
            if gen != st.cancel_gen or not st.enabled:
                continue

            st.seq += 1
            seq = st.seq
            reply_to = st.reply_to

            audio_b64 = ""

            try:
                if TTS_FAKE_AUDIO_PATH:
                    global _tts_fake_audio_b64
                    if _tts_fake_audio_b64 is None:
                        with open(TTS_FAKE_AUDIO_PATH, "rb") as f:
                            _tts_fake_audio_b64 = base64.b64encode(f.read()).decode("ascii")
                    audio_b64 = _tts_fake_audio_b64 or ""
                else:
                    client = await get_tts_client()
                    mp3_bytes = await asyncio.to_thread(
                        tts_synthesize_mp3_bytes_sync,
                        client=client,
                        text=seg,
                    )
                    if mp3_bytes:
                        audio_b64 = base64.b64encode(mp3_bytes).decode("ascii")
            except Exception as e:
                logger.log(f"tts.synthesize_failed session_id={session_id} err={e!r}")
                audio_b64 = ""

            await publish(
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


def tts_reset_session(*, session_id: str) -> None:
    st = get_tts_state(session_id)
    st.cancel_gen += 1
    st.tail_buffer = ""
    st.reply_to = None

    # best-effort drain queue
    try:
        while not st.queue.empty():
            st.queue.get_nowait()
    except Exception:
        pass


async def tts_enqueue_text(*, session_id: str, reply_to: str, text_delta: str, publish: PublishFn) -> None:
    # Debug: log the exact text fed into the TTS segmenter.
    print("tts.input_delta ", (text_delta or "").replace("\n", "\\n"))

    st = get_tts_state(session_id)
    if not st.enabled:
        return

    if st.reply_to != reply_to:
        st.seq = 0
        st.tail_buffer = ""
        st.reply_to = reply_to

    buf = st.tail_buffer + (text_delta or "")
    segs, rest = tts_split_flushable_segments(buf=buf, min_chars=16)

    for seg in segs:
        if st.queue.qsize() >= 100:
            return
        await st.queue.put(seg)

    st.tail_buffer = rest
    tts_maybe_start_worker(session_id=session_id, publish=publish)


async def tts_finalize_reply(*, session_id: str, reply_to: str, publish: PublishFn) -> None:
    st = get_tts_state(session_id)
    if not st.enabled:
        return

    # Flush tail_buffer even if short.
    if st.reply_to == reply_to and st.tail_buffer.strip():
        if st.queue.qsize() < 5:
            await st.queue.put(st.tail_buffer.strip())
        st.tail_buffer = ""

    tts_maybe_start_worker(session_id=session_id, publish=publish)
    await publish(session_id, {"type": "tts_done", "reply_to": reply_to})
