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

