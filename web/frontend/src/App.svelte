<script lang="ts">
  import DOMPurify from 'dompurify';
  import { marked } from 'marked';

  type SessionItem = { session_id: string };
  let sessions: SessionItem[] = [];
  let activeSessionId: string | null = null;
  let isChatActive = true;

  let status: 'disconnected' | 'connected' = 'disconnected';
  let pendingRuns = 0;
  let text = '';
  let messages: { role: 'user' | 'assistant' | 'meta'; text: string; id?: string; status?: 'pending' | 'sent' }[] = [];

  let ws: WebSocket | null = null;

  const API_BASE = 'http://localhost:8000';

  marked.setOptions({
    gfm: true,
    breaks: true
  });

  function normalizeMarkdown(src: string): string {
    return src.replace(/\n{3,}/g, '\n\n').trim();
  }

  function renderMarkdown(src: string): string {
    const normalized = normalizeMarkdown(src);
    return DOMPurify.sanitize(marked.parse(normalized) as string);
  }

  async function refreshSessions(): Promise<void> {
    const res = await fetch(`${API_BASE}/api/sessions`);
    const data = await res.json();
    sessions = Array.isArray(data.sessions) ? data.sessions : [];
    activeSessionId = typeof data.active_session_id === 'string' ? data.active_session_id : null;
  }

  async function ensureDefaultSession(): Promise<void> {
    await refreshSessions();
    if (sessions.length > 0) return;

    await fetch(`${API_BASE}/api/sessions`, { method: 'POST' });
    await refreshSessions();
  }

  async function setActiveSession(sessionId: string): Promise<void> {
    await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}/active`, { method: 'PUT' });
    activeSessionId = sessionId;
  }

  function resetChatState(): void {
    status = 'disconnected';
    pendingRuns = 0;
    text = '';
    messages = [];
  }

  async function createSession(): Promise<void> {
    const res = await fetch(`${API_BASE}/api/sessions`, { method: 'POST' });
    const data = await res.json();
    const sessionId = typeof data.session_id === 'string' ? data.session_id : null;
    await refreshSessions();
    if (!sessionId) return;
    await switchSession(sessionId);
  }

  async function switchSession(sessionId: string): Promise<void> {
    if (activeSessionId === sessionId && ws && ws.readyState === WebSocket.OPEN) return;

    isChatActive = true;
    resetChatState();

    if (ws) {
      try {
        ws.close();
      } catch {
        // ignore
      }
      ws = null;
    }

    await setActiveSession(sessionId);
    connect(sessionId);
  }

  function endSession(): void {
    isChatActive = false;
    resetChatState();

    if (ws) {
      try {
        ws.close();
      } catch {
        // ignore
      }
      ws = null;
    }
  }

  function connect(sessionId: string): void {
    if (ws) {
      try {
        ws.close();
      } catch {
        // ignore
      }
      ws = null;
    }

    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${location.hostname}:8000/ws?session_id=${encodeURIComponent(sessionId)}`;

    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      status = 'connected';
    };
    ws.onclose = () => {
      status = 'disconnected';
    };
    ws.onerror = () => {
      status = 'disconnected';
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'agent_handoff' && typeof msg.to_agent === 'string') {
          messages = [...messages, { role: 'meta', text: `[handoff] -> ${msg.to_agent}` }];
          return;
        }
        if (msg.type === 'tool_call' && typeof msg.name === 'string' && typeof msg.phase === 'string') {
          const name = msg.name;
          const phase = msg.phase;
          if (phase === 'end') {
            messages = [...messages, { role: 'meta', text: `[tool_call] ${name}` }];
          }
          if (phase === 'error') {
            messages = [...messages, { role: 'meta', text: `[tool_call] ${name} error` }];
          }
          return;
        }
        if (msg.type === 'assistant_message' && typeof msg.text === 'string') {
          messages = [...messages, { role: 'assistant', text: msg.text }];
          pendingRuns = Math.max(0, pendingRuns - 1);
          return;
        }
        if (msg.type === 'user_message' && typeof msg.text === 'string') {
          messages = [...messages, { role: 'user', text: msg.text, status: 'sent' }];
          return;
        }
        if (msg.type === 'error') {
          const detail = typeof msg.detail === 'string' ? `\n${msg.detail}` : '';
          const message = typeof msg.message === 'string' ? msg.message : 'unknown_error';
          messages = [...messages, { role: 'assistant', text: `[error] ${message}${detail}` }];
          pendingRuns = Math.max(0, pendingRuns - 1);
          return;
        }
        if (msg.type === 'ack' && typeof msg.message_id === 'string') {
          messages = messages.map((m) =>
            m.role === 'user' && m.id === msg.message_id ? { ...m, status: 'sent' } : m
          );
        }
      } catch {
        // ignore
      }
    };
  }

  function newId(): string {
    // Prefer crypto.randomUUID when available.
    // Fallback for older browsers / insecure contexts.
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function send() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const t = text.trim();
    if (!t) return;

    const id = newId();
    messages = [...messages, { role: 'user', id, status: 'pending', text: t }];
    pendingRuns += 1;
    ws.send(JSON.stringify({ type: 'user_message', message_id: id, text: t }));
    text = '';
  }

  (async () => {
    await ensureDefaultSession();
    if (activeSessionId) {
      await switchSession(activeSessionId);
    }
  })();
</script>

<main class="h-[100dvh] grid grid-cols-[280px_1fr] overflow-hidden">
  <aside class="border-r border-gray-200 bg-white grid grid-rows-[auto_1fr] min-h-[100dvh]">
    <div class="px-4 py-3 border-b border-gray-200">
      <div class="text-lg font-semibold">Tennisbot</div>
      <div class="text-sm text-gray-500">Sessions</div>

      <button
        class="mt-3 w-full px-3 py-2 text-sm rounded-lg border border-gray-900 bg-gray-900 text-white"
        on:click={createSession}
      >
        New session
      </button>
    </div>

    <div class="p-2 overflow-auto min-h-0">
      {#if sessions.length === 0}
        <div class="px-3 py-2 text-sm text-gray-500">No sessions</div>
      {:else}
        {#each sessions as s (s.session_id)}
          <button
            class={
              s.session_id === activeSessionId
                ? 'w-full text-left px-3 py-2 rounded-lg bg-gray-900 text-white'
                : 'w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 text-gray-900'
            }
            on:click={() => switchSession(s.session_id)}
          >
            <div class="text-sm font-medium truncate">{s.session_id}</div>
          </button>
        {/each}
      {/if}
    </div>
  </aside>

  <section class="grid grid-rows-[auto_1fr_auto] min-h-0">
    <header class="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
      <div class="text-lg font-semibold">Chat</div>
      <div class="flex items-center gap-3">
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50" on:click={endSession}>
          End session
        </button>

        <div class="text-base text-gray-500">
          {#if pendingRuns > 0}
            thinking...
          {:else}
            {status}
          {/if}
        </div>
      </div>
    </header>

    {#if !isChatActive}
      <div class="p-8 bg-gray-50 h-full">
        <div class="max-w-[70ch]">
          <div class="text-2xl font-semibold text-gray-900">No active session</div>
          <div class="mt-2 text-base text-gray-600">Select a session on the left, or create a new one.</div>
        </div>
      </div>
    {:else}
      <div class="p-4 pb-28 overflow-auto bg-gray-50 min-h-0">
        {#each messages as m}
          {#if m.role === 'meta'}
            <div class="my-1 text-base font-semibold text-gray-600">{m.text}</div>
          {:else}
            <div class={m.role === 'user' ? 'flex justify-end my-2' : 'flex justify-start my-2'}>
              <div
                class={
                  m.role === 'user'
                    ? `max-w-[70ch] px-3 py-2 rounded-xl bg-gray-900 text-white border border-gray-900 ${m.status === 'pending' ? 'opacity-60' : ''}`
                    : 'max-w-[70ch] px-3 py-2 rounded-xl bg-white text-gray-900 border border-gray-200'
                }
              >
                {#if m.role === 'assistant'}
                  <div class="prose prose-base leading-snug max-w-none">{@html renderMarkdown(m.text)}</div>
                {:else}
                  <div class="prose prose-base prose-invert leading-snug max-w-none">{@html renderMarkdown(m.text)}</div>
                {/if}
              </div>
            </div>
          {/if}
        {/each}
      </div>

      <footer class="flex gap-2 px-4 py-3 border-t border-gray-200 bg-white sticky bottom-0">
        <textarea
          class="flex-1 px-3 py-2 text-base rounded-xl border border-gray-300 outline-none focus:ring-2 focus:ring-gray-900/20 resize-none"
          rows={3}
          placeholder="Type a message..."
          bind:value={text}
          on:keydown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
        ></textarea>
        <button
          class="px-4 py-2 text-base rounded-xl border border-gray-900 bg-gray-900 text-white"
          on:click={send}
        >
          Send
        </button>
      </footer>
    {/if}
  </section>
</main>
