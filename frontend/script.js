// ============================================================
// script.js — Vidya AI Tutor frontend logic
//
// Handles:
//   - Sending questions to /api/chat
//   - Rendering user + AI messages
//   - "Explain Simpler" button via /api/simplify
//   - Subject / mode selectors
//   - Chat history (multiple conversations, stored in localStorage)
//   - Auto-resize textarea, keyboard shortcuts
// ============================================================

/* ── Constants ─────────────────────────────────────────────── */
const API_BASE = "http://127.0.0.1:5000/api";  // Change if deployed
const CHATS_STORAGE_KEY = "vidya_chats_v1";

/* ── DOM references ────────────────────────────────────────── */
const messagesEl      = document.getElementById("messages");
const questionInput   = document.getElementById("questionInput");
const sendBtn         = document.getElementById("sendBtn");
const simplifyBtn     = document.getElementById("simplifyBtn");
const subjectSelect   = document.getElementById("subjectSelect");
const modeSelect      = document.getElementById("modeSelect");
const languageSelect  = document.getElementById("languageSelect");
const typingIndicator = document.getElementById("typingIndicator");
const headerSubject   = document.getElementById("headerSubject");
const headerMode      = document.getElementById("headerMode");
const menuBtn         = document.getElementById("menuBtn");
const sidebar         = document.getElementById("sidebar");
const sidebarToggle   = document.getElementById("sidebarToggle");
const overlay         = document.getElementById("overlay");
const newChatBtn      = document.getElementById("newChatBtn");
const chatHistoryList = document.getElementById("chatHistoryList");
const classChips      = document.querySelectorAll(".chip");
const themeToggle     = document.getElementById("themeToggle");
const THEME_KEY       = "vidya_theme";
const blobs           = document.querySelectorAll(".blob");
const settingsBtn      = document.getElementById("settingsBtn");
const settingsOverlay  = document.getElementById("settingsOverlay");
const settingsCloseBtn = document.getElementById("settingsCloseBtn");
const SIDEBAR_KEY      = "vidya_sidebar_collapsed";

let messageCount = 0; // drives the staggered pop-in delay on new bubbles

/* ── App state ─────────────────────────────────────────────── */
let lastAIAnswer  = "";   // used by "Explain Simpler"
let isLoading     = false;

// All saved conversations, newest first. Persisted to localStorage.
let chats = loadChats();
// The conversation currently shown in the main view. `null` id means it
// hasn't been saved to `chats` yet (happens once the first message is sent).
let currentChat = makeBlankChat();

// Conversation memory: sent back to the backend on every /api/chat call so
// Gemini knows what was already discussed (follow-up questions, "explain more", etc.)
const MAX_HISTORY_TURNS = 12; // 6 user+ai pairs
let conversationHistory = [];

function pushHistory(role, text) {
  conversationHistory.push({ role, text });
  if (conversationHistory.length > MAX_HISTORY_TURNS) {
    conversationHistory = conversationHistory.slice(-MAX_HISTORY_TURNS);
  }
}

/* ── Chat history persistence ─────────────────────────────── */
function loadChats() {
  try {
    const raw = localStorage.getItem(CHATS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveChats() {
  localStorage.setItem(CHATS_STORAGE_KEY, JSON.stringify(chats));
}

function getSelectedClass() {
  const active = document.querySelector(".chip.active");
  return active ? active.dataset.class : "9";
}

function setSelectedClass(classValue) {
  classChips.forEach(chip => {
    chip.classList.toggle("active", chip.dataset.class === classValue);
  });
}

function makeBlankChat() {
  return {
    id: null,
    title: "New chat",
    subject: "science",
    mode: "easy",
    language: "english",
    studentClass: getSelectedClass(),
    messages: [],   // [{ role, text, isError }]
    history: [],    // conversationHistory snapshot
    updatedAt: Date.now()
  };
}

function makeChatTitle(question) {
  const trimmed = question.trim();
  return trimmed.length > 40 ? trimmed.slice(0, 40) + "…" : trimmed;
}

function renderHistoryList() {
  chatHistoryList.innerHTML = "";

  if (chats.length === 0) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.id = "historyEmpty";
    empty.textContent = "No previous chats yet.";
    chatHistoryList.appendChild(empty);
    return;
  }

  chats.forEach(chat => {
    const item = document.createElement("div");
    item.className = "history-item" + (chat.id === currentChat.id ? " active" : "");
    item.dataset.id = chat.id;
    item.setAttribute("role", "button");
    item.setAttribute("tabindex", "0");
    item.innerHTML = `
      <span class="history-item-title">${escapeHtml(chat.title)}</span>
      <button class="history-delete-btn" data-id="${chat.id}" aria-label="Delete this chat" title="Delete chat">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 6h12M8 6V4.5a1 1 0 011-1h2a1 1 0 011 1V6m-7 0 .6 9.4a1.5 1.5 0 001.5 1.4h4.8a1.5 1.5 0 001.5-1.4L15 6"/>
        </svg>
      </button>
    `;
    chatHistoryList.appendChild(item);
  });
}

/* Persist the current chat into `chats`, creating it if this is its first message. */
function persistCurrentChat() {
  currentChat.updatedAt = Date.now();

  if (currentChat.id === null) {
    currentChat.id = `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    chats.unshift(currentChat);
  } else {
    // Move to top (most recently active) and make sure the stored copy is fresh.
    chats = chats.filter(c => c.id !== currentChat.id);
    chats.unshift(currentChat);
  }

  saveChats();
  renderHistoryList();
}

/* Switch the main view to a different saved chat. */
function openChat(chatId) {
  const chat = chats.find(c => c.id === chatId);
  if (!chat) return;

  currentChat = chat;
  conversationHistory = [...chat.history];
  subjectSelect.value = chat.subject;
  modeSelect.value = chat.mode;
  languageSelect.value = chat.language || "english"; // older saved chats predate this field
  setSelectedClass(chat.studentClass || "9");
  updateHeader();

  messagesEl.innerHTML = "";
  messageCount = 0;
  if (chat.messages.length === 0) {
    showWelcomeCard();
  } else {
    chat.messages.forEach(m => addMessage(m, { skipSave: true }));
  }

  const lastAI = [...chat.messages].reverse().find(m => m.role === "ai" && !m.isError);
  lastAIAnswer = lastAI ? lastAI.text : "";
  simplifyBtn.disabled = !lastAIAnswer;

  renderHistoryList();
  closeSidebar();
}

/* Start a fresh, unsaved conversation. */
function startNewChat() {
  currentChat = makeBlankChat();
  currentChat.subject = subjectSelect.value;
  currentChat.mode = modeSelect.value;
  currentChat.language = languageSelect.value;
  conversationHistory = [];
  lastAIAnswer = "";
  simplifyBtn.disabled = true;

  messagesEl.innerHTML = "";
  messageCount = 0;
  showWelcomeCard();

  renderHistoryList();
  closeSidebar();
  questionInput.focus();
}

/* Delete any saved chat by id. If it's the one currently open, start fresh. */
function deleteChat(chatId) {
  chats = chats.filter(c => c.id !== chatId);
  saveChats();

  if (currentChat.id === chatId) {
    startNewChat();
  } else {
    renderHistoryList();
  }
}

/* ── Utility: get current time string ────────────────────────── */
function nowTime() {
  return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

/* ── Utility: auto-resize textarea as user types ─────────────── */
function autoResize() {
  questionInput.style.height = "auto";
  questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
}

/* ── Utility: scroll chat to bottom ──────────────────────────── */
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

/* ── Utility: format AI response text ────────────────────────── */
// Converts plain text from Gemini into HTML with basic formatting:
// bold (**text**), numbered lists, key points, etc.
function formatAIText(text) {
  // Escape HTML first
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold: **text** or *text*
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Numbered steps: "1." at start of line → styled
  html = html.replace(/^(\d+)\.\s+/gm, (_, n) =>
    `<span style="color:var(--accent-soft-text);font-weight:700;margin-right:6px">${n}.</span>`
  );

  // Bullet lines: "•" or "- " at start of line
  html = html.replace(/^[•\-]\s+/gm,
    `<span style="color:var(--accent-soft-text);font-weight:700;margin-right:6px">▸</span>`
  );

  // Wrap "Key Points:" section
  html = html.replace(/(Key Points?:)/gi,
    `<strong style="color:var(--accent-soft-text);display:block;margin-top:10px;margin-bottom:2px">$1</strong>`
  );

  // Final Answer label
  html = html.replace(/(Final Answer:?)/gi,
    `<strong style="color:var(--accent-soft-text);display:block;margin-top:10px">$1</strong>`
  );

  return html;
}

/* ── Render: add a message bubble to the chat ─────────────────── */
function addMessage({ role, text, isError = false }, { skipSave = false } = {}) {
  // Remove welcome card on first real message
  const card = document.getElementById("welcomeCard");
  if (card) card.remove();

  const isUser = role === "user";
  const avatar = isUser ? "U" : "V";
  const name   = isUser ? "You" : "Vidya";

  const messageEl = document.createElement("div");
  messageEl.className = `message ${role}`;
  messageEl.style.setProperty("--i", messageCount++ % 6); // stagger entrance, cap the delay

  const bubbleContent = isUser
    ? escapeHtml(text)           // user text: plain escaped
    : formatAIText(text);        // AI text: formatted HTML

  messageEl.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">
      <span class="message-name">${name}</span>
      <div class="message-bubble${isError ? " error" : ""}">${bubbleContent}</div>
      <span class="message-time">${nowTime()}</span>
    </div>
  `;

  messagesEl.appendChild(messageEl);
  scrollToBottom();

  if (!skipSave) {
    currentChat.messages.push({ role, text, isError });
  }

  return messageEl;
}

/* ── Show the welcome card (used on new chat / empty chat) ────── */
function showWelcomeCard() {
  const card = document.createElement("div");
  card.className = "welcome-card";
  card.id = "welcomeCard";
  card.innerHTML = `
    <div class="welcome-icon">🌟</div>
    <h2>Vanakkam! I'm Vidya</h2>
    <p>Your AI tutor for Tamil Nadu State Board classes 8–10.<br/>
       Ask me anything about <strong>Maths</strong>, <strong>Science</strong>, or <strong>Social Science</strong>!</p>
    <div class="welcome-chips">
      <span class="welcome-chip">✅ Step-by-step Maths</span>
      <span class="welcome-chip">🔬 Science explained simply</span>
      <span class="welcome-chip">🗺 History as stories</span>
    </div>
  `;
  messagesEl.appendChild(card);
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/* ── Show/hide loading indicator ──────────────────────────────── */
function setLoading(state) {
  isLoading = state;
  typingIndicator.hidden = !state;
  sendBtn.disabled = state;
  questionInput.disabled = state;
  simplifyBtn.disabled = state || !lastAIAnswer;
  if (state) scrollToBottom();
}

/* ── Update header labels when controls change ────────────────── */
function updateHeader() {
  const subjectLabel  = subjectSelect.options[subjectSelect.selectedIndex].text;
  const modeLabel     = modeSelect.options[modeSelect.selectedIndex].text;
  const languageLabel = languageSelect.options[languageSelect.selectedIndex].text;
  headerSubject.textContent = subjectLabel.replace(/^\S+\s+/, "");  // strip emoji
  headerMode.textContent    = `${modeLabel} · ${languageLabel}`;
}

/* ── Main: send question to /api/chat ─────────────────────────── */
async function sendQuestion(question) {
  if (!question || isLoading) return;

  const subject       = subjectSelect.value;
  const mode          = modeSelect.value;
  const language      = languageSelect.value;
  const studentClass  = getSelectedClass();

  // Render user message
  addMessage({ role: "user", text: question });

  // Clear input
  questionInput.value = "";
  questionInput.style.height = "auto";
  sendBtn.disabled = true;

  setLoading(true);

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, subject, mode, language, class: studentClass, history: conversationHistory })
    });

    const data = await response.json();

    if (!response.ok) {
      // API returned an error object
      const errMsg = data.error || "Something went wrong. Please try again.";
      const hint   = data.hint ? `\n\n💡 Hint: ${data.hint}` : "";
      addMessage({ role: "ai", text: errMsg + hint, isError: true });
      lastAIAnswer = "";
    } else {
      lastAIAnswer = data.answer;
      addMessage({ role: "ai", text: data.answer });
      simplifyBtn.disabled = false;
      pushHistory("user", question);
      pushHistory("ai", data.answer);

      if (currentChat.id === null) currentChat.title = makeChatTitle(question);
      currentChat.subject = subject;
      currentChat.mode = mode;
      currentChat.language = language;
      currentChat.studentClass = studentClass;
      currentChat.history = [...conversationHistory];
      persistCurrentChat();
    }

  } catch (err) {
    // Network error — backend not running?
    addMessage({
      role: "ai",
      text: "⚠️ Could not connect to the AI Tutor backend.\n\nMake sure you have:\n1. Installed requirements.txt\n2. Added your Gemini API key to .env\n3. Run build_index.py\n4. Started the Flask server with: python backend/app.py",
      isError: true
    });
    lastAIAnswer = "";
  } finally {
    setLoading(false);
  }
}

/* ── "Explain Simpler" button ─────────────────────────────────── */
async function simplifyLastAnswer() {
  if (!lastAIAnswer || isLoading) return;

  addMessage({ role: "user", text: "✨ Can you explain that in an even simpler way?" });
  setLoading(true);

  try {
    const response = await fetch(`${API_BASE}/simplify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: lastAIAnswer,
        subject: subjectSelect.value,
        language: languageSelect.value
      })
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage({ role: "ai", text: data.error || "Could not simplify.", isError: true });
    } else {
      lastAIAnswer = data.answer;
      addMessage({ role: "ai", text: data.answer });
      pushHistory("user", "Can you explain that in an even simpler way?");
      pushHistory("ai", data.answer);
      currentChat.history = [...conversationHistory];
      persistCurrentChat();
    }

  } catch (err) {
    addMessage({ role: "ai", text: "⚠️ Could not connect to backend.", isError: true });
  } finally {
    setLoading(false);
  }
}

/* ── Sidebar toggle ───────────────────────────────────────────── */
// On mobile the sidebar is an off-canvas overlay (open/close). On desktop
// it's always in-flow, so "toggling" instead retracts/expands its width.
// One button (menuBtn, in the header) drives both, since the header stays
// visible even when the sidebar itself is fully retracted.
function isMobileViewport() {
  return window.matchMedia("(max-width: 768px)").matches;
}

function openSidebar() {
  sidebar.classList.add("open");
  overlay.classList.add("show");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  overlay.classList.remove("show");
}

function toggleSidebar() {
  if (isMobileViewport()) {
    sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
    return;
  }
  const collapsed = sidebar.classList.toggle("collapsed");
  localStorage.setItem(SIDEBAR_KEY, collapsed ? "collapsed" : "expanded");
}

/* ── Settings modal ───────────────────────────────────────────── */
function openSettings() {
  settingsOverlay.hidden = false;
  requestAnimationFrame(() => settingsOverlay.classList.add("show"));
}

function closeSettings() {
  settingsOverlay.classList.remove("show");
  setTimeout(() => { settingsOverlay.hidden = true; }, 200);
}

/* ═══════════════════════════════════════════════════
   EVENT LISTENERS
═══════════════════════════════════════════════════ */

// Enable send button only when input has content
questionInput.addEventListener("input", () => {
  autoResize();
  sendBtn.disabled = questionInput.value.trim().length === 0 || isLoading;
});

// Enter to send (Shift+Enter = new line)
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    const q = questionInput.value.trim();
    if (q) sendQuestion(q);
  }
});

// Send button click
sendBtn.addEventListener("click", () => {
  const q = questionInput.value.trim();
  if (q) sendQuestion(q);
});

// Simplify button
simplifyBtn.addEventListener("click", simplifyLastAnswer);

// Dropdown changes → update header + keep current chat's saved subject/mode in sync
subjectSelect.addEventListener("change", () => {
  updateHeader();
  currentChat.subject = subjectSelect.value;
});
modeSelect.addEventListener("change", () => {
  updateHeader();
  currentChat.mode = modeSelect.value;
});
languageSelect.addEventListener("change", () => {
  updateHeader();
  currentChat.language = languageSelect.value;
});

// New chat button
newChatBtn.addEventListener("click", startNewChat);

// Chat history list — click an item to open it, or its trash icon to delete it
chatHistoryList.addEventListener("click", (e) => {
  const deleteBtn = e.target.closest(".history-delete-btn");
  if (deleteBtn) {
    e.stopPropagation();
    deleteChat(deleteBtn.dataset.id);
    return;
  }
  const item = e.target.closest(".history-item");
  if (!item) return;
  openChat(item.dataset.id);
});

// Keyboard access for history items (they're divs with role="button")
chatHistoryList.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const item = e.target.closest(".history-item");
  if (!item) return;
  e.preventDefault();
  openChat(item.dataset.id);
});

// Class chips — picks which standard's textbook content (and exercises) to use
classChips.forEach(chip => {
  chip.addEventListener("click", () => {
    classChips.forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    currentChat.studentClass = chip.dataset.class;
  });
});

// Sidebar toggle (mobile off-canvas open/close, desktop retract/expand)
menuBtn.addEventListener("click", toggleSidebar);
sidebarToggle.addEventListener("click", closeSidebar);
overlay.addEventListener("click", closeSidebar);

// Settings modal (houses the Class + Language controls)
settingsBtn.addEventListener("click", openSettings);
settingsCloseBtn.addEventListener("click", closeSettings);
settingsOverlay.addEventListener("click", (e) => {
  if (e.target === settingsOverlay) closeSettings();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !settingsOverlay.hidden) closeSettings();
});

// Theme toggle (light/dark) — the actual <html data-theme> is already set
// pre-paint by the inline script in index.html; this just flips + persists it.
// Where supported, wraps the swap in a circular "reveal" View Transition
// centered on the toggle button; falls back to an instant swap otherwise.
themeToggle.addEventListener("click", (e) => {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  const applyTheme = () => {
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
  };

  if (!document.startViewTransition || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    applyTheme();
    return;
  }

  const { clientX: x, clientY: y } = e;
  const radius = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y)
  );

  const transition = document.startViewTransition(applyTheme);
  transition.ready.then(() => {
    document.documentElement.animate(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
      { duration: 550, easing: "cubic-bezier(.22,.61,.36,1)", pseudoElement: "::view-transition-new(root)" }
    );
  });
});

/* ── Ripple micro-interaction on interactive buttons ─────────── */
function attachRipple(el) {
  el.addEventListener("click", (e) => {
    if (el.disabled) return;
    const rect = el.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const ripple = document.createElement("span");
    ripple.className = "ripple";
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
    el.appendChild(ripple);
    ripple.addEventListener("animationend", () => ripple.remove());
  });
}
[sendBtn, newChatBtn, simplifyBtn].forEach(attachRipple);

/* ── Ambient background parallax — blobs drift toward the pointer ──── */
let parallaxRaf = null;
window.addEventListener("pointermove", (e) => {
  if (parallaxRaf) return;
  parallaxRaf = requestAnimationFrame(() => {
    const nx = (e.clientX / window.innerWidth - 0.5) * 2;   // -1..1
    const ny = (e.clientY / window.innerHeight - 0.5) * 2;  // -1..1
    blobs.forEach((blob, i) => {
      const strength = (i + 1) * 10;
      blob.style.setProperty("--px", (nx * strength).toFixed(1));
      blob.style.setProperty("--py", (ny * strength).toFixed(1));
    });
    parallaxRaf = null;
  });
});

/* ── Init ─────────────────────────────────────────────────── */
updateHeader();
renderHistoryList();
questionInput.focus();

// Restore the desktop sidebar's collapsed/expanded state from last session.
if (!isMobileViewport() && localStorage.getItem(SIDEBAR_KEY) === "collapsed") {
  sidebar.classList.add("collapsed");
}
