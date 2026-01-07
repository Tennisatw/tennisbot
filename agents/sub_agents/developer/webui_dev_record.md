# Web UI Plan (FastAPI + Svelte)

Status: Draft

## Decisions
- Transport: WebSocket (primary), even for non-streaming MVP.
- UI: Tailwind CSS.
- Session: single session backed by `data/sessions/0.db`, multi-session reserved for later.
- Voice: out of scope for MVP (non-streaming voice later). Keep protocol extensible.

## MVP Scope
### Must-have
1. Chat UI
   - Message list (user/assistant)
   - Composer input + send
2. Session controls
   - Single fixed session (for now)
   - Buttons: **New / Archive** (placeholders; no-op for MVP)

### Not in MVP (but reserved)
- Token streaming
- Voice input/output
- Multi-session parallel runs
- Tool events visualization (future: read from logs)

## Architecture
### Backend
- FastAPI app
- WebSocket endpoint for chat/events
- Session storage: existing SQLite session store (`data/sessions/0.db`)
- Concurrency: queue runs per session (single session MVP).
  - Reserve `run_id` / `message_id` for future cancellation.

### Frontend
- Svelte (Vite)
- Tailwind
- Components
  - `ChatView.svelte`: render messages
  - `Composer.svelte`: input box + send
  - `SessionBar.svelte`: **New/Archive placeholders**

## Repository Layout Proposal
Create a new `web/` directory:

```
web/
  backend/
    app.py              # FastAPI app entry
    api.py              # routes/ws handlers
    models.py           # pydantic models / event schema
  frontend/
    package.json
    vite.config.ts
    src/
      main.ts
      App.svelte
      lib/
        api.ts          # ws client
        types.ts
      components/
        ChatView.svelte
        Composer.svelte
        SessionBar.svelte
```

Dev mode: run frontend and backend separately.
Prod mode: build frontend to `web/frontend/dist` and serve via FastAPI `StaticFiles`.

## WebSocket Protocol (Non-streaming MVP)
Use an event envelope to keep future extensibility.

### Client -> Server
- `user_message`

Example:
```json
{ "type": "user_message", "message_id": "uuid", "text": "hello" }
```

### Server -> Client (MVP)
- `ack` (optional but recommended): confirms message queued
- `assistant_message`
- `error`

Example:
```json
{ "type": "ack", "message_id": "uuid", "queue_pos": 0 }
{ "type": "assistant_message", "message_id": "uuid", "text": "..." }
```

### Reserved for later
- `run_started` / `run_finished`
- `cancel_run`
- `tool_call` / `tool_result` (future: may be reconstructed from logs instead)
- `asr_*` / `tts_*` (voice)

## Notes
- Even without token streaming, using WS now avoids a later refactor.
- For public access (future): add `AUTH_TOKEN` and bind host to `0.0.0.0` only when needed.

## Implementation Notes (Confirmed)
- SessionBar naming: use **New / Archive**.
  - For MVP, both buttons are placeholders (empty handlers / no-op on click).
- Tool events: **not in MVP**. Do not implement tool_call/tool_result. Future plan: read from logs for visualization.
- Concurrency (single session): allow continuous inputs; backend should **queue** requests per session and run them sequentially.
- Startup: `start.bat` should **start both backend and frontend** (one-command dev startup).
- CORS: enable CORS in FastAPI for dev (frontend dev server origin, e.g. `http://localhost:5173`).

## Change Log (This Session)
- Added backend skeleton:
  - `web/backend/app.py`
    - FastAPI app with CORS allowing `http://localhost:5173`
    - `GET /api/health` returns `{ "status": "ok" }`
    - `WS /ws` placeholder: accepts `user_message` and replies `ack` (no queue yet)
  - `web/backend/__init__.py`
- Added frontend skeleton (Svelte + Vite + TypeScript):
  - `web/frontend/package.json` (pnpm scripts)
  - `web/frontend/vite.config.ts`
  - `web/frontend/tsconfig.json`
  - `web/frontend/index.html`
  - `web/frontend/src/main.ts`
  - `web/frontend/src/App.svelte` (minimal chat UI)
  - `web/frontend/src/app.css`
  - `web/frontend/src/vite-env.d.ts`
- Tailwind integration (incremental):
  - `web/frontend/tailwind.config.js`
  - `web/frontend/postcss.config.js`
  - Updated `web/frontend/package.json` to include `tailwindcss`, `postcss`, `autoprefixer`
  - Updated `web/frontend/src/app.css` to Tailwind directives
  - Updated `web/frontend/src/App.svelte` to use Tailwind classes (removed inline CSS)
- Svelte 5 compatibility fix:
  - Updated `web/frontend/vite.config.ts` to set `compilerOptions.compatibility.componentApi = 4`
- Added dev startup script:
  - `start_web.bat` (opens two windows: backend on 8000, frontend on 5173)

## Notes / Current Issues
- Backend WebSocket currently fails without a WS library in the Python env.
  - Uvicorn warns: "No supported WebSocket library detected".
  - Fix: install `uvicorn[standard]` (recommended) or `websockets`/`wsproto`.

## Notes / Current Issues
- Backend WebSocket dependency resolved: `uvicorn[standard]` installed, WS now works.
- Current behavior:
  - Backend replies only `ack` (no `assistant_message` yet).
  - Frontend currently renders only user messages; it will render assistant messages when backend starts sending `assistant_message`.
- Next suggested steps (keep one change per patch):
  1) Backend: implement per-session queue + send `assistant_message` (start with echo), keep `message_id` mapping.
  2) Backend: replace echo with real `Runner.run(...)` output (non-streaming).
  3) Frontend: add basic components split (ChatView/Composer/SessionBar) once behavior stabilizes.
  4) Decide whether to merge `start_web.bat` into `start.bat` or keep separate.



## Change Log (This Session)

### Backend (FastAPI)
- WS `/ws`:
  - Implemented real agent execution via `Runner.run(...)` (non-streaming), and send `assistant_message`.
  - Added `assistant_message.message_id` (server-generated UUID) and `parent_id` (original user `message_id`).
  - Added a global `run_lock` to serialize runs (single-session stability).
  - Added `dotenv.load_dotenv()` and verbose debug logs around WS receive/run/send.
  - Error handling: send `{type:"error", message:"runner_failed", detail:...}`.
- Session DB separation:
  - WebUI now uses `SQLiteSession("1", db_path="data/sessions/1.db")`.
  - `/api/messages` reads from `data/sessions/1.db` and filters `session_id="1"`.
- Added HTTP history endpoint:
  - `GET /api/messages?limit=50` returns recent `{id, role, text}` for user/assistant.

### Frontend (Svelte + Tailwind)
- WS protocol handling:
  - Render `error` events in chat (as assistant messages).
  - Added user message `id/status` and `ack` handling to mark pending -> sent.
  - Added header status UX:
    - Show `thinking...` when any user message is pending; otherwise show `connected/disconnected`.
  - Added auto-scroll to bottom after sending.
- Markdown rendering:
  - Added `marked` + `dompurify` and render assistant messages via `{@html renderMarkdown(...)}`.
  - Added Tailwind Typography (`@tailwindcss/typography`) and wrapped assistant output with `prose`.# WebUI Dev Record

## 2026-01-02

### Goal
- Stream server-side runtime events (tool calls / agent handoffs) to WebUI via WebSocket.
- Improve WebUI chat rendering (markdown, spacing, typography) and UX.

### Backend changes
- **`src/logger.py`**
  - Enhanced `@logged_tool` to emit structured events around tool execution:
    - `{"type":"tool_call","name":...,"phase":"start"}`
    - `{"type":"tool_call","name":...,"phase":"end","elapsed_ms":...}`
    - `{"type":"tool_call","name":...,"phase":"error","elapsed_ms":...,"error":...}`
  - Added `Logger.emit(payload)` as a structured event emitter (default logs as a single line).
- **`web/backend/app.py`**
  - Added an in-process `EventBus` (async queue + broadcast loop) to fan out events to all connected WebSocket clients.
  - Wired `logger.emit` to `event_bus.publish` so tool/agent events are pushed to the WebUI.
  - Registered/unregistered WebSocket connections to the bus on connect/disconnect.

### Frontend changes (`web/frontend/src/App.svelte`)
- **Event rendering**
  - Added `role: 'meta'` message type.
  - Rendered `tool_call` events as `meta` lines (not chat bubbles).
  - Rendered `agent_handoff` events as `meta` lines (e.g. `[handoff] -> <agent>`).
  - Made `meta` lines bold (`font-semibold`).
- **Markdown**
  - Added markdown normalization to reduce excessive blank-line spacing (collapse 3+ newlines to 2).
  - Enabled markdown rendering for **user** messages too.
  - Fixed user bubble markdown visibility on dark background using `prose-invert`.
- **Typography / layout tweaks**
  - Increased overall font sizes (chat content, input, Send button, status text; title slightly larger).
  - Reduced markdown line-height using `leading-snug`.

### Notes / follow-ups
- Theme color experiments were done and later reverted by user.
- If Pylance complains about assigning to `logger.emit` due to `@dataclass(frozen=True)`, consider switching to `object.__setattr__` or removing `frozen`.


## 2026-01-07: WebUI backend per-session run locks
- Problem: global `run_lock` serialized agent runs across all sessions.
- Fix: replace global lock with `run_locks_by_session: dict[str, asyncio.Lock]` and helper `_get_run_lock(session_id)`; use `async with _get_run_lock(session_id):` around `Runner.run` to keep per-session serialization but allow parallelism across sessions.
- Also: cleanup `run_locks_by_session.pop(session_id, None)` in `/api/sessions/{session_id}/archive`.
