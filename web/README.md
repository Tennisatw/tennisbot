# Web UI

This folder contains the Web UI for Tennisbot.

## Structure

### backend/
- `backend/app.py`
  - FastAPI backend entry.
  - Endpoints:
    - `GET /api/health`: health check.
    - `GET /api/messages`: read recent user/assistant messages from `data/sessions/{session_id}.jsonl` (legacy: `.db`).
    - `WS /ws`: chat WebSocket. Receives `user_message`, runs the current agent via Agents SDK, and sends back events.

  - `EventBus` broadcasts server-side events (logger/tool calls/handoffs) to all connected WS clients.
  - Loads main agent + sub agents; keeps a `current_agent` that may change after handoffs.

- `backend/__init__.py`
  - Marks the backend as a Python package.

### frontend/
- `frontend/index.html`
  - Vite HTML template. Mounts the app to `#app` and loads `/src/main.ts`.

- `frontend/package.json`
  - Frontend dependencies and scripts (`dev`, `build`, `preview`).
  - Uses Svelte 5 + Vite 6 + TailwindCSS + TypeScript.

- `frontend/pnpm-lock.yaml`
  - Dependency lockfile for reproducible installs.

- `frontend/postcss.config.js`
  - PostCSS config enabling TailwindCSS and Autoprefixer.

- `frontend/tailwind.config.js`
  - Tailwind config. Enables `@tailwindcss/typography` for markdown rendering.

- `frontend/tsconfig.json`
  - TypeScript compiler options.

- `frontend/vite.config.ts`
  - Vite config with Svelte plugin.
  - Enables Svelte 5 compatibility mode for component API v4.

#### frontend/src/
- `src/main.ts`: app entry, mounts `App.svelte`.
- `src/App.svelte`: chat UI + WebSocket client + markdown rendering (`marked` + `DOMPurify`).
- `src/app.css`: Tailwind imports + small typography spacing tweaks.
- `src/vite-env.d.ts`: Vite TS type references.
