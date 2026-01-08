# Tennisbot WebUI Voice Mode Plan (Voice input + final-text segmented TTS)

Date: 2026-01-08

## Goals
- Add **voice input** (mic recording) and **voice output** (segmented TTS playback) to Tennisbot WebUI.
- Keep **one unified session model**: voice mode and normal mode share the same session, history, and message pipeline.
- Phase 1: voice input + **final-text** segmented TTS (backend does not stream assistant text).
- Phase 2: add **assistant text streaming** and delta-driven segmented TTS (the only planned Phase 2 item).

## Product Requirements (from user)
1. **No separate voice session**: voice and text interactions must share the same session id, history, and UI thread.
2. **Voice input button near the text box**:
   - Click to start listening to mic.
   - Click again to stop recording.
   - After stop, send the recorded audio as a user message.
3. **Voice output toggle**:
   - When enabled, assistant replies should be spoken.
   - Use segmented TTS:
     - Phase 1: segment from final assistant text.
     - Phase 2: segment as assistant text deltas arrive.
   - Delimiters: `。！？\n`
   - `min_chars_per_chunk = 16`
   - Audio format: `mp3`

## Segmented TTS Algorithm

### Delimiters
- Split points: `。`, `！`, `？`, `\n`

### Constraints
- `min_chars_per_chunk = 16`
- **Allow short-sentence merge**: if a delimiter is found but the segment is shorter than `min_chars_per_chunk`, keep buffering and merge with following sentences until the buffered segment reaches the minimum.

### Backpressure strategy (queue waterline + tail buffer)
- Goal: prevent unbounded TTS backlog while keeping speech roughly in sync.
- Maintain:
  - `tts_queue`: stores **frozen** segments waiting for TTS.
  - `tail_buffer`: stores **overflow** text that is not yet frozen.
- Waterline:
  - Target: at most **5 frozen segments** in `tts_queue`.
  - When `tts_queue` already has 5 segments, any newly produced segment text is appended into `tail_buffer` instead of being enqueued.
  - When `tts_queue` size drops below 5, freeze current `tail_buffer` (if non-empty) and enqueue it, then reset `tail_buffer`.

- **Tail buffer flush rule**:
  - When flushing `tail_buffer` into `tts_queue`, **do not enforce** `min_chars_per_chunk`.
  - Rationale: otherwise short final replies (or short trailing text) may never be spoken.


## Backend Architecture (FastAPI)

### WS Endpoint
- Prefer **reuse existing session WS** to satisfy “same session” requirement.

### Message Types (Phase 1)
Client -> Server:
- `voice_input` {session_id, client_msg_id, audio_b64, mime}
- `voice_output_toggle` {session_id, enabled}

Server -> Client:
- `transcript_final` {session_id, client_msg_id, text}
- `assistant_text_final` {session_id, text}
- `tts_audio_segment` {session_id, seq, text, audio_b64, mime:"audio/mpeg"}
- `tts_done` {session_id}

### Message Types (Phase 2)
Server -> Client:
- `assistant_text_delta` {session_id, delta}

### Session State
Per session:
- `voice_output_enabled: bool`
- `tts_seq: int`
- `tts_queue: asyncio.Queue[str]`
- `tail_buffer: str`
- `tts_worker_task: asyncio.Task | None`
- `tts_cancel_token` (simple bool/monotonic generation id)

### TTS Worker
- One worker per session when voice output is enabled.
- Serializes TTS calls to preserve order.
- Drops results if canceled (toggle off / disconnect).

### Disconnect / Reconnect Policy
- On WS disconnect: stop playback on client; server clears `tts_queue`, resets `tail_buffer`, cancels `tts_worker_task`.
- On reconnect: **do not replay** previous audio segments. Text history remains available.

## Frontend Architecture (Svelte)

### UI Controls
- Near input box:
  - Mic button (toggle): start/stop recording.
- Somewhere in header or toolbar:
  - Speaker button (toggle): enable/disable voice output.

### Recording
- MediaRecorder -> collect chunks -> on stop, send as **one payload** via WS message `voice_input`.
- After stop:
  - Generate a stable `message_id` for the placeholder message.
  - Include `message_id` in the `voice_input` request.
  - Server echoes `message_id` in `transcript_final` so the client can replace the correct placeholder.

  - Immediately insert a **placeholder user message** with `transcribing`.
  - When `transcript_final` arrives, **replace** the placeholder content with transcript text.

### Playback
- Maintain an `audioQueue: Array<{seq, url}>`.
- Use a single `<audio>` element:
  - On `ended`, pop next and play.
- When voice output toggled off or WS disconnects:
  - Stop audio, clear queue, revoke object URLs.

## Open Questions
1. STT provider choice and accepted audio formats (Phase 1 can pass through browser format; normalize later if needed).
2. TTS provider choice and accepted input/output formats (mp3 required for playback segments).

## Local STT/TTS Deployment Notes (Whisper + ChatTTS)

### Environment
- Target machine has **NVIDIA GPU**.
- STT language: **mixed Chinese/English**.

### STT: Local Whisper
- Use a local Whisper deployment for speech-to-text.
- Audio normalization / transcoding: **TBD**. Decide based on what the chosen Whisper runtime accepts.
- For mixed CN/EN:
  - Prefer auto language detection, or configure per-request if the UI provides a hint.

### TTS: Local ChatTTS
- Use a local ChatTTS deployment for text-to-speech.
- Output format requirement: **mp3** segments.
- Encoding: ChatTTS typically outputs waveform; encode to mp3 in-memory (avoid disk I/O).

### Concurrency
- STT/TTS are heavy; do not block the FastAPI event loop.
- Run STT/TTS in a worker (thread/process) and communicate results back to the WS sender.

## Non-Goals (for now)
- Full duplex “barge-in” while TTS is playing.
- WebRTC echo cancellation pipeline.
- Perfect sentence segmentation for English abbreviations, decimals, etc.

## Acceptance Criteria
- Same session id and history for voice and text.
- Mic button records and sends audio; transcript appears as a user message.
- With voice output enabled, assistant replies are spoken as mp3 segments split by `。！？\n`, with minimum 16 chars per segment.
- UI can toggle voice output on/off; toggling off stops playback.
