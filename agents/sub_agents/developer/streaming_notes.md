# Streaming output (WebUI)

Date: 2026-01-08

## Goal
Enable streaming assistant output in WebUI:
- Backend emits `assistant_text_delta` events over WebSocket during model generation.
- Backend emits `assistant_message_final` at the end to finalize the bubble.
- Frontend already supports `assistant_text_delta` + `assistant_message_final` keyed by `reply_to`.

## Current state
- Frontend (`web/frontend/src/App.svelte`) handles:
  - `meta/ws_bound`
  - `assistant_text_delta` (append by `reply_to`)
  - `assistant_message_final` (finalize by `reply_to`)
  - voice input protocol (`voice_input` -> `transcript_final` -> normal chat)
- Backend (`web/backend/app.py`) currently:
  - runs agent via `Runner.run(...)` and only sends final output.
  - imports `ResponseTextDeltaEvent` but does not stream.

## Plan (backend)
1. Switch agent execution to streaming mode using OpenAI Agents SDK streaming API.
2. While streaming:
   - For each `ResponseTextDeltaEvent`, publish WS event:
     - `{type: "assistant_text_delta", reply_to: <user_message_id>, delta: <text>}`
3. On completion:
   - Update `agents_by_session[session_id]` with `result.last_agent`.
   - Publish `{type: "assistant_message_final", message_id: <uuid>, reply_to: <user_message_id>, text: <final_text>}`.
4. Apply same flow for:
   - normal `user_message`
   - voice transcript chat step (after `transcript_final`)

## Notes / pitfalls
- Keep per-session lock to avoid concurrent mutation.
- Ensure deltas are scoped to the correct session_id (EventBus already supports scoping).
- If SDK final output differs from concatenated deltas, prefer SDK `final_output`.
- Consider cancellation: if WS disconnects mid-stream, best-effort stop streaming (optional).

## To verify
- Send a long prompt; UI should show token-by-token growth.
- Tool calls/handoffs still appear as meta messages.
- Session switching does not leak deltas across sessions.

## Frontend WS event contract (confirmed)
Confirmed by user: frontend fields are fixed as below.

### assistant_text_delta
- `type`: "assistant_text_delta"
- `delta`: string
- `reply_to`: string (user message_id)
- `session_id`: optional (backend currently injects via EventBus)

Frontend behavior:
- Find assistant message bubble with `role==='assistant' && reply_to===reply_to`.
- If exists: append `delta` to `text`.
- Else: create a new assistant message bubble with `text=delta`.

### assistant_message_final
- `type`: "assistant_message_final"
- `text`: string
- `reply_to`: string (user message_id)
- `message_id`: string (assistant message id)
- `session_id`: optional

Frontend behavior:
- If assistant bubble for `reply_to` exists: replace its `text` with final `text`.
- Else: create a new assistant message bubble.

### Related events (already supported)
- `meta/ws_bound`: {type:"meta", event:"ws_bound", session_id}
- `ack`: {type:"ack", message_id, queue_pos}
- `transcript_final`: {type:"transcript_final", message_id, text}
- `tool_call`: {type:"tool_call", name, phase, ...}
- `agent_handoff`: {type:"agent_handoff", to_agent, ...}
- `error`: {type:"error", message, detail?}
