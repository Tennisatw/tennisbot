import asyncio
import base64
import os
import subprocess
import tempfile

from faster_whisper import WhisperModel

from src.logger import logger


VOICE_INPUT_MAX_BYTES = 20 * 1024 * 1024
VOICE_STT_MODEL_SIZE = "turbo"


VOICE_DEBUG_DUMP_DIR = "data/voice_debug"

_stt_model: WhisperModel | None = None
_stt_model_lock = asyncio.Lock()


async def get_stt_model() -> WhisperModel:
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

async def stt_transcribe_audio(*, audio_bytes: bytes, mime: str) -> str:
    """High-level STT helper.

    Takes raw audio bytes + mime, transcodes to 16k mono wav, then runs faster-whisper.

    Returns:
        transcript text (may be empty string)
    """

    # Ensure model is loaded (async-safe) before running heavy work.
    await get_stt_model()

    wav_bytes = await asyncio.to_thread(
        _transcode_to_wav_16k_mono,
        audio_bytes=audio_bytes,
        mime=mime,
    )
    return await asyncio.to_thread(stt_transcribe_wav_sync, wav_bytes=wav_bytes)

def stt_transcribe_wav_sync(*, wav_bytes: bytes) -> str:
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


def b64decode_audio(*, audio_b64: str) -> bytes:
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