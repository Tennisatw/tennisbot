<script lang="ts">
  import DOMPurify from 'dompurify';
  import { marked } from 'marked';

  type SessionItem = { session_id: string };

  // Sidebar sessions list.
  let sessions: SessionItem[] = [];
  let activeSessionId: string | null = null;
  let isChatActive = true;

  let status: 'disconnected' | 'connected' | 'new session' = 'disconnected';
  let text = '';
  let messages: {
    role: 'user' | 'assistant' | 'meta';
    text: string;
    id?: string;
    reply_to?: string;
    status?: 'pending' | 'sent';
  }[] = [];

  // WebSocket connection for the currently active session.
  let ws: WebSocket | null = null;

  // Session id confirmed by backend for this socket.
  let wsSessionId: string | null = null;

  // Text queued while the socket is not yet bound to the expected session.
  let queuedText: string | null = null;

  // Voice payload queued while the socket is not yet bound to the expected session.
  // Voice output toggle queued while the socket is not yet bound to the expected session.
  let queuedVoiceOutputEnabled: boolean | null = null;

  let queuedVoicePayload: any | null = null;

  // Voice output (TTS) toggle (Phase 1/2)
  let voiceOutputEnabled = false;

  // TTS playback queue
  let audioQueue: { seq: number; url: string; reply_to: string | null }[] = [];
  let isPlayingAudio = false;
  let currentAudioUrl: string | null = null;
  let audioPlayer: HTMLAudioElement | null = null;

  function stopAndClearAudioQueue(): void {
    try {
      if (audioPlayer) {
        audioPlayer.onended = null;
        audioPlayer.onerror = null;
        audioPlayer.pause();
        audioPlayer.src = '';
      }
    } catch {
      // ignore
    }
    audioPlayer = null;

    if (currentAudioUrl) {
      try {
        URL.revokeObjectURL(currentAudioUrl);
      } catch {
        // ignore
      }
    }
    for (const item of audioQueue) {
      try {
        URL.revokeObjectURL(item.url);
      } catch {
        // ignore
      }
    }
    audioQueue = [];
    isPlayingAudio = false;
    currentAudioUrl = null;
  }

  function handleAudioEnded(): void {
    isPlayingAudio = false;

    if (currentAudioUrl) {
      try {
        URL.revokeObjectURL(currentAudioUrl);
      } catch {
        // ignore
      }
    }

    currentAudioUrl = null;
    audioPlayer = null;

    void playNextAudio();
  }

  async function playNextAudio(): Promise<void> {
    if (isPlayingAudio) return;
    if (!voiceOutputEnabled) return;
    if (audioQueue.length === 0) return;

    const next = audioQueue[0];
    audioQueue = audioQueue.slice(1);

    isPlayingAudio = true;
    currentAudioUrl = next.url;

    try {
      audioPlayer = new Audio(next.url);
      audioPlayer.onended = handleAudioEnded;
      audioPlayer.onerror = handleAudioEnded;
      await audioPlayer.play();
    } catch {
      // Autoplay blocked or decode failed: skip this segment.
      handleAudioEnded();
    }
  }

  function b64ToBlobUrl(b64: string, mime: string): string | null {
    try {
      const binary = atob(b64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: mime });
      return URL.createObjectURL(blob);
    } catch {
      return null;
    }
  }

  // Voice input (Phase 1): mic recording -> voice_input ws message.
  let isRecording = false;
  let recorder: MediaRecorder | null = null;
  let recordChunks: BlobPart[] = [];
  let recordStream: MediaStream | null = null;

  // Markdown rendering is sanitized before injecting into DOM.
  marked.setOptions({
    gfm: true,
    breaks: true,
  });

  function renderMarkdown(src: string): string {
    return DOMPurify.sanitize(marked.parse(src.trim()) as string);
  }

  async function refreshSessions(): Promise<void> {
    const res = await fetch(`/api/sessions`);
    const data = await res.json();
    sessions = Array.isArray(data.sessions) ? data.sessions : [];
    activeSessionId = typeof data.active_session_id === 'string' ? data.active_session_id : null;
  }


  async function ensureDefaultSession(): Promise<void> {
    await refreshSessions();

    if (sessions.length > 0) return;

    await fetch(`/api/sessions`, { method: 'POST' });
    await refreshSessions();
  }


  async function setActiveSession(sessionId: string): Promise<void> {
    const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/active`, { method: 'PUT' });
    const data = await res.json().catch(() => ({}));
    if (!data || data.ok !== true) {
      throw new Error(typeof data?.error === 'string' ? data.error : 'set_active_failed');
    }
    activeSessionId = sessionId;
  }

  function resetChatState(): void {
    status = 'new session';
    text = '';
    messages = [];
  }

  async function createSession(): Promise<void> {
    // Clear old messages immediately.
    isChatActive = true;
    resetChatState();

    const res = await fetch(`/api/sessions`, { method: 'POST' });
    const data = await res.json();
    const sessionId = typeof data.session_id === 'string' ? data.session_id : null;
    await refreshSessions();
    if (!sessionId) return;

    await switchSession(sessionId);
  }


  // Switching session should stop any current TTS playback.
  async function switchSession(sessionId: string): Promise<void> {
    if (activeSessionId === sessionId && ws && ws.readyState === WebSocket.OPEN) return;

    isChatActive = true;
    resetChatState();

    // Connect first to avoid "UI switched but socket not ready" window.
    connect(sessionId);

    // Best-effort persist active session for sidebar highlight.
    try {
      await setActiveSession(sessionId);
    } catch {
      // ignore
    }

    await refreshSessions();
  }

  async function endSession(): Promise<void> {
    const sid = activeSessionId;

    // Immediately detach UI.
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

    // Archive on server (best-effort).
    if (sid) {
      try {
        await fetch(`/api/sessions/${encodeURIComponent(sid)}/archive`, { method: 'POST' });
      } catch {
        // ignore
      }
    }

    await refreshSessions();
  }

  // Connect to backend WebSocket and route incoming events into UI messages.
  // Protocol (msg.type): meta(ws_bound), user_message, assistant_message, ack, tool_call, agent_handoff, error.
    function connect(sessionId: string): void {
    // Close previous socket.
    if (ws) {
      try {
        ws.close();
      } catch {
        // ignore
      }
      ws = null;
    }

    status = 'disconnected';
    wsSessionId = null;

    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${location.host}/ws?session_id=${encodeURIComponent(sessionId)}`;

    const sock = new WebSocket(wsUrl);
    ws = sock;

    sock.onopen = () => {
      if (sock !== ws) return;
      status = 'connected';
    };
    sock.onclose = () => {
      if (sock !== ws) return;
      status = 'disconnected';
      stopAndClearAudioQueue();
    };

    sock.onerror = () => {
      if (sock !== ws) return;
      status = 'disconnected';
      stopAndClearAudioQueue();
    };
    sock.onmessage = (ev) => {
      // Drop messages from stale sockets.
      if (sock !== ws) return;

      try {
        const msg = JSON.parse(ev.data);

        // Only show meta/tool/handoff events for the active session.
        // This is a UI safety net; backend should already scope events.
        const msgSid = typeof msg.session_id === 'string' ? msg.session_id : null;
        if (msgSid && activeSessionId && msgSid !== activeSessionId) {
          return;
        }

        if (msg.type === 'meta' && msg.event === 'ws_bound' && typeof msg.session_id === 'string') {
          wsSessionId = msg.session_id;
          if (msg.session_id !== sessionId) {
            status = 'disconnected';
            try {
              sock.close();
            } catch {
              // ignore
            }
            if (ws === sock) ws = null;
            return;
          }

          // Flush queued message after socket is bound.
          if (queuedText) {
            const t = queuedText;
            queuedText = null;

            const id = newId();
            messages = [...messages, { role: 'user', id, status: 'pending', text: t }];
            sock.send(JSON.stringify({ type: 'user_message', message_id: id, text: t }));
          }

          // Flush queued voice payload after socket is bound.
          // Flush queued voice output toggle after socket is bound.
          if (queuedVoiceOutputEnabled !== null) {
            const enabled = queuedVoiceOutputEnabled;
            queuedVoiceOutputEnabled = null;
            try {
              sock.send(
                JSON.stringify({ type: 'voice_output_toggle', session_id: activeSessionId, enabled })
              );
            } catch {
              // ignore
            }
          }

          if (queuedVoicePayload) {
            const payload = queuedVoicePayload;
            queuedVoicePayload = null;
            try {
              sock.send(JSON.stringify(payload));
            } catch {
              // ignore
            }
          }
          return;
        }

        if (msg.type === 'meta' && msg.event === 'voice_output' && typeof msg.enabled === 'boolean') {
          voiceOutputEnabled = msg.enabled;
          return;
        }

        if (msg.type === 'tts_audio_segment') {
          const seq = typeof msg.seq === 'number' ? msg.seq : null;
          const replyTo = typeof msg.reply_to === 'string' ? msg.reply_to : null;
          const audioB64 = typeof msg.audio_b64 === 'string' ? msg.audio_b64 : '';
          const mime = typeof msg.mime === 'string' ? msg.mime : 'audio/mpeg';

          if (!voiceOutputEnabled) return;
          if (!audioB64) return;

          const url = b64ToBlobUrl(audioB64, mime);
          if (!url) return;

          audioQueue = [...audioQueue, { seq: seq ?? 0, url, reply_to: replyTo }];
          playNextAudio();
          return;
        }

        if (msg.type === 'tts_done') {
          playNextAudio();
          return;
        }

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

        if (msg.type === 'assistant_text_delta' && typeof msg.delta === 'string') {
          const delta = msg.delta;
          const replyTo = typeof msg.reply_to === 'string' ? msg.reply_to : null;
          if (!delta || !replyTo) return;

          // Append streaming delta to the assistant bubble bound to reply_to.
          const idx = messages.findIndex((m) => m.role === 'assistant' && m.reply_to === replyTo);
          if (idx >= 0) {
            const m = messages[idx];
            messages = [...messages.slice(0, idx), { ...m, text: m.text + delta }, ...messages.slice(idx + 1)];
            return;
          }

          // First delta: create the assistant bubble.
          messages = [...messages, { role: 'assistant', reply_to: replyTo, text: delta }];
          return;
        }

        if (msg.type === 'assistant_message' && typeof msg.text === 'string') {
          const replyTo = typeof msg.reply_to === 'string' ? msg.reply_to : null;
          if (!replyTo) {
            messages = [...messages, { role: 'assistant', text: msg.text }];
            return;
          }

          const idx = messages.findIndex((m) => m.role === 'assistant' && m.reply_to === replyTo);
          if (idx >= 0) {
            const m = messages[idx];
            messages = [...messages.slice(0, idx), { ...m, text: msg.text }, ...messages.slice(idx + 1)];
            return;
          }

          messages = [...messages, { role: 'assistant', reply_to: replyTo, text: msg.text }];
          return;
        }

        if (msg.type === 'transcript_final' && typeof msg.message_id === 'string' && typeof msg.text === 'string') {
          // Replace placeholder user message by message_id.
          messages = messages.map((m) =>
            m.role === 'user' && m.id === msg.message_id ? { ...m, text: msg.text, status: 'sent' } : m
          );
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


  function wsSend(payload: any): void {
    if (!activeSessionId) return;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      messages = [...messages, { role: 'meta', text: '[system] disconnected, cannot send' }];
      return;
    }

    if (wsSessionId !== activeSessionId) {
      messages = [...messages, { role: 'meta', text: '[system] socket not bound, cannot send' }];
      return;
    }

    ws.send(JSON.stringify(payload));
  }

  async function startRecording(): Promise<void> {
    if (isRecording) return;

    recordChunks = [];
    recordStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mr = new MediaRecorder(recordStream);
    recorder = mr;

    mr.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) recordChunks.push(e.data);
    };

    mr.onstop = async () => {
      try {
        const blob = new Blob(recordChunks, { type: mr.mimeType || undefined });
        const mime = blob.type || mr.mimeType || 'application/octet-stream';

        const messageId = newId();
        // Insert placeholder user message.
        messages = [...messages, { role: 'user', id: messageId, status: 'pending', text: '(transcribing...)' }];

        const audio_b64 = await blobToBase64(blob);
        const payload = { type: 'voice_input', session_id: activeSessionId, message_id: messageId, audio_b64, mime };

        // If the socket is not yet bound (e.g. first message after session switch),
        // queue this payload and reconnect.
        if (!ws || ws.readyState !== WebSocket.OPEN || wsSessionId !== activeSessionId) {
          queuedVoicePayload = payload;
          if (activeSessionId) {
            connect(activeSessionId);
          }
        } else {
          wsSend(payload);
        }
      } catch {
        messages = [...messages, { role: 'meta', text: '[system] voice record failed' }];
      } finally {
        // Cleanup stream.
        if (recordStream) {
          for (const t of recordStream.getTracks()) t.stop();
        }
        recordStream = null;
        recorder = null;
        recordChunks = [];
        isRecording = false;
      }
    };

    mr.start();
    isRecording = true;
  }

  function stopRecording(): void {
    if (!isRecording) return;
    try {
      recorder?.stop();
    } catch {
      // ignore
    }
  }

  async function toggleRecording(): Promise<void> {
    if (isRecording) {
      stopRecording();
      return;
    }
    try {
      await startRecording();
    } catch {
      messages = [...messages, { role: 'meta', text: '[system] mic permission denied' }];
      isRecording = false;
    }
  }

  function blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('read_failed'));
      reader.onload = () => {
        const s = String(reader.result || '');
        // data:<mime>;base64,<payload>
        const idx = s.indexOf(',');
        resolve(idx >= 0 ? s.slice(idx + 1) : s);
      };
      reader.readAsDataURL(blob);
    });
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
    if (!activeSessionId) return;

    const t = text.trim();
    if (!t) return;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      messages = [...messages, { role: 'meta', text: '[system] disconnected, cannot send' }];
      return;
    }

    if (wsSessionId !== activeSessionId) {
      // Socket not bound yet (or stale). Queue once and reconnect.
      queuedText = t;
      text = '';
      connect(activeSessionId);
      return;
    }

    const id = newId();
    messages = [...messages, { role: 'user', id, status: 'pending', text: t }];
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

        <button
          class={
            voiceOutputEnabled
              ? 'px-3 py-1.5 text-sm rounded-lg border border-gray-900 bg-gray-900 text-white'
              : 'px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50'
          }
          title="Voice output"
          on:click={() => {
            const next = !voiceOutputEnabled;
            voiceOutputEnabled = next;

            if (!activeSessionId) return;

            // If the socket is not yet bound, queue the toggle and (re)connect.
            if (!ws || ws.readyState !== WebSocket.OPEN || wsSessionId !== activeSessionId) {
              queuedVoiceOutputEnabled = next;
              connect(activeSessionId);
              if (!next) stopAndClearAudioQueue();
              return;
            }

            wsSend({ type: 'voice_output_toggle', session_id: activeSessionId, enabled: next });
            if (!next) {
              stopAndClearAudioQueue();
            }
          }}
        >
          {voiceOutputEnabled ? 'Speaker:On' : 'Speaker:Off'}
        </button>

      <div class="text-base text-gray-500">{status}</div>
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
          rows={Math.min(10, Math.max(3, text.split('\n').length))}
          placeholder="Type a message..."
          bind:value={text}
          on:keydown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        ></textarea>
        <button
          class={
            isRecording
              ? 'px-4 py-2 text-base rounded-xl border border-red-700 bg-red-700 text-white'
              : 'px-4 py-2 text-base rounded-xl border border-gray-300 bg-white text-gray-900'
          }
          on:click={() => toggleRecording()}
          title="Voice input"
        >
          {isRecording ? 'Stop' : 'Voice'}
        </button>
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
