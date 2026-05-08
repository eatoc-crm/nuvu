(function () {
  const cfg = window.PORTAL_CONFIG || {};
  const qs = (sel, el) => (el || document).querySelector(sel);
  const isStaffView = !!cfg.staffView;
  const urlParams = new URLSearchParams(window.location.search);
  const qParam = urlParams.get("q");
  const requestedQuestionIndex =
    qParam != null && /^\d+$/.test(qParam) ? Number(qParam) : null;
  const isEditMode = requestedQuestionIndex != null && !isStaffView;

  const STARTER =
    "I am ready to work on this question. Please briefly explain what you need from me in plain English, then guide me step by step.";

  let state = {
    form: null,
    flat: [],
    responsesByKey: {},
    viewMode: "question",
    questionViewIndex: 0,
    transitionTargetIndex: null,
    transitionFromIndex: null,
    messages: [],
    portalAiEnabled: true,
    saving: false,
    guidanceLoading: false,
    boolValue: undefined,
    multiValues: [],
  };

  function toast(msg) {
    const t = qs("#toast");
    t.textContent = msg;
    t.classList.remove("portal-hidden");
    clearTimeout(t._h);
    t._h = setTimeout(() => t.classList.add("portal-hidden"), 4200);
  }

  function widgetType(q) {
    const t = (q.answer_type || q.type || "textarea").toLowerCase();
    if (t === "boolean") return "yes_no_not_known";
    if (t === "yes_no_not_known" || t === "yes_no") return t;
    if (
      ["text", "textarea", "select", "multi_select", "date"].includes(t)
    ) {
      return t;
    }
    return "textarea";
  }

  function flattenForm(form) {
    const out = [];
    (form.sections || []).forEach((sec) => {
      (sec.questions || []).forEach((q) => {
        out.push({
          sectionKey: sec.key,
          sectionTitle: sec.title,
          sectionDescription: sec.description || "",
          question: q,
        });
      });
    });
    return out;
  }

  function indexResponses(rows) {
    const m = {};
    (rows || []).forEach((r) => {
      m[`${r.section_key}::${r.question_key}`] = r;
    });
    return m;
  }

  function responseFor(sk, qk) {
    return state.responsesByKey[`${sk}::${qk}`];
  }

  function firstOpenIndex() {
    for (let i = 0; i < state.flat.length; i++) {
      const { sectionKey, question } = state.flat[i];
      const r = responseFor(sectionKey, question.key);
      if (!r || (r.status !== "answered" && r.status !== "skipped")) return i;
    }
    return state.flat.length;
  }

  function reviewUrl() {
    if (cfg.reviewUrl) return cfg.reviewUrl;
    const url = new URL("/portal/form/review", window.location.origin);
    url.searchParams.set("session_id", cfg.sessionId || "");
    url.searchParams.set("form", cfg.formType || "ta6");
    return url.toString();
  }

  function goToReview() {
    window.location.href = reviewUrl();
  }

  function completedCount() {
    let n = 0;
    state.flat.forEach(({ sectionKey, question }) => {
      const r = responseFor(sectionKey, question.key);
      if (r && (r.status === "answered" || r.status === "skipped")) n++;
    });
    return n;
  }

  function renderProgress() {
    const total = state.flat.length;
    const done = completedCount();
    qs("#progressLabel").textContent = `${done} of ${total} questions completed`;
    const pct = total ? Math.round((done / total) * 100) : 0;
    qs("#progressFill").style.width = pct + "%";
    const bar = qs(".portal-progress-bar");
    if (bar) {
      bar.setAttribute("aria-valuenow", String(pct));
    }
  }

  function parseConversation(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === "string") {
      try {
        const j = JSON.parse(raw);
        return Array.isArray(j) ? j : [];
      } catch (_) {
        return [];
      }
    }
    return [];
  }

  function lastAssistantText(messages) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].content)
        return messages[i].content;
    }
    return "";
  }

  function mergeResponseLocal(sk, qk, status, answer, aiConv) {
    const key = `${sk}::${qk}`;
    const prev = state.responsesByKey[key] || {};
    state.responsesByKey[key] = {
      ...prev,
      section_key: sk,
      question_key: qk,
      status,
      answer: status === "skipped" ? null : answer,
      ai_conversation: aiConv != null ? aiConv : prev.ai_conversation,
    };
  }

  function renderAnswerField(item) {
    const host = qs("#answerRegion");
    host.innerHTML = "";
    state.boolValue = undefined;
    state.multiValues = [];
    const q = item.question;
    const wt = widgetType(q);
    const existing = responseFor(item.sectionKey, q.key);
    const ans = existing && existing.status === "answered" ? existing.answer : null;

    const addLabel = (text) => {
      const lab = document.createElement("label");
      lab.className = "portal-field-label";
      lab.textContent = text;
      host.appendChild(lab);
    };

    if (wt === "yes_no_not_known") {
      const row = document.createElement("div");
      row.className = "portal-bool-row";
      let v = null;
      if (ans && ans.value !== undefined) v = ans.value;
      ["Yes", "No", "Not known"].forEach((lab) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = lab;
        const val = lab === "Yes" ? true : lab === "No" ? false : null;
        if (v === true && lab === "Yes") b.classList.add("selected");
        if (v === false && lab === "No") b.classList.add("selected");
        if (v === null && lab === "Not known") b.classList.add("selected");
        b.addEventListener("click", () => {
          row.querySelectorAll("button").forEach((x) => x.classList.remove("selected"));
          b.classList.add("selected");
          state.boolValue = val;
        });
        row.appendChild(b);
      });
      host.appendChild(row);
      if (v !== undefined) state.boolValue = v;
      return;
    }

    if (wt === "yes_no") {
      const row = document.createElement("div");
      row.className = "portal-bool-row";
      let v = ans && ans.value !== undefined ? ans.value : undefined;
      ["Yes", "No"].forEach((lab) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = lab;
        const val = lab === "Yes";
        if (v === true && lab === "Yes") b.classList.add("selected");
        if (v === false && lab === "No") b.classList.add("selected");
        b.addEventListener("click", () => {
          row.querySelectorAll("button").forEach((x) => x.classList.remove("selected"));
          b.classList.add("selected");
          state.boolValue = val;
        });
        row.appendChild(b);
      });
      host.appendChild(row);
      if (v !== undefined) state.boolValue = v;
      return;
    }

    if (wt === "select") {
      addLabel("Your answer");
      const sel = document.createElement("select");
      sel.id = "wizSelect";
      (q.options || []).forEach((opt) => {
        const o = document.createElement("option");
        o.value = opt;
        o.textContent = opt;
        sel.appendChild(o);
      });
      if (ans && ans.value != null) sel.value = String(ans.value);
      host.appendChild(sel);
      return;
    }

    if (wt === "multi_select") {
      addLabel("Select all that apply");
      (q.options || []).forEach((opt) => {
        const wrap = document.createElement("div");
        wrap.className = "portal-multi-opt";
        const id = "cb_" + String(opt).replace(/\W+/g, "_");
        const vals = (ans && ans.values) || [];
        const checked = vals.includes(opt);
        wrap.innerHTML = `<input type="checkbox" id="${id}" value="${String(opt)
          .replace(/"/g, "&quot;")
          .replace(/</g, "")}" ${checked ? "checked" : ""}> <label for="${id}">${opt}</label>`;
        host.appendChild(wrap);
      });
      return;
    }

    if (wt === "date") {
      addLabel("Date");
      const inp = document.createElement("input");
      inp.type = "date";
      inp.id = "wizDate";
      if (ans && ans.value) inp.value = String(ans.value);
      host.appendChild(inp);
      return;
    }

    if (wt === "text") {
      addLabel("Your answer");
      const inp = document.createElement("input");
      inp.type = "text";
      inp.id = "wizText";
      if (ans && ans.value != null) inp.value = String(ans.value);
      host.appendChild(inp);
      return;
    }

    addLabel("Your answer");
    const ta = document.createElement("textarea");
    ta.id = "wizTextarea";
    ta.rows = 5;
    if (ans && ans.value != null) ta.value = String(ans.value);
    host.appendChild(ta);
  }

  function isEmptyAnswer(wt, answer) {
    if (wt === "multi_select") return !(answer.values && answer.values.length);
    if (answer && answer.value !== undefined && answer.value !== null)
      return String(answer.value).trim() === "";
    return true;
  }

  function collectAnswer(item) {
    const q = item.question;
    const wt = widgetType(q);
    if (wt === "yes_no_not_known") {
      if (state.boolValue === undefined) return { ok: false, msg: "Please choose Yes, No, or Not known." };
      return { ok: true, answer: { value: state.boolValue } };
    }
    if (wt === "yes_no") {
      if (state.boolValue === undefined) return { ok: false, msg: "Please choose Yes or No." };
      return { ok: true, answer: { value: state.boolValue } };
    }
    if (wt === "select") {
      const el = qs("#wizSelect");
      return { ok: true, answer: { value: el ? el.value : "" } };
    }
    if (wt === "multi_select") {
      const vals = [];
      qs("#answerRegion").querySelectorAll('input[type="checkbox"]').forEach((c) => {
        if (c.checked) vals.push(c.value);
      });
      if (q.required && vals.length === 0)
        return { ok: false, msg: "Please select at least one option." };
      return { ok: true, answer: { values: vals } };
    }
    if (wt === "date") {
      const el = qs("#wizDate");
      const v = el ? el.value.trim() : "";
      if (q.required && !v) return { ok: false, msg: "Please choose a date." };
      return { ok: true, answer: { value: v } };
    }
    if (wt === "text") {
      const el = qs("#wizText");
      const v = el ? el.value.trim() : "";
      if (q.required && !v) return { ok: false, msg: "Please enter an answer." };
      return { ok: true, answer: { value: v } };
    }
    const el = qs("#wizTextarea");
    const v = el ? el.value.trim() : "";
    if (q.required && !v) return { ok: false, msg: "Please enter an answer." };
    return { ok: true, answer: { value: v } };
  }

  function answerIsProvided(item, answer) {
    const wt = widgetType(item.question);
    if (!item.question.required) return true;
    return !isEmptyAnswer(wt, answer);
  }

  function showQuestionWithAnimation(forward) {
    const inner = qs("#cardInner");
    inner.classList.remove("is-enter", "is-leave-forward", "is-leave-back");
    inner.offsetHeight;
    inner.classList.add(forward === false ? "is-leave-back" : "is-leave-forward");
    setTimeout(() => {
      paintQuestionView();
      inner.classList.remove("is-leave-forward", "is-leave-back");
      inner.classList.add("is-enter");
      setTimeout(() => inner.classList.remove("is-enter"), 400);
    }, 160);
  }

  function paintQuestionView() {
    qs("#questionPhase").classList.remove("portal-hidden");
    qs("#transitionPhase").classList.add("portal-hidden");
    qs("#btnTransitionContinue").classList.add("portal-hidden");
    qs("#btnNext").classList.remove("portal-hidden");
    if (!isStaffView) qs("#btnSkip").classList.remove("portal-hidden");
    else qs("#btnSkip").classList.add("portal-hidden");
    state.viewMode = "question";
    const item = state.flat[state.questionViewIndex];
    if (!item) return;
    const q = item.question;
    qs("#questionTitle").textContent = q.text || "";
    const desc = q.description || q.help || "";
    const descEl = qs("#questionDesc");
    if (desc) {
      descEl.textContent = desc;
      descEl.classList.remove("portal-hidden");
    } else {
      descEl.textContent = "";
      descEl.classList.add("portal-hidden");
    }
    renderAnswerField(item);
    renderProgress();
    qs("#btnBack").disabled = state.questionViewIndex <= 0;
    const last = state.questionViewIndex >= state.flat.length - 1;
    if (isStaffView) {
      qs("#btnNext").textContent = last ? "End" : "Next";
    } else if (isEditMode) {
      qs("#btnNext").textContent = "Save changes";
    } else {
      qs("#btnNext").textContent = last ? "Review answers" : "Next";
    }
    loadAiGuidance(item);
  }

  function showTransitionView(targetIdx, fromIdx) {
    state.viewMode = "transition";
    state.transitionTargetIndex = targetIdx;
    state.transitionFromIndex = fromIdx;
    qs("#questionPhase").classList.add("portal-hidden");
    qs("#transitionPhase").classList.remove("portal-hidden");
    qs("#btnSkip").classList.add("portal-hidden");
    qs("#btnNext").classList.add("portal-hidden");
    qs("#btnTransitionContinue").classList.remove("portal-hidden");
    qs("#btnBack").disabled = false;
    const sec = state.flat[targetIdx];
    qs("#transitionKicker").textContent = "You're now in";
    qs("#transitionTitle").textContent = sec.sectionTitle || "Next section";
    const d = sec.sectionDescription || "";
    const de = qs("#transitionDesc");
    if (d) {
      de.textContent = d;
      de.classList.remove("portal-hidden");
    } else {
      de.textContent = "";
      de.classList.add("portal-hidden");
    }
  }

  async function loadAiGuidance(item) {
    const wrap = qs("#aiGuidance");
    const body = qs("#aiGuidanceBody");
    const loadEl = qs("#aiGuidanceLoading");
    if (isStaffView || !state.portalAiEnabled) {
      wrap.classList.add("portal-hidden");
      return;
    }
    wrap.classList.remove("portal-hidden");
    body.classList.add("portal-hidden");
    loadEl.classList.remove("portal-hidden");
    body.textContent = "";

    const row = responseFor(item.sectionKey, item.question.key);
    let messages = parseConversation(row && row.ai_conversation);
    const cached = lastAssistantText(messages);
    if (cached) {
      body.textContent = cached;
      body.classList.remove("portal-hidden");
      loadEl.classList.add("portal-hidden");
      state.messages = messages;
      return;
    }

    if (!messages.length) messages = [{ role: "user", content: STARTER }];
    state.guidanceLoading = true;
    try {
      const res = await fetch(cfg.chatUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: cfg.sessionId,
          form_type: cfg.formType,
          section_key: item.sectionKey,
          question_key: item.question.key,
          messages,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Guidance failed");
      if (data.messages) state.messages = data.messages;
      const reply = lastAssistantText(state.messages) || data.reply || "";
      body.textContent = reply || "No guidance returned — you can still answer below.";
      body.classList.remove("portal-hidden");
    } catch (_) {
      body.textContent =
        "We could not load guidance just now. You can still complete your answer and continue.";
      body.classList.remove("portal-hidden");
    } finally {
      loadEl.classList.add("portal-hidden");
      state.guidanceLoading = false;
    }
  }

  async function persistAnswer(item, skipped, answerOverride) {
    const res = await fetch(cfg.saveUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: cfg.sessionId,
        form_type: cfg.formType,
        section_key: item.sectionKey,
        question_key: item.question.key,
        status: skipped ? "skipped" : "answered",
        answer: skipped ? null : answerOverride,
        messages: state.portalAiEnabled ? state.messages : null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save failed");
    mergeResponseLocal(
      item.sectionKey,
      item.question.key,
      skipped ? "skipped" : "answered",
      skipped ? null : answerOverride,
      state.portalAiEnabled ? state.messages : undefined
    );
    if (data.progress) {
      /* progress derived locally too */
    }
    return data;
  }

  function advanceAfterSave(savedAtIndex, data) {
    renderProgress();
    if (isEditMode || data.complete) {
      goToReview();
      return;
    }
    const next = savedAtIndex + 1;
    if (next >= state.flat.length) {
      goToReview();
      return;
    }
    const curSec = state.flat[savedAtIndex].sectionKey;
    const nextSec = state.flat[next].sectionKey;
    if (nextSec !== curSec) {
      showTransitionView(next, savedAtIndex);
    } else {
      state.questionViewIndex = next;
      showQuestionWithAnimation(true);
    }
  }


  async function onNextClick() {
    if (isStaffView) {
      if (state.viewMode === "transition") return;
      if (state.questionViewIndex >= state.flat.length - 1) return;
      const next = state.questionViewIndex + 1;
      const curSec = state.flat[state.questionViewIndex].sectionKey;
      const nextSec = state.flat[next].sectionKey;
      if (nextSec !== curSec) showTransitionView(next, state.questionViewIndex);
      else {
        state.questionViewIndex = next;
        showQuestionWithAnimation(true);
      }
      return;
    }

    if (state.viewMode === "transition") return;

    const item = state.flat[state.questionViewIndex];
    const collected = collectAnswer(item);
    if (!collected.ok) {
      toast(collected.msg);
      return;
    }
    if (!answerIsProvided(item, collected.answer)) {
      toast("Please enter an answer, or use Skip.");
      return;
    }

    state.saving = true;
    qs("#btnNext").disabled = true;
    qs("#btnSkip").disabled = true;
    try {
      const data = await persistAnswer(item, false, collected.answer);
      toast("Saved.");
      advanceAfterSave(state.questionViewIndex, data);
    } catch (_) {
      toast("Could not save. Check your connection and try again.");
    } finally {
      state.saving = false;
      qs("#btnNext").disabled = false;
      qs("#btnSkip").disabled = false;
    }
  }

  async function onSkipClick() {
    if (isStaffView) return;
    if (state.viewMode === "transition") return;
    const item = state.flat[state.questionViewIndex];
    state.saving = true;
    qs("#btnNext").disabled = true;
    qs("#btnSkip").disabled = true;
    try {
      const data = await persistAnswer(item, true, null);
      toast("Question skipped.");
      advanceAfterSave(state.questionViewIndex, data);
    } catch (_) {
      toast("Could not skip. Try again.");
    } finally {
      state.saving = false;
      qs("#btnNext").disabled = false;
      qs("#btnSkip").disabled = false;
    }
  }

  function onBackClick() {
    if (state.viewMode === "transition") {
      state.questionViewIndex = state.transitionFromIndex != null ? state.transitionFromIndex : 0;
      state.transitionTargetIndex = null;
      state.transitionFromIndex = null;
      showQuestionWithAnimation(false);
      return;
    }
    if (state.questionViewIndex <= 0) return;
    state.questionViewIndex -= 1;
    showQuestionWithAnimation(false);
  }

  function onTransitionContinue() {
    if (state.transitionTargetIndex == null) return;
    state.questionViewIndex = state.transitionTargetIndex;
    state.transitionTargetIndex = null;
    state.transitionFromIndex = null;
    showQuestionWithAnimation(true);
  }

  async function loadState() {
    qs("#loadingState").classList.remove("portal-hidden");
    qs("#errorState").classList.add("portal-hidden");
    qs("#wizardActive").classList.add("portal-hidden");
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
    cfg.portalAiEnabled = state.portalAiEnabled;

    const open = firstOpenIndex();
    qs("#loadingState").classList.add("portal-hidden");
    const hasDeepLink =
      requestedQuestionIndex != null &&
      requestedQuestionIndex >= 0 &&
      requestedQuestionIndex < state.flat.length;
    if (hasDeepLink) {
      state.questionViewIndex = requestedQuestionIndex;
    } else if (open >= state.flat.length) {
      goToReview();
      return;
    } else {
      state.questionViewIndex = open;
    }
    state.viewMode = "question";
    state.transitionTargetIndex = null;
    state.transitionFromIndex = null;
    qs("#wizardActive").classList.remove("portal-hidden");
    paintQuestionView();
    if (isStaffView) qs("#btnNext").disabled = false;
  }

  qs("#btnNext").addEventListener("click", onNextClick);
  qs("#btnSkip").addEventListener("click", onSkipClick);
  qs("#btnBack").addEventListener("click", onBackClick);
  qs("#btnTransitionContinue").addEventListener("click", onTransitionContinue);
  qs("#retryBtn").addEventListener("click", loadState);

  loadState();
})();
