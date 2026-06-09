// ============================================================
// script.js — Vidya AI Tutor frontend logic
//
// Handles:
//   - Sending questions to /api/chat
//   - Rendering user + AI messages
//   - "Explain Simpler" button via /api/simplify
//   - Subject / mode selectors
//   - Quick starter topics
//   - Auto-resize textarea, keyboard shortcuts
// ============================================================

/* ── Constants ─────────────────────────────────────────────── */
const API_BASE = "http://127.0.0.1:5000/api";  // Change if deployed

/* ── DOM references ────────────────────────────────────────── */
const messagesEl      = document.getElementById("messages");
const questionInput   = document.getElementById("questionInput");
const sendBtn         = document.getElementById("sendBtn");
const simplifyBtn     = document.getElementById("simplifyBtn");
const clearBtn        = document.getElementById("clearBtn");
const subjectSelect   = document.getElementById("subjectSelect");
const modeSelect      = document.getElementById("modeSelect");
const typingIndicator = document.getElementById("typingIndicator");
const welcomeCard     = document.getElementById("welcomeCard");
const headerSubject   = document.getElementById("headerSubject");
const headerMode      = document.getElementById("headerMode");
const menuBtn         = document.getElementById("menuBtn");
const sidebar         = document.getElementById("sidebar");
const sidebarToggle   = document.getElementById("sidebarToggle");
const overlay         = document.getElementById("overlay");

/* ── App state ─────────────────────────────────────────────── */
let lastAIAnswer  = "";   // used by "Explain Simpler"
let isLoading     = false;

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
    `<span style="color:var(--saffron);font-weight:700;margin-right:6px">${n}.</span>`
  );

  // Bullet lines: "•" or "- " at start of line
  html = html.replace(/^[•\-]\s+/gm,
    `<span style="color:var(--teal);font-weight:700;margin-right:6px">▸</span>`
  );

  // Wrap "Key Points:" section
  html = html.replace(/(Key Points?:)/gi,
    `<strong style="color:var(--teal);display:block;margin-top:10px;margin-bottom:2px">$1</strong>`
  );

  // Final Answer label
  html = html.replace(/(Final Answer:?)/gi,
    `<strong style="color:var(--saffron-dk);display:block;margin-top:10px">$1</strong>`
  );

  return html;
}

/* ── Render: add a message bubble to the chat ─────────────────── */
function addMessage({ role, text, isError = false }) {
  // Remove welcome card on first real message
  if (welcomeCard) welcomeCard.remove();

  const isUser = role === "user";
  const avatar = isUser ? "U" : "V";
  const name   = isUser ? "You" : "Vidya";

  const messageEl = document.createElement("div");
  messageEl.className = `message ${role}`;

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
  return messageEl;
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
  const subjectLabel = subjectSelect.options[subjectSelect.selectedIndex].text;
  const modeLabel    = modeSelect.options[modeSelect.selectedIndex].text;
  headerSubject.textContent = subjectLabel.replace(/^\S+\s+/, "");  // strip emoji
  headerMode.textContent    = modeLabel;
}

/* ── Main: send question to /api/chat ─────────────────────────── */
async function sendQuestion(question) {
  if (!question || isLoading) return;

  const subject = subjectSelect.value;
  const mode    = modeSelect.value;

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
      body: JSON.stringify({ question, subject, mode })
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
        subject: subjectSelect.value
      })
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage({ role: "ai", text: data.error || "Could not simplify.", isError: true });
    } else {
      lastAIAnswer = data.answer;
      addMessage({ role: "ai", text: data.answer });
    }

  } catch (err) {
    addMessage({ role: "ai", text: "⚠️ Could not connect to backend.", isError: true });
  } finally {
    setLoading(false);
  }
}

/* ── Clear chat ───────────────────────────────────────────────── */
function clearChat() {
  messagesEl.innerHTML = "";
  lastAIAnswer = "";
  simplifyBtn.disabled = true;

  // Re-add welcome card
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

/* ── Sidebar toggle (mobile) ──────────────────────────────────── */
function openSidebar() {
  sidebar.classList.add("open");
  overlay.classList.add("show");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  overlay.classList.remove("show");
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

// Clear chat
clearBtn.addEventListener("click", clearChat);

// Dropdown changes → update header
subjectSelect.addEventListener("change", updateHeader);
modeSelect.addEventListener("change", updateHeader);

// Quick starter buttons
document.getElementById("starters").addEventListener("click", (e) => {
  const btn = e.target.closest(".starter-btn");
  if (!btn) return;
  const q = btn.dataset.q;
  questionInput.value = q;
  autoResize();
  sendBtn.disabled = false;
  // Auto-set subject based on question content
  if (/photosynthesis|newton|motion/i.test(q)) subjectSelect.value = "science";
  else if (/pythagoras|area|circle/i.test(q)) subjectSelect.value = "maths";
  else if (/revolution|constitution/i.test(q)) subjectSelect.value = "social";
  updateHeader();
  // Close sidebar on mobile
  closeSidebar();
  // Focus input
  questionInput.focus();
});

// Class chips (cosmetic — could be used to tailor prompts in future)
document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
  });
});

// Mobile sidebar
menuBtn.addEventListener("click", openSidebar);
sidebarToggle.addEventListener("click", closeSidebar);
overlay.addEventListener("click", closeSidebar);

/* ── Init ─────────────────────────────────────────────────── */
updateHeader();
questionInput.focus();
