/* ============================================================
   Lingua Partner — frontend logic
   ============================================================ */

'use strict';

// ── State ─────────────────────────────────────────────────────
const state = {
  sessionId: crypto.randomUUID(),
  mode: 'conversation',      // 'conversation' | 'correction'
  targetLanguage: 'Spanish',
  nativeLanguage: 'English',
  busy: false,
};

// ── DOM refs ──────────────────────────────────────────────────
const chatContainer  = document.getElementById('chatContainer');
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const newChatBtn     = document.getElementById('newChatBtn');
const grammarBtn     = document.getElementById('grammarBtn');
const grammarPanel   = document.getElementById('grammarPanel');
const grammarResult  = document.getElementById('grammarResult');
const targetLangSel  = document.getElementById('targetLang');
const nativeLangSel  = document.getElementById('nativeLang');
const modeButtons    = document.querySelectorAll('.mode-btn');
const statusDot      = document.getElementById('statusDot');
const statusText     = document.getElementById('statusText');
const topbarTitle    = document.getElementById('topbarTitle');
const topbarSub      = document.getElementById('topbarSub');
const toastContainer = document.getElementById('toastContainer');

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  setInterval(checkHealth, 30_000);
  renderWelcome();
  syncTopbar();

  // Hint chips
  document.querySelectorAll('.hint-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      messageInput.value = chip.dataset.msg;
      messageInput.focus();
      autoResize(messageInput);
    });
  });
});

// ── Language / mode selectors ─────────────────────────────────
targetLangSel.addEventListener('change', () => {
  state.targetLanguage = targetLangSel.value;
  syncTopbar();
});

nativeLangSel.addEventListener('change', () => {
  state.nativeLanguage = nativeLangSel.value;
});

modeButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    modeButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.mode = btn.dataset.mode;
    grammarPanel.classList.remove('open');
    syncTopbar();
  });
});

// ── Topbar sync ───────────────────────────────────────────────
function syncTopbar() {
  const modeLabel = state.mode === 'correction' ? 'Grammar Correction' : 'Conversation Practice';
  topbarTitle.textContent = `${state.targetLanguage} — ${modeLabel}`;
  topbarSub.textContent   = `Session · ${state.sessionId.slice(0, 8)}`;
}

// ── Send message ──────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

messageInput.addEventListener('input', () => autoResize(messageInput));

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || state.busy) return;

  // Hide welcome screen on first message
  const welcome = document.querySelector('.welcome');
  if (welcome) welcome.remove();

  // Close grammar panel
  grammarPanel.classList.remove('open');

  appendMessage('user', text);
  messageInput.value = '';
  autoResize(messageInput);

  const typingId = showTyping();
  setBusy(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id:      state.sessionId,
        message:         text,
        target_language: state.targetLanguage,
        native_language: state.nativeLanguage,
        mode:            state.mode,
      }),
    });

    removeTyping(typingId);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? 'Server error');
    }

    const data = await res.json();
    appendMessage('assistant', data.reply, data.corrections ?? []);

  } catch (err) {
    removeTyping(typingId);
    showToast(err.message, 'error');
  } finally {
    setBusy(false);
  }
}

// ── Grammar check ─────────────────────────────────────────────
grammarBtn.addEventListener('click', async () => {
  const text = messageInput.value.trim();
  if (!text) {
    showToast('Type something in the input box first.', 'error');
    return;
  }
  if (state.busy) return;

  setBusy(true);
  grammarPanel.classList.remove('open');
  grammarResult.innerHTML = '<p style="color:var(--text-muted);font-size:13px">Checking…</p>';
  grammarPanel.classList.add('open');

  try {
    const res = await fetch('/api/grammar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id:      state.sessionId,
        text,
        target_language: state.targetLanguage,
        native_language: state.nativeLanguage,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? 'Server error');
    }

    const data = await res.json();
    renderGrammarResult(data);

  } catch (err) {
    grammarPanel.classList.remove('open');
    showToast(err.message, 'error');
  } finally {
    setBusy(false);
  }
});

function renderGrammarResult(data) {
  const noErrors = data.corrections.length === 0;

  grammarResult.innerHTML = `
    <div class="row">
      <span class="tag original">Original</span>
      <span>${escHtml(data.original)}</span>
    </div>
    <div class="row">
      <span class="tag corrected">Corrected</span>
      <span>${escHtml(data.corrected)}</span>
    </div>
    ${data.corrections.length ? `
    <div class="row" style="flex-direction:column;gap:4px">
      ${data.corrections.map(c => `<span style="font-family:var(--mono);font-size:12px;color:var(--danger)">• ${escHtml(c)}</span>`).join('')}
    </div>` : `<div style="color:var(--success);font-size:13px">✓ No errors found.</div>`}
    ${data.explanation ? `
    <div class="row" style="margin-top:4px">
      <span class="tag explain">Tip</span>
      <span style="color:var(--text-muted)">${escHtml(data.explanation)}</span>
    </div>` : ''}
  `;
}

// ── New chat ──────────────────────────────────────────────────
newChatBtn.addEventListener('click', async () => {
  try {
    await fetch(`/api/chat/${state.sessionId}`, { method: 'DELETE' });
  } catch (_) { /* best-effort */ }

  state.sessionId = crypto.randomUUID();
  chatContainer.innerHTML = '';
  grammarPanel.classList.remove('open');
  renderWelcome();
  syncTopbar();
});

// ── Health check ──────────────────────────────────────────────
async function checkHealth() {
  statusDot.className  = 'status-dot loading';
  statusText.textContent = 'Connecting…';
  try {
    const res  = await fetch('/api/health');
    const data = await res.json();
    if (data.api_reachable) {
      statusDot.className   = 'status-dot ok';
      statusText.textContent = `${data.model} · ready`;
    } else {
      statusDot.className   = 'status-dot error';
      statusText.textContent = 'Gemini API unreachable';
    }
  } catch (_) {
    statusDot.className   = 'status-dot error';
    statusText.textContent = 'Server unreachable';
  }
}

// ── Render helpers ────────────────────────────────────────────
function renderWelcome() {
  const hints = [
    { msg: 'Hola, me llamo Ana. ¿Cómo estás?',   label: '💬  Start a conversation in Spanish' },
    { msg: 'Ich möchte ein Buch kaufen.',          label: '✏️  Check my German sentence' },
    { msg: 'Tell me about the weather today.',     label: '🌤  Practice everyday vocabulary' },
    { msg: 'Puedo ir al mercado mañana.',          label: '🛒  Talk about future plans' },
  ];

  chatContainer.innerHTML = `
    <div class="welcome">
      <div class="welcome-icon">🌍</div>
      <h2>Welcome to Lingua Partner</h2>
      <p>Pick a language, choose a mode, and start practising. Your AI tutor is ready.</p>
      <div class="welcome-hints">
        ${hints.map(h => `<button class="hint-chip" data-msg="${escAttr(h.msg)}">${escHtml(h.label)}</button>`).join('')}
      </div>
    </div>
  `;

  // Re-attach hint handlers after innerHTML replace
  document.querySelectorAll('.hint-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      messageInput.value = chip.dataset.msg;
      messageInput.focus();
      autoResize(messageInput);
    });
  });
}

function appendMessage(role, content, corrections = []) {
  // Remove welcome screen if still visible
  const welcome = document.querySelector('.welcome');
  if (welcome) welcome.remove();

  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  // Split on the translation divider (---) that the bot adds
  let bubbleHTML = '';
  if (role === 'assistant') {
    const parts = content.split(/\n---\n/);
    bubbleHTML = `<div>${formatText(parts[0])}</div>`;
    if (parts[1]) {
      bubbleHTML += `<div class="translation">${formatText(parts[1])}</div>`;
    }
  } else {
    bubbleHTML = `<div>${escHtml(content)}</div>`;
  }

  // Correction chips
  const correctionHTML = corrections.length
    ? `<div class="corrections">${corrections.map(c => `<span class="correction-chip">${escHtml(c)}</span>`).join('')}</div>`
    : '';

  msg.innerHTML = `
    <div class="avatar">${role === 'user' ? '🧑' : '🤖'}</div>
    <div class="bubble">${bubbleHTML}${correctionHTML}</div>
  `;

  chatContainer.appendChild(msg);
  scrollToBottom();
}

function showTyping() {
  const id = `typing-${Date.now()}`;
  const el = document.createElement('div');
  el.className = 'message assistant typing-indicator';
  el.id = id;
  el.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="bubble">
      <span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </div>`;
  chatContainer.appendChild(el);
  scrollToBottom();
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

// ── Utilities ─────────────────────────────────────────────────
function setBusy(busy) {
  state.busy = busy;
  sendBtn.disabled      = busy;
  messageInput.disabled = busy;
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escAttr(str) {
  return String(str).replace(/"/g, '&quot;');
}

/**
 * Minimal markdown-ish formatting for assistant replies:
 * bold (**text**), italic (*text*), newlines → <br>
 */
function formatText(text) {
  return escHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/`(.+?)`/g,       '<code style="font-family:var(--mono);font-size:12px;background:var(--surface-2);padding:1px 5px;border-radius:4px">$1</code>')
    .replace(/\n/g, '<br>');
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}
