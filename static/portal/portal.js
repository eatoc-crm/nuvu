(function () {
  const cfg = window.PORTAL_CONFIG || {};
  const qs = (sel, el) => (el || document).querySelector(sel);
  const isStaffView = !!cfg.staffView;

  let state = {
    form: null,
    flat: [],
    responsesByKey: {},
    currentIndex: 0,
    messages: [],
    portalAiEnabled: true,
    saving: false,
    sending: false,
    lastAssistant: "",
    boolValue: null,
    multiValues: [],
  };

  function toast(msg) {
    const t = qs("#toast");
    t.textContent = msg;
    t.classList.remove("portal-hidden");
    clearTimeout(t._h);
    t._h = setTimeout(() => t.classList.add("portal-hidden"), 4200);
  }

  function flattenForm(form) {
    const out = [];
    (form.sections || []).forEach((sec) => {
      (sec.questions || []).forEach((q) => {
        out.push({
          sectionKey: sec.key,
          sectionTitle: sec.title,
          question: q,
        });
      });
    });
    return out;
  }

  function responseFor(sk, qk) {
    return state.responsesByKey[`${sk}::${qk}`];
  }

  function indexResponses(rows) {
    const m = {};
    (rows || []).forEach((r) => {
      m[`${r.section_key}::${r.question_key}`] = r;
    });
    return m;
  }

  function firstOpenIndex() {
    for (let i = 0; i < state.flat.length; i++) {
      const { sectionKey, question } = state.flat[i];
      const r = responseFor(sectionKey, question.key);
      if (!r || (r.status !== "answered" && r.status !== "skipped")) return i;
    }
    return state.flat.length;
  }

  function sectionStatus(sec) {
    const qs = sec.questions || [];
    let done = 0;
    let hasCurrent = false;
    qs.forEach((q) => {
      const r = responseFor(sec.key, q.key);
      if (r && (r.status === "answered" || r.status === "skipped")) done++;
    });
    const allDone = qs.length && done === qs.length;
    qs.forEach((q) => {
      const item = state.flat[state.currentIndex];
      if (item && item.sectionKey === sec.key && item.question.key === q.key) hasCurrent = true;
    });
    return { allDone, hasCurrent };
  }

  function renderNav() {
    const nav = qs("#sectionNav");
    nav.innerHTML = "";
    (state.form.sections || []).forEach((sec) => {
      const { allDone, hasCurrent } = sectionStatus(sec);
      const row = document.createElement("div");
      row.className = "portal-sec-row" + (hasCurrent ? " current" : "");
      const ic = document.createElement("span");
      ic.className = "portal-sec-ic" + (allDone ? " done" : hasCurrent ? " progress" : "");
      const lab = document.createElement("div");
      lab.textContent = sec.title;
      row.appendChild(ic);
      row.appendChild(lab);
      nav.appendChild(row);
    });
  }

  function renderProgress(answered, total) {
    qs("#progressLabel").textContent = `${answered} of ${total} questions completed`;
    const pct = total ? Math.round((answered / total) * 100) : 0;
    qs("#progressFill").style.width = pct + "%";
  }

  function appendMessage(role, text) {
    const wrap = qs("#messages");
    const div = document.createElement("div");
    div.className = "portal-msg " + (role === "user" ? "user" : "ai");
    div.textContent = text;
    wrap.appendChild(div);
    wrap.scrollTop = wrap.scrollHeight;
  }

  function clearMessages() {
    qs("#messages").innerHTML = "";
  }

  function renderDirectField(q) {
    const host = qs("#directFields");
    host.innerHTML = "";
    state.boolValue = null;
    state.multiValues = [];

    const wrap = (html) => {
      host.innerHTML = html;
    };

    if (q.type === "boolean") {
      const row = document.createElement("div");
      row.className = "bool-row";
      ["Yes", "No", "Not known"].forEach((lab) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = lab;
        b.addEventListener("click", () => {
          row.querySelectorAll("button").forEach((x) => x.classList.remove("selected"));
          b.classList.add("selected");
          state.boolValue = lab === "Yes" ? true : lab === "No" ? false : null;
        });
        row.appendChild(b);
      });
      host.appendChild(row);
      return;
    }

    if (q.type === "select") {
      const sel = document.createElement("select");
      sel.id = "directSelect";
      (q.options || []).forEach((opt) => {
        const o = document.createElement("option");
        o.value = opt;
        o.textContent = opt;
        sel.appendChild(o);
      });
      host.appendChild(sel);
      return;
    }

    if (q.type === "multi_select") {
      (q.options || []).forEach((opt) => {
        const d = document.createElement("div");
        d.className = "multi-opt";
        const id = "cb_" + opt.replace(/\W+/g, "_");
        d.innerHTML = `<input type="checkbox" id="${id}" value="${opt.replace(/"/g, "&quot;")}"> <label for="${id}">${opt}</label>`;
        host.appendChild(d);
      });
      return;
    }

    if (q.type === "date") {
      wrap(`<input type="date" id="directDate" />`);
      return;
    }

    if (q.type === "text") {
      wrap(`<input type="text" id="directText" />`);
      return;
    }

    wrap(`<textarea id="directTextarea" rows="5"></textarea>`);
  }

  function collectAnswerFromDirect(q) {
    if (q.type === "boolean") {
      if (state.boolValue === null) return { value: null };
      return { value: state.boolValue };
    }
    if (q.type === "select") {
      const el = qs("#directSelect");
      return { value: el ? el.value : "" };
    }
    if (q.type === "multi_select") {
      const vals = [];
      qs("#directFields")
        .querySelectorAll("input[type=checkbox]")
        .forEach((c) => {
          if (c.checked) vals.push(c.value);
        });
      return { values: vals };
    }
    if (q.type === "date") {
      const el = qs("#directDate");
      return { value: el ? el.value : "" };
    }
    if (q.type === "text") {
      const el = qs("#directText");
      return { value: el ? el.value.trim() : "" };
    }
    const el = qs("#directTextarea");
    return { value: el ? el.value.trim() : "" };
  }

  function setViewMode(ai) {
    qs("#aiChatWrap").classList.toggle("portal-hidden", !ai);
    qs("#directWrap").classList.toggle("portal-hidden", ai);
  }

  async function loadState() {
    qs("#loadingState").classList.remove("portal-hidden");
    qs("#errorState").classList.add("portal-hidden");
    qs("#activeState").classList.add("portal-hidden");
    qs("#completeState").classList.add("portal-hidden");
    const url =
      cfg.formStateUrl +
      "?session_id=" +
      encodeURIComponent(cfg.sessionId) +
      "&form=" +
      encodeURIComponent(cfg.formType);
    const res = await fetch(url);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      qs("#errorText").textContent = data.error || "Could not load form.";
      qs("#loadingState").classList.add("portal-hidden");
      qs("#errorState").classList.remove("portal-hidden");
      return;
    }
    state.form = data.form;
    state.flat = flattenForm(data.form);
    state.responsesByKey = indexResponses(data.responses);
    state.portalAiEnabled = data.portal_ai_enabled !== false;
    state.currentIndex = firstOpenIndex();
    const titleEl = qs("#formTitleLabel");
    if (titleEl) titleEl.textContent = data.form.title || "Property form";
    cfg.portalAiEnabled = state.portalAiEnabled;
    qs("#loadingState").classList.add("portal-hidden");
    if (state.currentIndex >= state.flat.length) {
      qs("#completeState").classList.remove("portal-hidden");
      renderProgress(data.progress.answered, data.progress.total);
      return;
    }
    qs("#activeState").classList.remove("portal-hidden");
    renderProgress(data.progress.answered, data.progress.total);
    openQuestion(state.currentIndex);
    renderReview();
  }

  async function maybeOpeningChat() {
    if (isStaffView) return;
    if (!state.portalAiEnabled || state.messages.length) return;
    const item = state.flat[state.currentIndex];
    state.sending = true;
    qs("#sendBtn").disabled = true;
    const starter = [
      {
        role: "user",
        content:
          "I am ready to work on this question. Please briefly explain what you need from me in plain English, then guide me step by step.",
      },
    ];
    try {
      const res = await fetch(cfg.chatUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: cfg.sessionId,
          form_type: cfg.formType,
          section_key: item.sectionKey,
          question_key: item.question.key,
          messages: starter,
        }),
      });
      const data = await res.json();
      if (data.messages) state.messages = data.messages;
      if (data.reply) {
        state.lastAssistant = data.reply;
        appendMessage("assistant", data.reply);
        qs("#useSummaryBtn").classList.remove("portal-hidden");
      }
    } catch (e) {
      appendMessage(
        "assistant",
        "We could not reach the assistant just now. You can still type your answer below and save."
      );
    } finally {
      state.sending = false;
      qs("#sendBtn").disabled = false;
    }
  }

  function openQuestion(index) {
    if (index < 0 || index >= state.flat.length) return;
    state.currentIndex = index;
    const item = state.flat[index];
    const q = item.question;
    qs("#questionTitle").textContent = q.text || "";
    qs("#questionHelp").textContent = q.help || "";
    qs("#answerDraft").value = "";
    clearMessages();
    state.messages = [];
    const existing = responseFor(item.sectionKey, q.key);
    if (existing && existing.ai_conversation) {
      try {
        const hist =
          typeof existing.ai_conversation === "string"
            ? JSON.parse(existing.ai_conversation)
            : existing.ai_conversation;
        if (Array.isArray(hist)) {
          state.messages = hist;
          hist.forEach((m) => appendMessage(m.role === "user" ? "user" : "assistant", m.content));
        }
      } catch (_) {}
    }
    setViewMode(state.portalAiEnabled);
    if (!state.portalAiEnabled) {
      renderDirectField(q);
      if (existing && existing.answer) {
        const a = existing.answer;
        if (q.type === "textarea" || q.type === "text")
          qs("#directTextarea") && (qs("#directTextarea").value = a.value || "");
      }
    } else {
      maybeOpeningChat();
    }
    renderNav();
  }

  async function sendChat() {
    if (isStaffView) return;
    const item = state.flat[state.currentIndex];
    const text = (qs("#chatInput").value || "").trim();
    if (!text || state.sending) return;
    appendMessage("user", text);
    qs("#chatInput").value = "";
    state.messages.push({ role: "user", content: text });
    state.sending = true;
    qs("#sendBtn").disabled = true;
    try {
      const res = await fetch(cfg.chatUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: cfg.sessionId,
          form_type: cfg.formType,
          section_key: item.sectionKey,
          question_key: item.question.key,
          messages: state.messages,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Chat failed");
      if (data.messages) state.messages = data.messages;
      if (data.reply) {
        state.lastAssistant = data.reply;
        appendMessage("assistant", data.reply);
        qs("#useSummaryBtn").classList.remove("portal-hidden");
      }
    } catch (e) {
      toast("Something went wrong — your earlier answers are still saved. Try again.");
    } finally {
      state.sending = false;
      qs("#sendBtn").disabled = false;
    }
  }

  async function saveAnswer(skipped) {
    if (isStaffView) return;
    const item = state.flat[state.currentIndex];
    const q = item.question;
    let answer = null;
    if (!skipped) {
      if (state.portalAiEnabled) {
        const draft = (qs("#answerDraft").value || "").trim();
        if (!draft) {
          toast("Please enter your answer, or skip the question.");
          return;
        }
        answer = { value: draft };
      } else {
        answer = collectAnswerFromDirect(q);
      }
    }
    state.saving = true;
    qs("#saveBtn").disabled = true;
    try {
      const res = await fetch(cfg.saveUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: cfg.sessionId,
          form_type: cfg.formType,
          section_key: item.sectionKey,
          question_key: q.key,
          status: skipped ? "skipped" : "answered",
          answer: skipped ? null : answer,
          messages: state.portalAiEnabled ? state.messages : null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Save failed");
      toast(skipped ? "Question skipped." : "Saved.");
      await loadState();
    } catch (e) {
      toast("Could not save. Check your connection and try again.");
    } finally {
      state.saving = false;
      qs("#saveBtn").disabled = false;
    }
  }

  function renderReview() {
    const ul = qs("#reviewList");
    ul.innerHTML = "";
    state.flat.forEach((item, idx) => {
      const r = responseFor(item.sectionKey, item.question.key);
      if (!r || r.status !== "answered") return;
      const li = document.createElement("li");
      const sn = document.createElement("div");
      sn.className = "portal-review-snippet";
      const ans = r.answer && r.answer.value !== undefined ? String(r.answer.value) : JSON.stringify(r.answer || {});
      sn.textContent = (item.question.text || "").slice(0, 72) + " — " + ans.slice(0, 80);
      const actions = document.createElement("div");
      actions.className = "portal-review-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "portal-btn secondary";
      edit.textContent = "Edit";
      edit.addEventListener("click", () => {
        state.currentIndex = idx;
        openQuestion(idx);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      actions.appendChild(edit);
      li.appendChild(sn);
      li.appendChild(actions);
      ul.appendChild(li);
    });
  }

  qs("#sendBtn").addEventListener("click", sendChat);
  qs("#chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });
  qs("#saveBtn").addEventListener("click", () => saveAnswer(false));
  qs("#skipBtn").addEventListener("click", () => saveAnswer(true));
  qs("#retryBtn").addEventListener("click", loadState);
  qs("#useSummaryBtn").addEventListener("click", () => {
    if (state.lastAssistant) qs("#answerDraft").value = state.lastAssistant;
  });
  qs("#sectionToggle").addEventListener("click", () => {
    const inner = qs("#sidebarInner");
    const open = inner.classList.toggle("open");
    qs("#sectionToggle").setAttribute("aria-expanded", open ? "true" : "false");
  });

  if (isStaffView) {
    ["#sendBtn", "#chatInput", "#saveBtn", "#skipBtn", "#answerDraft", "#useSummaryBtn"].forEach((sel) => {
      const el = qs(sel);
      if (el) el.disabled = true;
    });
  }

  loadState();
})();
