<script lang="ts">
  import DOMPurify from 'dompurify';
  import { marked } from 'marked';
  import { tick } from 'svelte';

  let status: 'disconnected' | 'connected' = 'disconnected';
  let pendingRuns = 0;
  let text = '';
  let messages: { role: 'user' | 'assistant' | 'meta'; text: string; id?: string; status?: 'pending' | 'sent' }[] = [];

  let ws: WebSocket | null = null;

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

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${location.hostname}:8000/ws`;

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

  function send() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const t = text.trim();
    if (!t) return;

    const id = crypto.randomUUID();
    messages = [...messages, { role: 'user', id, status: 'pending', text: t }];
    pendingRuns += 1;
    ws.send(JSON.stringify({ type: 'user_message', message_id: id, text: t }));
    text = '';
  }

  connect();
</script>

<main class="h-screen grid grid-rows-[auto_1fr_auto]">
  <header class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
    <div class="text-lg font-semibold">Tennisbot Web UI</div>
    <div class="text-base text-gray-500">
      {#if pendingRuns > 0}
        thinking...
      {:else}
        {status}
      {/if}
    </div>
  </header>

  <section class="p-4 overflow-auto bg-gray-50">
    {#each messages as m}
      {#if m.role === 'meta'}
        <div class="my-1 text-base font-semibold text-gray-600 whitespace-pre-wrap">{m.text}</div>
      {:else}
      <div class={m.role === 'user' ? 'flex justify-end my-2' : 'flex justify-start my-2'}>
        <div
          class={
            m.role === 'user'
              ? 'max-w-[70ch] px-3 py-2 rounded-xl bg-gray-900 text-white border border-gray-900 whitespace-pre-wrap'
              : 'max-w-[70ch] px-3 py-2 rounded-xl bg-white text-gray-900 border border-gray-200 whitespace-pre-wrap'
          }
        >
          {#if m.role === 'assistant'}
            <div class="prose prose-base leading-snug max-w-none">{@html renderMarkdown(m.text)}</div>
          {:else}
            <div class="prose prose-base prose-invert leading-snug max-w-none">{@html renderMarkdown(m.text)}</div>{m.role === 'user' && m.status === 'pending' ? ' (sending...)' : ''}
          {/if}
        </div>
      </div>
      {/if}
    {/each}
  </section>

  <footer class="flex gap-2 px-4 py-3 border-t border-gray-200">
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
</main>
