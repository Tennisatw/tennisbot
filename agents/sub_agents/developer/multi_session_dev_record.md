# Multi-session mode dev record

## Date
- 2026-01-04

## Goal
Turn Tennisbot into multi-session mode:
- Multiple sessions can exist and be switched like ChatGPT/WeChat.
- One session is displayed at a time.
- Each session is stored in its own SQLite DB file.

## Storage
- Session DB: `data/sessions/<session_id>.db`
- Session index: `data/sessions/index.json`

### session_id
- Use Unix epoch milliseconds (integer as string) as `session_id`.
- If user clicks "New session" twice within the same millisecond, create only one session.

## UI/UX
- Layout like ChatGPT:
  - Left sidebar lists all available sessions (name = `session_id` for now).
  - Right side is the chat view (reuse current UI as much as possible).
- Main page has a "New session" button.
  - After creating, automatically switch to the new session.
- In-session has an "End session" button.
  - For now: does nothing to DB (no archive/delete yet).
  - After clicking, navigate back to the main page.
- "No session" means: there is no DB file on disk.
  - If there is no DB file, auto-create/load a default session.

## Deferred
- "End session" should eventually archive and delete the session DB (and its history).
- No status field needed in UI (archived sessions are deleted).

## Open questions / to confirm later
- Exact definition of "main page" vs "chat page" in current frontend routing.
- Whether to persist `active_session_id` in `index.json`.
- Backend API shape for session list/create/switch.

## Dev log
- 2026-01-04: Requirements clarified and recorded.

## Confirmed decisions
- "End session" navigates back to a welcome/blank view on the right; left sidebar remains visible.
- On startup, treat `data/sessions/*.db` as the source of truth.
  - Rebuild/repair `data/sessions/index.json` by scanning existing DB files.

## Dev log
- 2026-01-04: Backend: POST /api/sessions now pre-warms an agent bundle via `agents_by_session[session_id] = _new_session_agent()`.
- 2026-01-04: Backend: `_rebuild_sessions_index()` now preserves `active_session_id` when possible.
- 2026-01-04: Backend: added `PUT /api/sessions/{session_id}/active` to persist active session in index.json.
- 2026-01-04: Backend: `GET /api/messages` now accepts optional `session_id` query param.

## Dev log
- 2026-01-04: Frontend: added sessions sidebar (two-column layout) with session switch via `switchSession(session_id)`.
- 2026-01-04: Frontend: added "New session" button in sidebar header; calls `POST /api/sessions` then auto-switches.
- 2026-01-04: Frontend: implemented "End session" (frontend-only): closes WS, clears chat state, and shows a blank/welcome view on the right; selecting a session re-activates chat.
