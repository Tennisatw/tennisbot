<script lang="ts">
  import DOMPurify from 'dompurify';
  import { marked } from 'marked';
  import { tick } from 'svelte';

  let status: 'disconnected' | 'connected' = 'disconnected';
  let text = '';
  let messages: { role: 'user' | 'assistant'; text: string; id?: string; status?: 'pending' | 'sent' }[] = [];

  let ws: WebSocket | null = null;

  marked.setOptions({
    gfm: true,
    breaks: true
  });

  function renderMarkdown(src: string): string {
    return DOMPurify.sanitize(marked.parse(src) as string);
  }

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    const wsUrl = `ws://${location.hostname}:8000/ws`;
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
        if (msg.type === 'assistant_message' && typeof msg.text === 'string') {
          messages = [...messages, { role: 'assistant', text: msg.text }];
          return;
        }
        if (msg.type === 'error') {
          const detail = typeof msg.detail === 'string' ? `\n${msg.detail}` : '';
          const message = typeof msg.message === 'string' ? msg.message : 'unknown_error';
          messages = [...messages, { role: 'assistant', text: `[error] ${message}${detail}` }];
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
    ws.send(JSON.stringify({ type: 'user_message', message_id: id, text: t }));
    text = '';
  }

  connect();
</script>

<main class="h-screen grid grid-rows-[auto_1fr_auto]">
  <header class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
    <div class="font-semibold">Tennisbot Web UI</div>
    <div class="text-xs text-gray-500">
      {#if messages.some((m) => m.role === 'user' && m.status === 'pending')}
        thinking...
      {:else}
        {status}
      {/if}
    </div>
  </header>

  <section class="p-4 overflow-auto bg-gray-50">
    {#each messages as m}
      <div class={m.role === 'user' ? 'flex justify-end my-2' : 'flex justify-start my-2'}>
        <div
          class={
            m.role === 'user'
              ? 'max-w-[70ch] px-3 py-2 rounded-xl bg-gray-900 text-white border border-gray-900 whitespace-pre-wrap'
              : 'max-w-[70ch] px-3 py-2 rounded-xl bg-white text-gray-900 border border-gray-200 whitespace-pre-wrap'
          }
        >
          {#if m.role === 'assistant'}
            <div class="prose prose-sm max-w-none">{@html renderMarkdown(m.text)}</div>
          {:else}
            {m.text}{m.role === 'user' && m.status === 'pending' ? ' (sending...)' : ''}
          {/if}
        </div>
      </div>
    {/each}
  </section>

  <footer class="flex gap-2 px-4 py-3 border-t border-gray-200">
    <input
      class="flex-1 px-3 py-2 rounded-xl border border-gray-300 outline-none focus:ring-2 focus:ring-gray-900/20"
      placeholder="Type a message..."
      bind:value={text}
      on:keydown={(e) => e.key === 'Enter' && send()}
    />
    <button
      class="px-4 py-2 rounded-xl border border-gray-900 bg-gray-900 text-white"
      on:click={send}
    >
      Send
    </button>
  </footer>
</main>
