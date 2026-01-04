# Bugs / TODO (multi-session)

## 1) Backend: EventBus broadcasts across sessions (cross-session leak)

### Symptom
- When multiple WebSocket clients are connected (e.g. multiple tabs / sessions), server-side meta events (tool_call / handoff / logs emitted via `logger.emit`) are broadcast to **all** clients.
- This causes session A to see meta events triggered by session B.

### Root cause
- `EventBus` is global and keeps only `_clients: set[WebSocket]`.
- `EventBus.run()` broadcasts every queued payload to every ws in `_clients`.
- `logger.emit = event_bus.publish` sends events without any session scoping.

### Minimal fix plan (recommended)
1. Track `session_id` per WebSocket connection.
   - Add `self._session_by_client: dict[WebSocket, str | None]` in `EventBus.__init__`.
   - Change `EventBus.add(...)` to accept `session_id` and store it.
   - Ensure `remove(...)` also deletes the mapping.

2. Filter broadcasts by `payload["session_id"]`.
   - In `EventBus.run()`, read `payload_session_id = payload.get("session_id")`.
   - If `payload_session_id` is a valid digit string, only send to clients whose stored session_id matches.
   - If payload has no session_id, decide policy:
     - Option A: broadcast to all (keeps current behavior for global events)
     - Option B: drop (safer, avoids leaks)

3. Register ws with session_id.
   - In `ws_endpoint`, compute `session_id` first (from query param or active session).
   - Call `await event_bus.add(ws, session_id=session_id)` **after** session_id is known.

4. Ensure emitted payloads include session_id.
   - Currently `logger.emit` payload likely does not include session_id.
   - Without this, filtering cannot work.
   - Quick approach: in `ws_endpoint`, wrap `logger.emit` for the duration of this connection:
     - Save old `emit = logger.emit`
     - Set `logger.emit = lambda p: emit({**p, "session_id": session_id})`
     - Restore on disconnect
   - Cleaner approach: implement task-local / contextvar session_id inside `src/logger.py`.

### Files
- `web/backend/app.py` (EventBus + ws_endpoint)
- Possibly `src/logger.py` (if choosing the cleaner approach)

## 2) Frontend: sidebar list height uses magic number

### Symptom
- Sidebar uses `h-[calc(100dvh-57px)]` for the sessions list.
- After adding the "New session" button, header height is >57px, so the list area may overflow / double-scroll.

### Fix
- Make sidebar a flex column:
  - `<aside class="... flex flex-col h-[100dvh]">`
  - Header: `class="shrink-0"`
  - List: `class="flex-1 overflow-auto"`
- Remove the magic number.

### File
- `web/frontend/src/App.svelte`
