# Tennisbot WebUI Voice Mode Plan (Voice input + final-text segmented TTS)

Date: 2026-01-08

## Current Status (implemented)
- ✅ Phase 1 STT 已落地（voice input -> transcript_final -> 作为 user message 驱动 agent 回复）。
- ❌ Phase 1 TTS（final-text segmented mp3）未实现。
- ❌ Phase 2（assistant delta text -> segmented TTS）未实现。

### Implemented Protocol / Flow (STT)
Client -> Server:
- voice_input { session_id, message_id, audio_b64, mime }

Server -> Client:
- transcript_final { session_id, message_id, text }
- assistant_message { session_id, message_id, reply_to, text }（沿用现有文本聊天输出类型）

### Implemented Backend (web/backend/app.py)
- WS: /ws?session_id=...
- voice input:
  - VOICE_INPUT_MAX_BYTES = 20MB
  - base64 decode（严格 validate + 大小限制）
  - ffmpeg 转码为 wav 16k mono pcm_s16le（临时目录）
  - faster-whisper:
    - VOICE_STT_MODEL_SIZE = "medium"（注意：旧 plan 写的是 small，已不一致）
    - GPU: device="cuda", compute_type="float16"
    - 模型全局单例 _stt_model + _stt_model_lock 防并发加载
    - STT + transcode 都跑在 asyncio.to_thread(...)，避免卡 event loop
  - transcript_final 回传；然后 _run_agent_for_user_text() 进入 Runner.run；最终发 assistant_message

### Implemented Frontend (web/frontend/src/App.svelte)
- UI：输入框旁新增 Voice toggle 按钮（录音中显示 Stop）
- 录音：navigator.mediaDevices.getUserMedia({audio:true}) + MediaRecorder
- 停止后：
  - 插入 placeholder user message： (transcribing...) ，id = messageId
  - Blob -> dataURL -> base64（剥离前缀）
  - 发送 voice_input（带 session_id/message_id/audio_b64/mime）
  - 收到 transcript_final 用 message_id 精准替换 placeholder
- 会话切换 race：
  - 后端 meta/ws_bound 回传确认 session
  - 前端维护 wsSessionId，未 bound 时将 voice payload 放入 queuedVoicePayload，等 bound 后 flush

### Notes / Known Gaps
- 目前 STT 没做语言 hints（CN/EN 混合依赖 whisper 自行判断）。
- _stt_transcribe_sync() 内部如果 model 未加载，会在 worker thread 再 sync new 一个（兜底）；但正常路径是先 await _get_stt_model()。
- 录音未显式设置 mime/codec（浏览器自选），后端靠 ffmpeg 吃掉。


## Goals
- Add voice input (mic recording) and voice output (segmented TTS playback) to Tennisbot WebUI.
- Keep one unified session model: voice mode and normal mode share the same session, history, and message pipeline.
- Phase 1: voice input + final-text segmented TTS (backend does not stream assistant text).
- Phase 2: add assistant text streaming and delta-driven segmented TTS (the only planned Phase 2 item).

## Product Requirements (from user)
1. No separate voice session: voice and text interactions must share the same session id, history, and UI thread.
2. Voice input button near the text box:
   - Click to start listening to mic.
   - Click again to stop recording.
   - After stop, send the recorded audio as a user message.
3. Voice output toggle:
   - When enabled, assistant replies should be spoken.
   - Use segmented TTS:
     - Phase 1: segment from final assistant text.
     - Phase 2: segment as assistant text deltas arrive.
   - Delimiters: 。！？\n
   - min_chars_per_chunk = 16
   - Audio format: mp3

## Segmented TTS Algorithm

### Delimiters
- Split points: 。, ！, ？, \n

### Constraints
- min_chars_per_chunk = 16
- Allow short-sentence merge: if a delimiter is found but the segment is shorter than min_chars_per_chunk, keep buffering and merge with following sentences until the buffered segment reaches the minimum.

### Backpressure strategy (queue waterline + tail buffer)
- Goal: prevent unbounded TTS backlog while keeping speech roughly in sync.
- Maintain:
  - tts_queue: stores frozen segments waiting for TTS.
  - tail_buffer: stores overflow text that is not yet frozen.
- Waterline:
  - Target: at most 5 frozen segments in tts_queue.
  - When tts_queue already has 5 segments, any newly produced segment text is appended into tail_buffer instead of being enqueued.
  - When tts_queue size drops below 5, freeze current tail_buffer (if non-empty) and enqueue it, then reset tail_buffer.

- Tail buffer flush rule:
  - When flushing tail_buffer into tts_queue, do not enforce min_chars_per_chunk.
  - Rationale: otherwise short final replies (or short trailing text) may never be spoken.


## Backend Architecture (FastAPI)

### WS Endpoint
- Reuse existing session WS to satisfy “same session” requirement.

### Message Types (Phase 1)
Client -> Server:
- voice_input {session_id, message_id, audio_b64, mime}
- voice_output_toggle {session_id, enabled}

Server -> Client:
- transcript_final {session_id, message_id, text}
- assistant_message {session_id, message_id, reply_to, text}
- tts_audio_segment {session_id, seq, text, audio_b64, mime:"audio/mpeg"}
- tts_done {session_id}

### Message Types (Phase 2)
Server -> Client:
- assistant_text_delta {session_id, delta}

### Session State (for TTS)
Per session:
- voice_output_enabled: bool
- tts_seq: int
- tts_queue: asyncio.Queue[str]
- tail_buffer: str
- tts_worker_task: asyncio.Task | None
- tts_cancel_token (simple bool/monotonic generation id)

### TTS Worker
- One worker per session when voice output is enabled.
- Serializes TTS calls to preserve order.
- Drops results if canceled (toggle off / disconnect).

### Disconnect / Reconnect Policy
- On WS disconnect: stop playback on client; server clears tts_queue, resets tail_buffer, cancels tts_worker_task.
- On reconnect: do not replay previous audio segments. Text history remains available.


## Frontend Architecture (Svelte)

### UI Controls
- Near input box:
  - Voice button (toggle): start/stop recording. ✅
- In header:
  - Speaker button (toggle): enable/disable voice output. ❌

### Recording ✅
- MediaRecorder -> collect chunks -> on stop, send as one payload via WS message voice_input.
- Uses placeholder user message keyed by message_id and replaces via transcript_final.
- queuedVoicePayload handles “socket not yet bound” edge.

### Playback (TTS) ❌
- Maintain an audioQueue: Array<{seq, url}>.
- Use a single <audio> element:
  - On ended, pop next and play.
- When voice output toggled off or WS disconnects:
  - Stop audio, clear queue, revoke object URLs.


## Local STT/TTS Deployment Notes (Whisper + ChatTTS)

### STT: Local Whisper ✅
- faster-whisper 已接入，ffmpeg 做转码。

### TTS: Local ChatTTS (planned)
- Use local ChatTTS -> waveform -> encode to mp3 in-memory.

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
- With voice output enabled, assistant replies are spoken as mp3 segments split by 。！？\n with minimum 16 chars per segment.
- UI can toggle voice output on/off; toggling off stops playback.
