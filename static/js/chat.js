document.addEventListener("DOMContentLoaded", () => {
  let currentChatId = null;
  let isLoading = false;

  if (!window.API) {
    console.error("[Chatbot] Required dependencies not loaded.");
    return;
  }

  function getLang() {
    return (window.I18n && window.I18n.current) ? window.I18n.current : (localStorage.getItem("lang") || "en");
  }

  async function loadUserInfo() {
    try {
      const data = await window.API.get("/auth/me");
      const userInfoDiv = document.getElementById("userInfo");
      if (userInfoDiv) userInfoDiv.textContent = data.user.username;

      if (data.user.university_id) {
        try {
          const univData = await window.API.get("/auth/universities");
          const university = univData.universities.find(u => u.id === data.user.university_id);
          if (university) {
            const nameDiv = document.getElementById("universityName");
            if (nameDiv) {
              nameDiv.removeAttribute("data-i18n");
              const applyName = () => {
                const l = getLang();
                const brandText = nameDiv.querySelector('.brand-text');
                const name = (l === "ar" && university.name_ar) ? university.name_ar : university.name;
                if (brandText) brandText.textContent = name;
                else nameDiv.textContent = name;
              };
              applyName();
              window.addEventListener("langChanged", applyName);
            }
          }
        } catch (e) { console.error("[Chatbot] Failed to load university:", e); }
      }
    } catch (e) { console.error("[Chatbot] Failed to load user info:", e); }
  }

  async function loadChatList() {
    try {
      const data = await window.API.get("/chat/list");
      const chatList = document.getElementById("chatList");
      if (data.chats.length === 0) {
        chatList.innerHTML = `<p style="padding:12px;color:var(--text-secondary);font-size:14px;">${getLang() === "ar" ? "لا توجد محادثات بعد" : "No chats yet"}</p>`;
        return;
      }
      chatList.innerHTML = data.chats.map(chat => {
        let timeStr = "";
        if (chat.updated_at) {
          const d = new Date(chat.updated_at);
          timeStr = d.toLocaleString(getLang() === 'ar' ? 'ar-EG' : 'en-US', {
            hour: 'numeric', minute: 'numeric', day: 'numeric', month: 'short'
          });
        }
        return `
        <div class="chat-item" data-chat-id="${chat.id}">
          <div style="flex:1; overflow:hidden;">
            <div class="chat-item-title">${chat.title}</div>
            <div class="chat-item-time" style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">${timeStr}</div>
          </div>
          <button class="delete-chat-btn" data-chat-id="${chat.id}" title="${getLang() === 'ar' ? 'حذف المحادثة' : 'Delete chat'}" style="background:transparent; border:none; color:var(--text-tertiary); cursor:pointer; padding:4px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
            </svg>
          </button>
        </div>`;
      }).join("");

      document.querySelectorAll(".chat-item").forEach(item => {
        item.addEventListener("click", () => loadChat(Number.parseInt(item.dataset.chatId)));
      });

      document.querySelectorAll(".delete-chat-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const confirmMsg = getLang() === 'ar' ? 'هل أنت متأكد من حذف هذه المحادثة؟' : 'Are you sure you want to delete this chat?';
          const confirmed = await UIDialogs.confirm(confirmMsg, { danger: true });
          if (confirmed) {
            try {
              const res = await fetch(`/chat/${btn.dataset.chatId}`, { method: 'DELETE' });
              if (res.ok) {
                if (currentChatId === Number.parseInt(btn.dataset.chatId)) {
                  currentChatId = null;
                  showWelcomeScreen();
                }
                loadChatList();
              }
            } catch (err) { console.error("Failed to delete", err); }
          }
        });
      });

    } catch (e) { console.error("[Chatbot] Failed to load chats:", e); }
  }

  const FAQ_QUESTIONS = {
    en: [
      "What are the registration requirements?",
      "When does the academic year start?",
      "How can I contact my department?",
      "What scholarships are available?",
      "How do I access the student portal?",
      "What are the library opening hours?"
    ],
    ar: [
      "ما هي متطلبات التسجيل؟",
      "متى يبدأ العام الدراسي؟",
      "كيف يمكنني التواصل مع قسمي؟",
      "ما هي المنح الدراسية المتاحة؟",
      "كيف أدخل إلى بوابة الطالب؟",
      "ما هي أوقات عمل المكتبة؟"
    ]
  };

  function renderWelcomeScreen() {
    const lang = getLang();
    const questions = FAQ_QUESTIONS[lang] || FAQ_QUESTIONS.en;
    const t = window.I18n ? window.I18n.t.bind(window.I18n) : (k => k);
    return `
      <div class="welcome-message">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
            <path d="M6 12v5c0 1.657 2.686 3 6 3s6-1.343 6-3v-5"/>
          </svg>
        </div>
        <h2>${t("chat.welcome_title")}</h2>
        <p>${t("chat.welcome_sub")}</p>
        <div class="faq-section">
          <p class="faq-section-label">${lang === "ar" ? "أسئلة شائعة" : "Frequently Asked Questions"}</p>
          <div class="faq-cards">
            ${questions.map(q => `<button class="faq-card" data-question="${q}"><span class="faq-icon">💬</span><span>${q}</span></button>`).join("")}
          </div>
        </div>
      </div>`;
  }

  function showWelcomeScreen() {
    const d = document.getElementById("chatMessages");
    if (d) { d.innerHTML = renderWelcomeScreen(); attachFaqCardListeners(); }
  }

  function attachFaqCardListeners() {
    document.querySelectorAll(".faq-card").forEach(card => {
      card.addEventListener("click", () => {
        const q = card.dataset.question;
        if (currentChatId) {
          const inp = document.getElementById("messageInput");
          if (inp) { inp.value = q; }
          sendMessage(q);
        } else {
          createNewChatWithMessage(q);
        }
      });
    });
  }

  function escapeHtml(text) {
    const d = document.createElement('div'); d.textContent = text; return d.innerHTML;
  }

  function formatMessageContent(content) {
    // Code blocks first (protect from other formatting)
    const codeBlocks = [];
    content = content.replace(/```(\w+)?\n?([\s\S]+?)```/g, (_, lang, code) => {
      const idx = codeBlocks.length;
      codeBlocks.push(`<pre><code class="language-${lang || 'plaintext'}">${escapeHtml(code.trim())}</code></pre>`);
      return `%%CODEBLOCK_${idx}%%`;
    });
    const inlineCodes = [];
    content = content.replace(/`([^`]+)`/g, (_, code) => {
      const idx = inlineCodes.length;
      inlineCodes.push(`<code>${escapeHtml(code)}</code>`);
      return `%%INLINECODE_${idx}%%`;
    });

    // Convert headers to bold text (### before ## before #)
    content = content.replace(/^#{1,6}\s+(.+)$/gm, '<strong>$1</strong>');

    // Bold and italic
    content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/\*(.+?)\*/g, '$1');

    // Unordered lists (- item or * item)
    content = content.replace(/^[\-\*]\s+(.+)$/gm, '- $1');

    // Line breaks
    content = content.replace(/\n/g, '<br>');

    // Links
    content = content.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');

    // Restore code blocks
    codeBlocks.forEach((block, i) => { content = content.replace(`%%CODEBLOCK_${i}%%`, block); });
    inlineCodes.forEach((code, i) => { content = content.replace(`%%INLINECODE_${i}%%`, code); });

    return content;
  }

  function createMessageHTML(msg, showActions = true) {
    const lang = getLang();
    const formatted = formatMessageContent(msg.content);
    const actions = showActions && msg.role === 'assistant' ? `
      <div class="message-actions">
        <button class="message-action-btn copy-btn" data-content="${escapeHtml(msg.content)}" title="${lang === "ar" ? "نسخ" : "Copy"}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
      </div>` : '';
    return `<div class="message ${msg.role}" data-message-id="${msg.id || ''}">
      <div class="message-content">${formatted}</div>${actions}</div>`;
  }

  async function loadChat(chatId) {
    try {
      const data = await window.API.get(`/chat/${chatId}`);
      currentChatId = chatId;
      document.getElementById("chatTitle").textContent = data.chat.title;
      document.getElementById("messageInput").disabled = false;
      document.querySelector(".chat-input-form button").disabled = false;
      const md = document.getElementById("chatMessages");
      md.innerHTML = data.messages.map(m => createMessageHTML(m)).join("");
      attachMessageActionListeners();
      if (localStorage.getItem('codeHighlight') !== 'false') highlightCode();
      md.scrollTop = md.scrollHeight;
      document.querySelectorAll(".chat-item").forEach(item =>
        item.classList.toggle("active", Number.parseInt(item.dataset.chatId) === chatId));
    } catch (e) { console.error("[Chatbot] Failed to load chat:", e); }
  }

  function highlightCode() {
    document.querySelectorAll('pre code').forEach(b => b.classList.add('highlighted'));
  }

  function attachMessageActionListeners() {
    document.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.content);
          const orig = btn.innerHTML;
          btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
          btn.classList.add('success');
          setTimeout(() => { btn.innerHTML = orig; btn.classList.remove('success'); }, 2000);
        } catch (e) { console.error('[Chatbot] Copy failed:', e); }
      });
    });
  }

  async function createNewChat() {
    try {
      const placeholder = getLang() === "ar" ? "محادثة جديدة" : "New Chat";
      const data = await window.API.post("/chat/new", { title: placeholder });
      currentChatId = data.chat.id;
      document.getElementById("messageInput").disabled = false;
      document.querySelector(".chat-input-form button").disabled = false;
      document.getElementById("chatTitle").textContent = placeholder;
      showWelcomeScreen();
      await loadChatList();
      document.querySelectorAll(".chat-item").forEach(item =>
        item.classList.toggle("active", Number.parseInt(item.dataset.chatId) === currentChatId));
    } catch (e) { console.error("[Chatbot] Failed to create chat:", e); }
  }

  async function createNewChatWithMessage(message) {
    try {
      const placeholder = getLang() === "ar" ? "محادثة جديدة" : "New Chat";
      const data = await window.API.post("/chat/new", { title: placeholder });
      currentChatId = data.chat.id;
      document.getElementById("messageInput").disabled = false;
      document.querySelector(".chat-input-form button").disabled = false;
      await loadChatList();
      sendMessage(message);
    } catch (e) { console.error("[Chatbot] Failed to create chat:", e); }
  }

  async function sendMessage(message) {
    if (!currentChatId || isLoading) return;
    isLoading = true;
    const md = document.getElementById("chatMessages");
    const inp = document.getElementById("messageInput");

    const welcome = md.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    md.innerHTML += createMessageHTML({ role: 'user', content: message }, false);
    md.scrollTop = md.scrollHeight;
    md.innerHTML += `<div class="message assistant loading"><div class="message-content"><div class="loading-dots"><span></span><span></span><span></span></div></div></div>`;
    md.scrollTop = md.scrollHeight;
    inp.value = "";

    try {
      const data = await window.API.post(`/chat/${currentChatId}/message`, { message, use_faq: true });
      document.querySelector(".message.loading")?.remove();

      let content = data.ai_message.content;
      if (data.confidence !== undefined && data.confidence !== null) {
        const lang = getLang();
        const pct = Math.round(data.confidence * 100);
        const src = data.source || 'ai';
        let badgeText = '';
        if (lang === 'ar') {
          badgeText = src === 'faq' ? `من الأسئلة الشائعة • دقة ${pct}%` : `ذكاء اصطناعي • دقة ${pct}%`;
        } else if (lang === 'fr') {
          badgeText = src === 'faq' ? `FAQ • Confiance ${pct}%` : `IA • Confiance ${pct}%`;
        } else {
          badgeText = src === 'faq' ? `FAQ • Confidence ${pct}%` : `AI • Confidence ${pct}%`;
        }
        let level = 'low';
        if (pct >= 70) level = 'high';
        else if (pct >= 40) level = 'medium';
        content = `<div class="confidence-badge confidence-${level}"><span class="confidence-dot"></span>${badgeText}</div><br>` + content;
      }

      md.innerHTML += createMessageHTML({ id: data.ai_message.id, role: 'assistant', content });
      attachMessageActionListeners();
      if (localStorage.getItem('codeHighlight') !== 'false') highlightCode();
      md.scrollTop = md.scrollHeight;

      if (data.chat_title) document.getElementById("chatTitle").textContent = data.chat_title;

      await loadChatList();
      document.querySelectorAll(".chat-item").forEach(item =>
        item.classList.toggle("active", Number.parseInt(item.dataset.chatId) === currentChatId));
    } catch (e) {
      console.error("[Chatbot] Send failed:", e);
      document.querySelector(".message.loading")?.remove();
      const errMsg = getLang() === "ar" ? "فشل الرد. حاول مجدداً." : "Failed to get response. Please try again.";
      md.innerHTML += `<div class="message assistant"><div class="message-content" style="color:var(--error);">${errMsg}</div></div>`;
    } finally { isLoading = false; }
  }

  document.getElementById("newChatBtn").addEventListener("click", createNewChat);

  document.getElementById("messageForm").addEventListener("submit", e => {
    e.preventDefault();
    const msg = document.getElementById("messageInput").value.trim();
    if (!msg) return;
    if (!currentChatId) createNewChatWithMessage(msg); else sendMessage(msg);
  });

  document.getElementById("messageInput").addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      const msg = e.target.value.trim();
      if (!msg) return;
      if (!currentChatId) createNewChatWithMessage(msg); else sendMessage(msg);
    }
  });

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    try { await window.API.post("/auth/logout"); window.location.href = "/auth/login"; }
    catch (e) { console.error("[Chatbot] Logout failed:", e); }
  });

  const settingsBtn = document.getElementById("settingsBtn");
  const settingsPanel = document.getElementById("settingsPanel");
  const closeSettings = document.getElementById("closeSettings");

  function updateSettingsPanelDir() {
    if (!settingsPanel) return;
    if (getLang() === "ar") {
      settingsPanel.classList.add("rtl-panel");
    } else {
      settingsPanel.classList.remove("rtl-panel");
    }
  }
  updateSettingsPanelDir();
  window.addEventListener("langChanged", updateSettingsPanelDir);

  if (settingsBtn && settingsPanel && closeSettings) {
    settingsBtn.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); settingsPanel.classList.add("active"); loadSettingsData(); });
    closeSettings.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); settingsPanel.classList.remove("active"); });
    document.addEventListener("click", e => {
      if (settingsPanel.classList.contains("active") && !settingsPanel.contains(e.target) && e.target !== settingsBtn)
        settingsPanel.classList.remove("active");
    });
  }

  async function loadSettingsData() {
    try {
      const data = await window.API.get("/auth/me");
      const el = id => document.getElementById(id);
      if (el("profileName")) el("profileName").value = data.user.full_name || "";
      if (el("profileEmail")) el("profileEmail").value = data.user.email || "";
      if (el("profileDepartment")) {
        let deptName = "";
        if (data.user.department && data.user.department.name) deptName = data.user.department.name;
        el("profileDepartment").value = deptName;
      }
      if (el("profileStudentId")) el("profileStudentId").value = data.user.student_id || "";
    } catch (e) { console.error("[Chatbot] Failed to load settings:", e); }
  }

  const saveProfileBtn = document.getElementById("saveProfile");
  if (saveProfileBtn) {
    saveProfileBtn.addEventListener("click", async () => {
      try {
        await window.API.post("/auth/update-profile", {
          full_name: document.getElementById("profileName")?.value,
        });
        UIDialogs.toast(getLang() === "ar" ? "تم تحديث الملف الشخصي!" : "Profile updated successfully!", 'success');
      } catch (e) { UIDialogs.toast(getLang() === "ar" ? "فشل التحديث." : "Failed to update profile.", 'error'); }
    });
  }

  const fontSizeSelect = document.getElementById("fontSize");
  if (fontSizeSelect) {
    fontSizeSelect.addEventListener("change", e => {
      document.body.classList.remove("font-small", "font-medium", "font-large");
      document.body.classList.add(`font-${e.target.value}`);
      localStorage.setItem("fontSize", e.target.value);
    });
    const sz = localStorage.getItem("fontSize") || "medium";
    fontSizeSelect.value = sz; document.body.classList.add(`font-${sz}`);
  }

  const creativitySlider = document.getElementById("creativity");
  const creativityValue = document.getElementById("creativityValue");
  if (creativitySlider && creativityValue) {
    creativitySlider.addEventListener("input", e => { creativityValue.textContent = `${e.target.value}%`; localStorage.setItem("creativity", e.target.value); });
    const sv = localStorage.getItem("creativity") || "70";
    creativitySlider.value = sv; creativityValue.textContent = `${sv}%`;
  }

  const rsSelect = document.getElementById("responseStyle");
  if (rsSelect) { rsSelect.addEventListener("change", e => localStorage.setItem("responseStyle", e.target.value)); rsSelect.value = localStorage.getItem("responseStyle") || "balanced"; }

  ["codeHighlight", "autoSave", "dataCollection"].forEach(id => {
    const t = document.getElementById(id);
    if (t) { const s = localStorage.getItem(id); if (s !== null) t.checked = s === "true"; t.addEventListener("change", e => localStorage.setItem(id, e.target.checked)); }
  });

  document.querySelectorAll(".theme-option").forEach(btn => {
    btn.addEventListener("click", () => {
      const theme = btn.dataset.theme;
      document.body.classList.toggle("light-theme", theme === "light");
      localStorage.setItem("theme", theme);
      document.querySelectorAll(".theme-option").forEach(b => b.classList.toggle("active", b === btn));
    });
    if (btn.dataset.theme === (localStorage.getItem("theme") || "dark")) btn.classList.add("active");
  });



  const clearBtn = document.getElementById("clearHistory");
  if (clearBtn) {
    clearBtn.addEventListener("click", async e => {
      e.preventDefault();
      const confirmMsg = getLang() === "ar" ? "هل أنت متأكد من حذف كل المحادثات؟" : "Delete all chat history? This cannot be undone.";
      const confirmed = await UIDialogs.confirm(confirmMsg, { danger: true });
      if (confirmed) {
        try { await window.API.delete("/chat/clear-all"); window.location.reload(); }
        catch (e) { console.error("[Chatbot] Clear failed:", e); }
      }
    });
  }

  async function initialize() {
    await loadUserInfo();
    await loadChatList();
    showWelcomeScreen();
  }

  initialize();
});


(function () {
  const toggleBtn = document.getElementById('sidebarToggleBtn');
  const closeBtn = document.getElementById('sidebarCloseBtn');
  const sidebar = document.getElementById('chatSidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (!toggleBtn || !sidebar || !overlay) return;
  const open = () => { sidebar.classList.add('active'); overlay.classList.add('active'); document.body.style.overflow = 'hidden'; };
  const close = () => { sidebar.classList.remove('active'); overlay.classList.remove('active'); document.body.style.overflow = ''; };
  toggleBtn.addEventListener('click', open);
  overlay.addEventListener('click', close);
  if (closeBtn) closeBtn.addEventListener('click', close);
  document.addEventListener('click', e => { if (e.target.closest('.chat-item') && window.innerWidth <= 768) close(); });
  window.addEventListener('resize', () => { if (window.innerWidth > 768) close(); });
})();


(function () {
  const userInfo = document.getElementById('userInfo');
  if (!userInfo) return;
  const setInitial = () => {
    const text = userInfo.textContent.trim();
    if (text) userInfo.setAttribute('data-initial', text.replace(/[^a-zA-Z\u0600-\u06FF]/g, '').charAt(0) || '?');
  };
  const obs = new MutationObserver(() => { setInitial(); obs.disconnect(); });
  obs.observe(userInfo, { childList: true, subtree: true, characterData: true });
  setInitial();
})();