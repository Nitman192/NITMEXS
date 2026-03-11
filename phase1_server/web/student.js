(() => {
  const STUDENT_SESSION_KEY = "nitmexs_student_session";
  const ATTEMPT_CACHE_PREFIX = "nitmexs_attempt_cache_";
  const STUDENT_ONBOARDING_KEY = "nitmexs_student_onboarding_seen";
  const STUDENT_UI_PREFS_KEY = "nitmexs_student_ui_prefs";
  const INACTIVITY_TIMEOUT_MS = 120000;
  const HEARTBEAT_INTERVAL_MS = 15000;
  const BROADCAST_INTERVAL_MS = 10000;
  const ATTEMPT_STATUS_INTERVAL_MS = 5000;

  const st = {
    studentId: "",
    examId: "",
    examName: "",
    attemptId: "",
    sequence: 1,
    totalQuestions: 0,
    currentQuestion: null,
    warningCount: 0,
    finalized: false,
    paused: false,
    syncIntervalId: null,
    attemptStatusTimerId: null,
    warningTimeoutId: null,
    moraleTimerId: null,
    inactivityTimerId: null,
    inactivityModalOpen: false,
    lowTimeAlerted: new Set(),
    paletteFilter: "all",
    heartbeatTimerId: null,
    heartbeatLatencyMs: null,
    broadcastTimerId: null,
    broadcastCursor: null,
    broadcastHistory: [],
    revisionMode: false,
    breathingTimerId: null,
    breathingSecondsLeft: 0,
    autoSubmitInProgress: false,
    receipt: null,
    seenBroadcastIds: new Set(),
    questionTimeBySequence: {},
    questionTimeStartedAt: null,
    answerTimeline: [],
    focusStreak: 0,
    diagnostics: {
      keyboardSeen: false,
      mouseSeen: false,
      lastRunAt: null,
    },
  };

  const $ = (id) => document.getElementById(id);

  const el = {
    version: $("version"),
    sessionStudent: $("session-student"),
    logoutStudent: $("logout-student"),
    openShortcuts: $("open-shortcuts"),
    loadExams: $("load-exams"),
    examSelect: $("exam-select"),
    startAttempt: $("start-attempt"),
    status: $("student-status"),
    attemptMeta: $("attempt-meta"),
    examName: $("exam-name"),
    questionProgress: $("question-progress"),
    questionText: $("question-text"),
    optionsList: $("options-list"),
    markReview: $("mark-review"),
    prevQuestion: $("prev-question"),
    saveNext: $("save-next"),
    reportQuestionIssue: $("report-question-issue"),
    reportTechnicalIssue: $("report-technical-issue"),
    remainingTime: $("remaining-time"),
    moraleTitle: $("morale-title"),
    moraleMessage: $("morale-message"),
    moraleTip: $("morale-tip"),
    refreshMorale: $("refresh-morale"),
    paletteStats: $("palette-stats"),
    questionPalette: $("question-palette"),
    submitExam: $("submit-exam"),
    viewResult: $("view-result"),
    resultBox: $("result-box"),
    antiCheatWarning: $("anti-cheat-warning"),
    submitModal: $("submit-modal"),
    shortcutsModal: $("shortcuts-modal"),
    submitSummary: $("submit-summary"),
    cancelSubmit: $("cancel-submit"),
    closeShortcuts: $("close-shortcuts"),
    confirmSubmit: $("confirm-submit"),
    onboardingModal: $("onboarding-modal"),
    dismissOnboarding: $("dismiss-onboarding"),
    openOnboarding: $("open-onboarding"),
    fontSizeSelect: $("font-size-select"),
    highContrastToggle: $("high-contrast-toggle"),
    confirmUnansweredToggle: $("confirm-unanswered-toggle"),
    autosaveIndicator: $("autosave-indicator"),
    syncHealthIndicator: $("sync-health-indicator"),
    heartbeatIndicator: $("heartbeat-indicator"),
    lowTimeAlert: $("low-time-alert"),
    runDiagnostics: $("run-diagnostics"),
    diagnosticsResult: $("diagnostics-result"),
    questionZoomOut: $("question-zoom-out"),
    questionZoomIn: $("question-zoom-in"),
    questionZoomReset: $("question-zoom-reset"),
    questionZoomLabel: $("question-zoom-label"),
    jumpUnanswered: $("jump-unanswered"),
    jumpSequence: $("jump-sequence"),
    jumpSequenceBtn: $("jump-sequence-btn"),
    filterAll: $("filter-all"),
    filterAnswered: $("filter-answered"),
    filterUnanswered: $("filter-unanswered"),
    filterReview: $("filter-review"),
    toggleFaq: $("toggle-faq"),
    faqContent: $("faq-content"),
    toggleRules: $("toggle-rules"),
    rulesContent: $("rules-content"),
    broadcastBadge: $("broadcast-badge"),
    broadcastFeed: $("broadcast-feed"),
    startBreathing: $("start-breathing"),
    breathingPrompt: $("breathing-prompt"),
    enterRevision: $("enter-revision"),
    inactivityModal: $("inactivity-modal"),
    continueAfterInactive: $("continue-after-inactive"),
    printResult: $("print-result"),
    receiptBox: $("receipt-box"),
    progressMiniSummary: $("progress-mini-summary"),
    focusStreak: $("focus-streak"),
    questionTimeSpent: $("question-time-spent"),
    answerTimeline: $("answer-timeline"),
    turboModeHint: $("turbo-mode-hint"),
  };

  const uiPrefs = {
    fontScale: "normal",
    highContrast: false,
    questionZoom: 100,
    confirmUnanswered: true,
  };

  function createTimerState(onTick) {
    let timerId = null;
    let expiresAt = null;

    const asSeconds = () => {
      if (!expiresAt) {
        return 0;
      }
      const expiresAtMs = new Date(expiresAt).valueOf();
      if (Number.isNaN(expiresAtMs)) {
        return 0;
      }
      return Math.max(0, Math.floor((expiresAtMs - Date.now()) / 1000));
    };

    const asText = () => {
      const totalSeconds = asSeconds();
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    };

    const tick = () => {
      onTick(asText(), asSeconds());
    };

    return {
      start(nextExpiresAt) {
        expiresAt = nextExpiresAt || null;
        if (timerId) {
          clearInterval(timerId);
          timerId = null;
        }
        tick();
        if (expiresAt) {
          timerId = window.setInterval(tick, 1000);
        }
      },
      stop() {
        if (timerId) {
          clearInterval(timerId);
          timerId = null;
        }
      },
      getExpiresAt() {
        return expiresAt;
      },
      getRemainingText() {
        return asText();
      },
      getRemainingSeconds() {
        return asSeconds();
      },
    };
  }

  function createAnswerState(onChange) {
    let draftAnswers = {};
    let confidenceByQuestion = {};
    let markedSequences = new Set();
    let answeredQuestionIds = new Set();
    let sequenceQuestionMap = new Map();
    let pendingQueue = [];

    const persist = () => {
      if (typeof onChange === "function") {
        onChange();
      }
    };

    const normalizePendingItem = (item) => {
      if (!item || !item.question_id || !item.selected_option_id) {
        return null;
      }
      return {
        question_id: String(item.question_id),
        selected_option_id: String(item.selected_option_id),
        sequence_number: Number(item.sequence_number || 0),
        confidence_tag: item.confidence_tag ? String(item.confidence_tag) : null,
        saved_at: item.saved_at || new Date().toISOString(),
      };
    };

    return {
      clear() {
        draftAnswers = {};
        confidenceByQuestion = {};
        markedSequences = new Set();
        answeredQuestionIds = new Set();
        sequenceQuestionMap = new Map();
        pendingQueue = [];
        persist();
      },
      hydrate(cache) {
        if (!cache || typeof cache !== "object") {
          return;
        }

        if (cache.draft_answers && typeof cache.draft_answers === "object") {
          draftAnswers = { ...draftAnswers, ...cache.draft_answers };
        }
        if (cache.confidence_by_question && typeof cache.confidence_by_question === "object") {
          confidenceByQuestion = { ...confidenceByQuestion, ...cache.confidence_by_question };
        }

        if (Array.isArray(cache.marked_sequences)) {
          markedSequences = new Set(
            cache.marked_sequences
              .map((value) => Number(value))
              .filter((value) => Number.isInteger(value) && value > 0)
          );
        }

        if (Array.isArray(cache.answered_question_ids)) {
          answeredQuestionIds = new Set(cache.answered_question_ids.map(String));
        }

        if (Array.isArray(cache.sequence_question_map)) {
          sequenceQuestionMap = new Map(
            cache.sequence_question_map
              .map((pair) => [Number(pair[0]), String(pair[1])])
              .filter(([sequence, questionId]) => sequence > 0 && questionId)
          );
        }

        if (Array.isArray(cache.pending_queue)) {
          pendingQueue = cache.pending_queue
            .map(normalizePendingItem)
            .filter((item) => item !== null);
        }
      },
      serialize() {
        return {
          draft_answers: { ...draftAnswers },
          confidence_by_question: { ...confidenceByQuestion },
          marked_sequences: [...markedSequences],
          answered_question_ids: [...answeredQuestionIds],
          sequence_question_map: [...sequenceQuestionMap.entries()],
          pending_queue: [...pendingQueue],
        };
      },
      rememberSelection(questionId, selectedOptionId) {
        if (!questionId || !selectedOptionId) {
          return;
        }
        draftAnswers[String(questionId)] = String(selectedOptionId);
        persist();
      },
      setConfidence(questionId, confidenceTag) {
        if (!questionId) {
          return;
        }
        if (!confidenceTag) {
          delete confidenceByQuestion[String(questionId)];
        } else {
          confidenceByQuestion[String(questionId)] = String(confidenceTag);
        }
        persist();
      },
      getConfidence(questionId) {
        if (!questionId) {
          return "";
        }
        return confidenceByQuestion[String(questionId)] || "";
      },
      getSelection(questionId) {
        if (!questionId) {
          return "";
        }
        return draftAnswers[String(questionId)] || "";
      },
      setSequenceQuestion(sequenceNumber, questionId) {
        const sequence = Number(sequenceNumber);
        if (!sequence || !questionId) {
          return;
        }
        sequenceQuestionMap.set(sequence, String(questionId));
        persist();
      },
      getQuestionId(sequenceNumber) {
        return sequenceQuestionMap.get(Number(sequenceNumber)) || "";
      },
      recordServerAnswered(answeredRows) {
        if (!Array.isArray(answeredRows)) {
          return;
        }
        for (const row of answeredRows) {
          const sequence = Number(row.sequence_number);
          const questionId = String(row.question_id || "");
          const selectedOptionId = String(row.selected_option_id || "");
          if (!sequence || !questionId) {
            continue;
          }
          sequenceQuestionMap.set(sequence, questionId);
          answeredQuestionIds.add(questionId);
          if (selectedOptionId && !draftAnswers[questionId]) {
            draftAnswers[questionId] = selectedOptionId;
          }
        }
        persist();
      },
      markSubmitted(questionId) {
        if (!questionId) {
          return;
        }
        answeredQuestionIds.add(String(questionId));
        persist();
      },
      isAnsweredSequence(sequenceNumber) {
        const questionId = sequenceQuestionMap.get(Number(sequenceNumber));
        if (!questionId) {
          return false;
        }
        return answeredQuestionIds.has(questionId) || Boolean(draftAnswers[questionId]);
      },
      getAnsweredCount(totalQuestions) {
        let count = 0;
        for (let sequence = 1; sequence <= Number(totalQuestions || 0); sequence += 1) {
          if (this.isAnsweredSequence(sequence)) {
            count += 1;
          }
        }
        return count;
      },
      getConfidenceTaggedCount(totalQuestions) {
        let count = 0;
        for (let sequence = 1; sequence <= Number(totalQuestions || 0); sequence += 1) {
          const questionId = sequenceQuestionMap.get(sequence);
          if (!questionId) {
            continue;
          }
          if (confidenceByQuestion[questionId]) {
            count += 1;
          }
        }
        return count;
      },
      toggleMarked(sequenceNumber) {
        const sequence = Number(sequenceNumber);
        if (!sequence) {
          return false;
        }
        if (markedSequences.has(sequence)) {
          markedSequences.delete(sequence);
        } else {
          markedSequences.add(sequence);
        }
        persist();
        return markedSequences.has(sequence);
      },
      isMarked(sequenceNumber) {
        return markedSequences.has(Number(sequenceNumber));
      },
      getMarkedCount() {
        return markedSequences.size;
      },
      queuePending(item) {
        const normalized = normalizePendingItem(item);
        if (!normalized) {
          return;
        }
        pendingQueue = pendingQueue.filter((entry) => entry.question_id !== normalized.question_id);
        pendingQueue.push(normalized);
        persist();
      },
      removePending(questionId) {
        if (!questionId) {
          return;
        }
        pendingQueue = pendingQueue.filter((entry) => entry.question_id !== String(questionId));
        persist();
      },
      getPendingQueue() {
        return [...pendingQueue];
      },
      getPendingCount() {
        return pendingQueue.length;
      },
    };
  }

  const timerState = createTimerState((remainingText, remainingSeconds) => {
    el.remainingTime.textContent = remainingText;
    updateMiniProgressWidget();
    if (st.attemptId && !st.finalized && remainingSeconds > 0) {
      evaluateLowTimeAlerts(remainingSeconds);
    }
    if (remainingSeconds === 0 && st.attemptId && !st.finalized) {
      autoSubmitExpiredAttempt();
    }
  });

  const answerState = createAnswerState(() => {
    persistAttemptCache();
    updateProgress();
    renderPalette();
    updateSyncHealthIndicator();
  });

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const setStatus = (message) => {
    el.status.textContent = message;
  };

  function renderAnswerTimeline() {
    if (!el.answerTimeline) {
      return;
    }
    if (!st.answerTimeline.length) {
      el.answerTimeline.textContent = "No answer changes yet.";
      return;
    }
    el.answerTimeline.innerHTML = st.answerTimeline
      .slice(-8)
      .map(
        (item) => `
          <div class="timeline-item">
            <strong>Q${esc(String(item.sequence))}</strong> - ${esc(item.action)}
            <span class="small">${esc(formatDate(item.at))}</span>
          </div>
        `
      )
      .join("");
  }

  function appendAnswerTimeline(action, sequenceNumber) {
    const sequence = Number(sequenceNumber || st.sequence || 0);
    if (!sequence) {
      return;
    }
    st.answerTimeline.push({
      sequence,
      action: String(action || "updated"),
      at: new Date().toISOString(),
    });
    if (st.answerTimeline.length > 120) {
      st.answerTimeline = st.answerTimeline.slice(-120);
    }
    renderAnswerTimeline();
    persistAttemptCache();
  }

  function stopQuestionTimeTracking() {
    if (!st.questionTimeStartedAt || !st.sequence) {
      st.questionTimeStartedAt = null;
      return;
    }
    const elapsedSeconds = Math.max(
      0,
      Math.floor((Date.now() - st.questionTimeStartedAt) / 1000)
    );
    if (!st.questionTimeBySequence[st.sequence]) {
      st.questionTimeBySequence[st.sequence] = 0;
    }
    st.questionTimeBySequence[st.sequence] += elapsedSeconds;
    st.questionTimeStartedAt = null;
  }

  function startQuestionTimeTracking(sequenceNumber) {
    const sequence = Number(sequenceNumber || 0);
    if (!sequence) {
      return;
    }
    stopQuestionTimeTracking();
    st.questionTimeStartedAt = Date.now();
    if (!st.questionTimeBySequence[sequence]) {
      st.questionTimeBySequence[sequence] = 0;
    }
  }

  function getCurrentQuestionElapsedSeconds() {
    const sequence = Number(st.sequence || 0);
    if (!sequence) {
      return 0;
    }
    const spent = Number(st.questionTimeBySequence[sequence] || 0);
    if (!st.questionTimeStartedAt) {
      return spent;
    }
    return spent + Math.max(0, Math.floor((Date.now() - st.questionTimeStartedAt) / 1000));
  }

  function updateMiniProgressWidget() {
    const total = Number(st.totalQuestions || 0);
    const answered = answerState.getAnsweredCount(total);
    const review = answerState.getMarkedCount();
    const pending = answerState.getPendingCount();
    if (el.progressMiniSummary) {
      el.progressMiniSummary.textContent = `Answered ${answered}/${total} | Review ${review} | Pending ${pending}`;
    }
    if (el.focusStreak) {
      el.focusStreak.textContent = String(st.focusStreak);
    }
    if (el.questionTimeSpent) {
      el.questionTimeSpent.textContent = `${getCurrentQuestionElapsedSeconds()}s`;
    }
  }

  function openShortcutsModal() {
    if (!el.shortcutsModal) {
      return;
    }
    el.shortcutsModal.hidden = false;
    syncModalOpenState();
  }

  function closeShortcutsModal() {
    if (!el.shortcutsModal) {
      return;
    }
    el.shortcutsModal.hidden = true;
    syncModalOpenState();
  }

  function setPausedState(paused, reason) {
    const changed = st.paused !== Boolean(paused);
    st.paused = Boolean(paused);
    if (st.finalized) {
      return;
    }
    if (st.paused && st.inactivityModalOpen) {
      closeInactivityModal();
    }
    if (st.paused) {
      stopQuestionTimeTracking();
    } else if (st.sequence) {
      startQuestionTimeTracking(st.sequence);
    }
    setAttemptControlsEnabled(!st.paused);
    if (st.paused && (changed || reason)) {
      setStatus(reason || "Exam is paused by admin. Wait for resume.");
    } else if (!st.paused && st.attemptId && (changed || reason)) {
      setStatus(reason || "Exam resumed. Continue from current question.");
      resetInactivityTimer();
    }
  }

  function readUiPrefs() {
    try {
      const raw = localStorage.getItem(STUDENT_UI_PREFS_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        if (parsed.font_scale === "normal" || parsed.font_scale === "large" || parsed.font_scale === "xlarge") {
          uiPrefs.fontScale = parsed.font_scale;
        }
        uiPrefs.highContrast = Boolean(parsed.high_contrast);
        const nextZoom = Number(parsed.question_zoom);
        if (!Number.isNaN(nextZoom)) {
          uiPrefs.questionZoom = Math.min(160, Math.max(80, Math.round(nextZoom)));
        }
        if (typeof parsed.confirm_unanswered === "boolean") {
          uiPrefs.confirmUnanswered = parsed.confirm_unanswered;
        }
      }
    } catch {
      return;
    }
  }

  function persistUiPrefs() {
    localStorage.setItem(
      STUDENT_UI_PREFS_KEY,
      JSON.stringify({
        font_scale: uiPrefs.fontScale,
        high_contrast: uiPrefs.highContrast,
        question_zoom: uiPrefs.questionZoom,
        confirm_unanswered: uiPrefs.confirmUnanswered,
      })
    );
  }

  function applyUiPrefs() {
    document.body.dataset.fontScale = uiPrefs.fontScale;
    document.body.classList.toggle("student-high-contrast", uiPrefs.highContrast);
    if (el.fontSizeSelect) {
      el.fontSizeSelect.value = uiPrefs.fontScale;
    }
    if (el.highContrastToggle) {
      el.highContrastToggle.checked = uiPrefs.highContrast;
    }
    if (el.questionZoomLabel) {
      el.questionZoomLabel.textContent = `${uiPrefs.questionZoom}%`;
    }
    if (el.confirmUnansweredToggle) {
      el.confirmUnansweredToggle.checked = uiPrefs.confirmUnanswered;
    }
    const zoomScale = (uiPrefs.questionZoom / 100).toFixed(2);
    document.documentElement.style.setProperty("--student-question-zoom", zoomScale);
  }

  function setQuestionZoom(nextZoom) {
    uiPrefs.questionZoom = Math.min(160, Math.max(80, Math.round(nextZoom)));
    applyUiPrefs();
    persistUiPrefs();
  }

  function openOnboardingModal() {
    el.onboardingModal.hidden = false;
    syncModalOpenState();
  }

  function dismissOnboardingModal(markSeen) {
    el.onboardingModal.hidden = true;
    syncModalOpenState();
    if (markSeen) {
      localStorage.setItem(STUDENT_ONBOARDING_KEY, "seen");
    }
  }

  function maybeShowOnboarding() {
    if (localStorage.getItem(STUDENT_ONBOARDING_KEY) === "seen") {
      return;
    }
    openOnboardingModal();
  }

  function syncModalOpenState() {
    const anyOpen =
      !el.submitModal.hidden ||
      !el.onboardingModal.hidden ||
      !el.inactivityModal.hidden ||
      (el.shortcutsModal ? !el.shortcutsModal.hidden : false);
    document.body.classList.toggle("modal-open", anyOpen);
  }

  function setAutosaveIndicator(mode, message) {
    if (!el.autosaveIndicator) {
      return;
    }
    el.autosaveIndicator.classList.remove(
      "autosave-synced",
      "autosave-local",
      "autosave-pending"
    );
    if (mode === "pending") {
      el.autosaveIndicator.classList.add("autosave-pending");
    } else if (mode === "local") {
      el.autosaveIndicator.classList.add("autosave-local");
    } else {
      el.autosaveIndicator.classList.add("autosave-synced");
    }
    el.autosaveIndicator.textContent = `Autosave: ${message}`;
  }

  function updateSyncHealthIndicator() {
    if (!el.syncHealthIndicator) {
      return;
    }
    const pendingCount = answerState.getPendingCount();
    el.syncHealthIndicator.classList.remove("sync-online", "sync-offline", "sync-degraded");

    if (!navigator.onLine) {
      el.syncHealthIndicator.classList.add("sync-offline");
      el.syncHealthIndicator.textContent = "LAN: Offline";
      return;
    }

    if (pendingCount > 0) {
      el.syncHealthIndicator.classList.add("sync-degraded");
      el.syncHealthIndicator.textContent = `LAN: Syncing (${pendingCount})`;
      return;
    }

    el.syncHealthIndicator.classList.add("sync-online");
    el.syncHealthIndicator.textContent = "LAN: Healthy";
  }

  function updateHeartbeatIndicator(mode, message) {
    if (!el.heartbeatIndicator) {
      return;
    }
    el.heartbeatIndicator.classList.remove("sync-online", "sync-offline", "sync-degraded");
    if (mode === "offline") {
      el.heartbeatIndicator.classList.add("sync-offline");
    } else if (mode === "degraded") {
      el.heartbeatIndicator.classList.add("sync-degraded");
    } else {
      el.heartbeatIndicator.classList.add("sync-online");
    }
    el.heartbeatIndicator.textContent = message;
  }

  async function pingServerHeartbeat() {
    const start = performance.now();
    try {
      const response = await fetch("/system/version", {
        method: "GET",
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const latencyMs = Math.round(performance.now() - start);
      st.heartbeatLatencyMs = latencyMs;
      if (latencyMs > 1500) {
        updateHeartbeatIndicator("degraded", `Server: Slow (${latencyMs}ms)`);
      } else {
        updateHeartbeatIndicator("online", `Server: OK (${latencyMs}ms)`);
      }
    } catch {
      updateHeartbeatIndicator("offline", "Server: Unreachable");
    }
  }

  function updatePaletteFilterButtons() {
    const mapping = {
      all: el.filterAll,
      answered: el.filterAnswered,
      unanswered: el.filterUnanswered,
      review: el.filterReview,
    };
    Object.entries(mapping).forEach(([key, button]) => {
      if (!button) {
        return;
      }
      button.classList.toggle("active-filter", st.paletteFilter === key);
    });
  }

  function sequenceMatchesFilter(sequence) {
    if (st.paletteFilter === "all") {
      return true;
    }
    if (st.paletteFilter === "answered") {
      return answerState.isAnsweredSequence(sequence);
    }
    if (st.paletteFilter === "unanswered") {
      return !answerState.isAnsweredSequence(sequence);
    }
    if (st.paletteFilter === "review") {
      return answerState.isMarked(sequence);
    }
    return true;
  }

  function setPaletteFilter(filterKey) {
    st.paletteFilter = filterKey;
    updatePaletteFilterButtons();
    renderPalette();
  }

  function runDeviceDiagnostics() {
    const checks = [
      {
        label: "Keyboard Support",
        ok: typeof window.KeyboardEvent !== "undefined",
      },
      {
        label: "Mouse Support",
        ok: typeof window.MouseEvent !== "undefined",
      },
      {
        label: "Network Online",
        ok: navigator.onLine,
      },
      {
        label: "Local Storage Available",
        ok: (() => {
          try {
            localStorage.setItem("nitmexs_diag", "1");
            localStorage.removeItem("nitmexs_diag");
            return true;
          } catch {
            return false;
          }
        })(),
      },
      {
        label: "Recent Keyboard Activity",
        ok: st.diagnostics.keyboardSeen,
      },
      {
        label: "Recent Mouse Activity",
        ok: st.diagnostics.mouseSeen,
      },
    ];

    st.diagnostics.lastRunAt = new Date().toISOString();
    const allOk = checks.every((item) => item.ok);
    const rows = checks
      .map(
        (item) => `<div>${item.ok ? "PASS" : "WARN"} - ${esc(item.label)}</div>`
      )
      .join("");
    el.diagnosticsResult.innerHTML = `
      <div><strong>${allOk ? "Diagnostics OK" : "Diagnostics require attention"}</strong></div>
      ${rows}
      <div>Checked at: ${esc(formatDate(st.diagnostics.lastRunAt))}</div>
    `;
    setStatus(
      allOk
        ? "Device diagnostics completed successfully."
        : "Diagnostics completed with warnings. Please review before exam."
    );
  }

  function toggleFaq() {
    const nextHidden = !el.faqContent.hidden;
    el.faqContent.hidden = nextHidden;
    el.toggleFaq.textContent = nextHidden ? "Show" : "Hide";
  }

  function toggleRules() {
    const nextHidden = !el.rulesContent.hidden;
    el.rulesContent.hidden = nextHidden;
    el.toggleRules.textContent = nextHidden ? "Show" : "Hide";
  }

  async function loadExamRules() {
    if (!st.attemptId) {
      return;
    }
    try {
      const data = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/rules`,
        { headers: studentHeaders() }
      );
      const rules = Array.isArray(data.rules) ? data.rules : [];
      const list = rules
        .map((rule) => `<li>${esc(rule)}</li>`)
        .join("");
      el.rulesContent.innerHTML = `
        <p><strong>${esc(data.exam_name || st.examName || "Exam")}</strong> | ${esc(String(data.duration_minutes || "-"))} min</p>
        <p>Negative Marking: ${esc(String(data.negative_marking ?? 0))}</p>
        <ol>${list || "<li>No explicit rules configured.</li>"}</ol>
      `;
    } catch (error) {
      el.rulesContent.innerHTML = `<p>${esc(error.message || "Unable to load rules.")}</p>`;
    }
  }

  function renderBroadcasts(rows) {
    if (!Array.isArray(rows) || rows.length === 0) {
      el.broadcastBadge.textContent = "No alerts";
      el.broadcastBadge.classList.remove("sync-offline", "sync-degraded");
      el.broadcastBadge.classList.add("sync-online");
      el.broadcastFeed.textContent = "No broadcast messages yet.";
      return;
    }

    const latest = rows[rows.length - 1];
    const severity = String(latest.severity || "info").toLowerCase();
    el.broadcastBadge.classList.remove("sync-online", "sync-offline", "sync-degraded");
    if (severity === "critical") {
      el.broadcastBadge.classList.add("sync-offline");
      el.broadcastBadge.textContent = "Critical alert";
    } else if (severity === "warn") {
      el.broadcastBadge.classList.add("sync-degraded");
      el.broadcastBadge.textContent = "Warning";
    } else {
      el.broadcastBadge.classList.add("sync-online");
      el.broadcastBadge.textContent = "Info";
    }

    el.broadcastFeed.innerHTML = rows
      .slice(-5)
      .map(
        (item) => `
          <div class="broadcast-item">
            <div><strong>${esc(String(item.severity || "info").toUpperCase())}</strong> - ${esc(item.message || "")}</div>
            <div class="small">${esc(formatDate(item.created_at))}</div>
          </div>
        `
      )
      .join("");
  }

  async function acknowledgeBroadcastReceipts(rows) {
    if (!st.attemptId || !Array.isArray(rows) || rows.length === 0) {
      return;
    }
    const pendingIds = rows
      .map((item) => String(item.id || "").trim())
      .filter((value) => value && !st.seenBroadcastIds.has(value));
    if (!pendingIds.length) {
      return;
    }
    try {
      const ack = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/broadcasts/ack`,
        {
          method: "POST",
          headers: studentHeaders(),
          body: { broadcast_ids: pendingIds },
        }
      );
      const accepted = ack.acknowledged_broadcast_ids || pendingIds;
      accepted.forEach((id) => st.seenBroadcastIds.add(String(id)));
    } catch {
      return;
    }
  }

  async function pullBroadcasts() {
    if (!st.attemptId || st.finalized || st.paused) {
      return;
    }
    try {
      const query = new URLSearchParams({
        limit: "20",
      });
      if (st.broadcastCursor) {
        query.set("since", st.broadcastCursor);
      }
      const data = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/broadcasts?${query.toString()}`,
        { headers: studentHeaders() }
      );
      const rows = data.broadcasts || [];
      if (rows.length > 0) {
        st.broadcastCursor = rows[rows.length - 1].created_at || st.broadcastCursor;
        const byId = new Map(st.broadcastHistory.map((item) => [String(item.id), item]));
        rows.forEach((item) => {
          const id = String(item.id || "").trim();
          if (!id) {
            return;
          }
          byId.set(id, item);
        });
        st.broadcastHistory = Array.from(byId.values())
          .sort((left, right) => String(left.created_at || "").localeCompare(String(right.created_at || "")))
          .slice(-50);
      }
      renderBroadcasts(st.broadcastHistory);
      persistAttemptCache();
      await acknowledgeBroadcastReceipts(rows);
    } catch {
      return;
    }
  }

  async function reportQuestionIssue() {
    if (!st.attemptId || !st.currentQuestion || st.finalized || st.paused) {
      setStatus("Active question required to report issue.");
      return;
    }
    const issueType = window.prompt("Issue type? (example: typo, unclear, option_mismatch)", "content_issue");
    if (issueType === null) {
      return;
    }
    const note = window.prompt("Short note (optional):", "");
    try {
      await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/question-issue`, {
        method: "POST",
        headers: studentHeaders(),
        body: {
          question_id: st.currentQuestion.id,
          issue_type: issueType || "content_issue",
          note: note || null,
        },
      });
      setStatus("Question issue reported to admin/proctor.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function reportTechnicalIssue() {
    if (!st.attemptId || st.finalized || st.paused) {
      setStatus("Active attempt required to report technical issue.");
      return;
    }
    const issueType = window.prompt("Technical issue type? (example: lag, keyboard, network)", "technical_issue");
    if (issueType === null) {
      return;
    }
    const note = window.prompt("Short note (optional):", "");
    try {
      await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/technical-issue`, {
        method: "POST",
        headers: studentHeaders(),
        body: {
          issue_type: issueType || "technical_issue",
          note: note || null,
        },
      });
      setStatus("Technical issue reported. Continue exam; autosave remains active.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function stopBreathingPrompt() {
    if (st.breathingTimerId) {
      clearInterval(st.breathingTimerId);
      st.breathingTimerId = null;
    }
  }

  function startBreathingPrompt() {
    if (!el.breathingPrompt) {
      return;
    }
    stopBreathingPrompt();
    st.breathingSecondsLeft = 30;
    el.breathingPrompt.textContent = "Breathing reset started: Inhale 4s, hold 2s, exhale 4s.";
    st.breathingTimerId = window.setInterval(() => {
      st.breathingSecondsLeft -= 1;
      if (st.breathingSecondsLeft <= 0) {
        stopBreathingPrompt();
        el.breathingPrompt.textContent = "Reset complete. You're ready to continue with steady focus.";
        return;
      }
      const phase = st.breathingSecondsLeft % 10;
      let instruction = "Inhale";
      if (phase >= 4 && phase < 6) {
        instruction = "Hold";
      } else if (phase >= 6) {
        instruction = "Exhale";
      }
      el.breathingPrompt.textContent =
        `Breathing reset (${st.breathingSecondsLeft}s): ${instruction} slowly and relax shoulders.`;
    }, 1000);
  }

  async function enterRevisionMode() {
    if (!st.attemptId || st.finalized || st.paused) {
      setStatus("Active exam required for revision mode.");
      return;
    }
    st.revisionMode = true;
    const total = Number(st.totalQuestions || 0);
    let target = 0;
    for (let sequence = 1; sequence <= total; sequence += 1) {
      if (answerState.isMarked(sequence) || !answerState.isAnsweredSequence(sequence)) {
        target = sequence;
        break;
      }
    }
    st.paletteFilter = "review";
    renderPalette();
    if (!target) {
      st.paletteFilter = "unanswered";
      renderPalette();
      await jumpToFirstUnanswered();
      setStatus("Revision mode active. Reviewing unanswered questions.");
      return;
    }
    await fetchQuestion(target);
    setStatus(`Revision mode active. Reviewing question #${target}.`);
  }

  function buildAcknowledgementReceipt(summary) {
    const receiptId = `RCPT-${st.attemptId.slice(0, 8)}-${Date.now().toString().slice(-6)}`;
    return {
      receipt_id: receiptId,
      student_id: st.studentId,
      exam_id: st.examId,
      exam_name: st.examName,
      attempt_id: st.attemptId,
      submitted_at: new Date().toISOString(),
      score: Number(summary?.total_score ?? 0),
      percentage: Number(summary?.percentage ?? 0),
      passed: Boolean(summary?.passed),
    };
  }

  function renderReceipt(receipt) {
    if (!receipt || !el.receiptBox) {
      return;
    }
    if (el.printResult) {
      el.printResult.disabled = false;
    }
    el.receiptBox.innerHTML = `
      <div class="summary-row"><span>Receipt ID</span><strong>${esc(receipt.receipt_id)}</strong></div>
      <div class="summary-row"><span>Student</span><strong>${esc(receipt.student_id)}</strong></div>
      <div class="summary-row"><span>Exam</span><strong>${esc(receipt.exam_name || receipt.exam_id)}</strong></div>
      <div class="summary-row"><span>Attempt</span><strong>${esc(receipt.attempt_id)}</strong></div>
      <div class="summary-row"><span>Submitted At</span><strong>${esc(formatDate(receipt.submitted_at))}</strong></div>
      <div class="summary-row"><span>Score</span><strong>${esc(receipt.score.toFixed(2))}</strong></div>
      <div class="summary-row"><span>Percentage</span><strong>${esc(receipt.percentage.toFixed(2))}%</strong></div>
      <div class="summary-row"><span>Status</span><strong>${receipt.passed ? "PASS" : "NEEDS IMPROVEMENT"}</strong></div>
    `;
  }

  function printResultSlip() {
    if (!st.receipt) {
      setStatus("Submit exam first to generate printable result slip.");
      return;
    }
    const popup = window.open("", "_blank", "width=820,height=720");
    if (!popup) {
      setStatus("Popup blocked. Please allow popups to print result slip.");
      return;
    }
    popup.document.write(`
      <html>
        <head>
          <title>NITMEXS Result Slip</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
            h1 { margin: 0 0 12px; }
            table { width: 100%; border-collapse: collapse; margin-top: 8px; }
            td { border: 1px solid #ddd; padding: 8px; }
            td:first-child { width: 30%; font-weight: bold; background: #f7f7f7; }
          </style>
        </head>
        <body>
          <h1>NITMEXS Result Slip</h1>
          <table>
            <tr><td>Receipt ID</td><td>${esc(st.receipt.receipt_id)}</td></tr>
            <tr><td>Student</td><td>${esc(st.receipt.student_id)}</td></tr>
            <tr><td>Exam</td><td>${esc(st.receipt.exam_name || st.receipt.exam_id)}</td></tr>
            <tr><td>Attempt</td><td>${esc(st.receipt.attempt_id)}</td></tr>
            <tr><td>Submitted</td><td>${esc(formatDate(st.receipt.submitted_at))}</td></tr>
            <tr><td>Score</td><td>${esc(st.receipt.score.toFixed(2))}</td></tr>
            <tr><td>Percentage</td><td>${esc(st.receipt.percentage.toFixed(2))}%</td></tr>
            <tr><td>Status</td><td>${st.receipt.passed ? "PASS" : "NEEDS IMPROVEMENT"}</td></tr>
          </table>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  }

  function showLowTimeAlert(message) {
    if (!el.lowTimeAlert) {
      return;
    }
    el.lowTimeAlert.textContent = message;
    el.lowTimeAlert.hidden = false;
    window.setTimeout(() => {
      if (el.lowTimeAlert.textContent === message) {
        el.lowTimeAlert.hidden = true;
      }
    }, 7000);
  }

  function evaluateLowTimeAlerts(remainingSeconds) {
    if (el.turboModeHint) {
      el.turboModeHint.hidden = remainingSeconds > 300 || st.finalized;
    }
    const thresholds = [
      { seconds: 300, message: "5 minutes left. High-confidence questions pe focus karo." },
      { seconds: 120, message: "2 minutes left. Review complete karke submit readiness check karo." },
      { seconds: 60, message: "Final 60 seconds. Pending doubts skip karo aur finalize plan banao." },
    ];

    for (const item of thresholds) {
      if (remainingSeconds <= item.seconds && !st.lowTimeAlerted.has(item.seconds)) {
        st.lowTimeAlerted.add(item.seconds);
        showLowTimeAlert(item.message);
        setStatus(item.message);
        if (item.seconds <= 120) {
          startBreathingPrompt();
        }
      }
    }
  }

  function openInactivityModal() {
    if (!st.attemptId || st.finalized || st.inactivityModalOpen) {
      return;
    }
    st.inactivityModalOpen = true;
    st.focusStreak = 0;
    updateMiniProgressWidget();
    el.inactivityModal.hidden = false;
    syncModalOpenState();
    setStatus("Inactivity warning: continue exam to resume active session tracking.");
  }

  function closeInactivityModal() {
    st.inactivityModalOpen = false;
    el.inactivityModal.hidden = true;
    syncModalOpenState();
  }

  function resetInactivityTimer() {
    if (st.inactivityTimerId) {
      clearTimeout(st.inactivityTimerId);
      st.inactivityTimerId = null;
    }
    if (!st.attemptId || st.finalized || st.paused) {
      return;
    }
    if (st.inactivityModalOpen) {
      closeInactivityModal();
    }
    st.inactivityTimerId = window.setTimeout(openInactivityModal, INACTIVITY_TIMEOUT_MS);
  }

  function setMoralePlaceholder() {
    el.moraleTitle.textContent = "Stay focused";
    el.moraleMessage.textContent = "Start exam to receive personalized motivation and pacing tips.";
    el.moraleTip.textContent = "Tip: read question statement twice before selecting answer.";
  }

  function renderResultSummary(payload) {
    const summary = payload?.result && typeof payload.result === "object"
      ? payload.result
      : payload;
    const questionResults = Array.isArray(payload?.question_results)
      ? payload.question_results
      : [];

    const totalScore = Number(summary?.total_score ?? 0);
    const totalPossible = Number(summary?.total_possible_marks ?? 0);
    const percentage = Number(summary?.percentage ?? 0);
    const passed = Boolean(summary?.passed);

    const attempted = questionResults.filter((item) => item.selected_option_id).length;
    const correct = questionResults.filter((item) => item.is_correct).length;
    const totalQuestions = questionResults.length || Number(st.totalQuestions || 0);

    const resultBadgeClass = passed ? "result-pass" : "result-fail";
    const resultBadgeText = passed ? "PASS" : "NEEDS IMPROVEMENT";

    el.resultBox.innerHTML = `
      <div class="result-grid">
        <div class="result-kpi">
          <p>Final Score</p>
          <h4>${totalScore.toFixed(2)} / ${totalPossible.toFixed(2)}</h4>
        </div>
        <div class="result-kpi">
          <p>Percentage</p>
          <h4>${percentage.toFixed(2)}%</h4>
        </div>
        <div class="result-kpi">
          <p>Status</p>
          <h4><span class="result-badge ${resultBadgeClass}">${resultBadgeText}</span></h4>
        </div>
      </div>
      <div class="result-grid compact">
        <div class="result-kpi small">
          <p>Attempted</p>
          <h5>${attempted || 0}${totalQuestions ? ` / ${totalQuestions}` : ""}</h5>
        </div>
        <div class="result-kpi small">
          <p>Correct</p>
          <h5>${correct || 0}${totalQuestions ? ` / ${totalQuestions}` : ""}</h5>
        </div>
      </div>
      <p class="result-note">
        ${passed
          ? "Excellent effort. Keep this consistency for upcoming exams."
          : "Acha attempt tha. Weak areas revise karke next attempt me score improve hoga."}
      </p>
    `;
  }

  function showAntiCheatWarning(message) {
    el.antiCheatWarning.textContent = message;
    el.antiCheatWarning.hidden = false;
    if (st.warningTimeoutId) {
      clearTimeout(st.warningTimeoutId);
    }
    st.warningTimeoutId = window.setTimeout(() => {
      el.antiCheatWarning.hidden = true;
      st.warningTimeoutId = null;
    }, 3600);
  }

  function parseSession() {
    try {
      const raw = localStorage.getItem(STUDENT_SESSION_KEY);
      if (!raw) {
        return null;
      }
      const payload = JSON.parse(raw);
      if (!payload?.student_id) {
        return null;
      }
      return payload;
    } catch {
      return null;
    }
  }

  function ensureSession() {
    const session = parseSession();
    if (!session) {
      window.location.href = "/web?target=student&reason=login_required";
      throw new Error("Student login required");
    }
    st.studentId = String(session.student_id);
    el.sessionStudent.textContent = st.studentId;
  }

  function studentHeaders() {
    return { "x-student-id": st.studentId };
  }

  async function api(path, options = {}) {
    const request = { ...options, headers: { ...(options.headers || {}) } };
    if (request.body && typeof request.body !== "string") {
      request.headers["Content-Type"] = "application/json";
      request.body = JSON.stringify(request.body);
    }

    const response = await fetch(path, request);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.detail || payload.error || `HTTP ${response.status}`);
      error.httpStatus = response.status;
      throw error;
    }
    return payload.data ?? payload;
  }

  function attemptCacheKey() {
    if (!st.attemptId) {
      return "";
    }
    return `${ATTEMPT_CACHE_PREFIX}${st.attemptId}`;
  }

  function persistAttemptCache() {
    if (!st.attemptId) {
      return;
    }
    const key = attemptCacheKey();
    const payload = {
      student_id: st.studentId,
      attempt_id: st.attemptId,
      exam_id: st.examId,
      exam_name: st.examName,
      sequence: st.sequence,
      total_questions: st.totalQuestions,
      paused: st.paused,
      focus_streak: st.focusStreak,
      question_time_by_sequence: st.questionTimeBySequence,
      answer_timeline: st.answerTimeline,
      seen_broadcast_ids: Array.from(st.seenBroadcastIds),
      broadcast_history: st.broadcastHistory,
      expires_at: timerState.getExpiresAt(),
      updated_at: new Date().toISOString(),
      ...answerState.serialize(),
    };
    localStorage.setItem(key, JSON.stringify(payload));
  }

  function clearAttemptCache() {
    const key = attemptCacheKey();
    if (!key) {
      return;
    }
    localStorage.removeItem(key);
  }

  function applyCachedAttemptState() {
    const key = attemptCacheKey();
    if (!key) {
      return;
    }
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return;
      }
      const cache = JSON.parse(raw);
      if (!cache || cache.attempt_id !== st.attemptId) {
        return;
      }
      answerState.hydrate(cache);
      if (Number.isInteger(cache.sequence) && cache.sequence > 0) {
        st.sequence = cache.sequence;
      }
      if (Number.isInteger(cache.total_questions) && cache.total_questions > 0) {
        st.totalQuestions = cache.total_questions;
      }
      if (typeof cache.focus_streak === "number" && Number.isFinite(cache.focus_streak)) {
        st.focusStreak = Math.max(0, Math.floor(cache.focus_streak));
      }
      if (cache.question_time_by_sequence && typeof cache.question_time_by_sequence === "object") {
        st.questionTimeBySequence = { ...cache.question_time_by_sequence };
      }
      if (Array.isArray(cache.answer_timeline)) {
        st.answerTimeline = cache.answer_timeline.slice(-120).map((item) => ({
          sequence: Number(item.sequence || 0),
          action: String(item.action || "updated"),
          at: item.at || new Date().toISOString(),
        }));
      }
      if (Array.isArray(cache.seen_broadcast_ids)) {
        st.seenBroadcastIds = new Set(cache.seen_broadcast_ids.map(String));
      }
      if (Array.isArray(cache.broadcast_history)) {
        st.broadcastHistory = cache.broadcast_history
          .slice(-50)
          .map((item) => ({
            id: item.id,
            created_at: item.created_at,
            message: item.message,
            severity: item.severity || "info",
          }))
          .filter((item) => item.id && item.created_at);
        renderBroadcasts(st.broadcastHistory);
      }
      if (cache.exam_name) {
        st.examName = String(cache.exam_name);
      }
      if (cache.expires_at) {
        timerState.start(cache.expires_at);
      }
      renderAnswerTimeline();
      updateMiniProgressWidget();
    } catch {
      return;
    }
  }

  function findLatestCachedAttemptForStudent() {
    let latest = null;
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (!key || !key.startsWith(ATTEMPT_CACHE_PREFIX)) {
        continue;
      }
      try {
        const raw = localStorage.getItem(key);
        if (!raw) {
          continue;
        }
        const payload = JSON.parse(raw);
        if (payload?.student_id !== st.studentId || !payload?.attempt_id) {
          continue;
        }
        if (!latest) {
          latest = payload;
          continue;
        }
        if (String(payload.updated_at || "") > String(latest.updated_at || "")) {
          latest = payload;
        }
      } catch {
        continue;
      }
    }
    return latest;
  }

  function formatDate(isoValue) {
    if (!isoValue) {
      return "-";
    }
    const date = new Date(isoValue);
    if (Number.isNaN(date.valueOf())) {
      return isoValue;
    }
    return date.toLocaleString();
  }

  function updateMarkReviewLabel() {
    if (answerState.isMarked(st.sequence)) {
      el.markReview.textContent = "Unmark Review";
    } else {
      el.markReview.textContent = "Mark for Review";
    }
  }

  function updateProgress() {
    const total = Number(st.totalQuestions || 0);
    const answered = answerState.getAnsweredCount(total);
    el.questionProgress.textContent = `Question ${st.sequence} of ${total || "-"}`;
    el.paletteStats.textContent = `Answered ${answered} / ${total}`;
    el.prevQuestion.disabled = st.sequence <= 1 || st.finalized || st.paused;
    updateMiniProgressWidget();
  }

  function renderPalette() {
    const total = Number(st.totalQuestions || 0);
    if (!total) {
      el.questionPalette.innerHTML = '<p class="palette-placeholder">Question palette will appear after exam start.</p>';
      updatePaletteFilterButtons();
      return;
    }

    const paletteButtons = [];
    for (let sequence = 1; sequence <= total; sequence += 1) {
      if (!sequenceMatchesFilter(sequence)) {
        continue;
      }
      const marked = answerState.isMarked(sequence);
      const answered = answerState.isAnsweredSequence(sequence);
      const stateClass = marked ? "review" : answered ? "answered" : "unanswered";
      const currentClass = sequence === st.sequence ? "current" : "";
      paletteButtons.push(
        `<button type="button" class="palette-btn ${stateClass} ${currentClass}" data-sequence="${sequence}">${sequence}</button>`
      );
    }
    if (paletteButtons.length === 0) {
      el.questionPalette.innerHTML = '<p class="palette-placeholder">No questions match this filter.</p>';
    } else {
      el.questionPalette.innerHTML = paletteButtons.join("");
    }
    updatePaletteFilterButtons();
  }

  function renderExamOptions(exams) {
    const previousValue = el.examSelect.value;
    el.examSelect.innerHTML = '<option value="">Choose an available exam...</option>';

    for (const exam of exams) {
      const option = document.createElement("option");
      option.value = exam.id;
      option.dataset.examName = exam.name;
      option.textContent = `${exam.name} (${exam.duration_minutes} min)`;
      el.examSelect.appendChild(option);
    }

    if (previousValue && exams.some((exam) => exam.id === previousValue)) {
      el.examSelect.value = previousValue;
    }
  }

  function renderAttemptMeta(statusPayload = null) {
    const metaLines = [
      `Attempt ID: ${st.attemptId || "-"}`,
      `Exam: ${st.examName || st.examId || "-"}`,
    ];

    if (statusPayload) {
      metaLines.push(`Started: ${formatDate(statusPayload.started_at)}`);
      metaLines.push(`Ends: ${formatDate(statusPayload.expires_at)}`);
      metaLines.push(`Status: ${statusPayload.status || "-"}`);
    }

    const pendingCount = answerState.getPendingCount();
    metaLines.push(`Pending Sync: ${pendingCount}`);

    el.attemptMeta.textContent = metaLines.join(" | ");
  }

  function renderQuestion(payload) {
    stopQuestionTimeTracking();
    st.currentQuestion = payload.question;
    st.sequence = Number(payload.sequence_number);
    answerState.setSequenceQuestion(st.sequence, payload.question.id);
    startQuestionTimeTracking(st.sequence);

    el.examName.textContent = st.examName || st.examId || "Exam";
    el.questionText.textContent = payload.question.text || "Question text unavailable.";

    const selectedOptionId = answerState.getSelection(payload.question.id);
    el.optionsList.innerHTML = "";

    for (const option of payload.options || []) {
      const label = document.createElement("label");
      label.className = "choice-option";

      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "selected-option";
      radio.value = option.id;
      radio.checked = selectedOptionId === option.id;

      const text = document.createElement("span");
      text.textContent = option.option_text;

      label.appendChild(radio);
      label.appendChild(text);
      el.optionsList.appendChild(label);
    }

    const selectedConfidence = answerState.getConfidence(payload.question.id);
    document
      .querySelectorAll('input[name="confidence-tag"]')
      .forEach((input) => {
        if (!(input instanceof HTMLInputElement)) {
          return;
        }
        input.checked = input.value === selectedConfidence;
      });

    updateMarkReviewLabel();
    updateProgress();
    renderPalette();
    persistAttemptCache();
    resetInactivityTimer();
    updateMiniProgressWidget();
  }

  function setAttemptControlsEnabled(enabled) {
    const active = Boolean(enabled) && !st.finalized && !st.paused;
    el.markReview.disabled = !active;
    el.prevQuestion.disabled = !active || st.sequence <= 1;
    el.saveNext.disabled = !active;
    if (el.reportQuestionIssue) {
      el.reportQuestionIssue.disabled = !active;
    }
    if (el.reportTechnicalIssue) {
      el.reportTechnicalIssue.disabled = !active;
    }
    if (el.enterRevision) {
      el.enterRevision.disabled = !active;
    }
    if (el.startBreathing) {
      el.startBreathing.disabled = !active;
    }
    el.submitExam.disabled = !active;
    el.jumpUnanswered.disabled = !active;
    if (el.jumpSequence) {
      el.jumpSequence.disabled = !active;
    }
    if (el.jumpSequenceBtn) {
      el.jumpSequenceBtn.disabled = !active;
    }
  }

  function currentlySelectedOptionId() {
    const selected = el.optionsList.querySelector('input[name="selected-option"]:checked');
    return selected ? selected.value : "";
  }

  function currentlySelectedConfidenceTag() {
    const selected = document.querySelector('input[name="confidence-tag"]:checked');
    if (!(selected instanceof HTMLInputElement)) {
      return "";
    }
    return selected.value || "";
  }

  function rememberCurrentSelection() {
    if (!st.currentQuestion) {
      return "";
    }
    const selectedOptionId = currentlySelectedOptionId();
    if (!selectedOptionId) {
      return "";
    }
    const previousSelection = answerState.getSelection(st.currentQuestion.id);
    answerState.rememberSelection(st.currentQuestion.id, selectedOptionId);
    answerState.setConfidence(st.currentQuestion.id, currentlySelectedConfidenceTag() || null);
    setAutosaveIndicator("local", "Saved Locally");
    if (previousSelection !== selectedOptionId) {
      appendAnswerTimeline("option_changed", st.sequence);
    }
    updateMiniProgressWidget();
    return selectedOptionId;
  }

  async function submitAnswerToServer(questionId, selectedOptionId, sequenceNumber) {
    if (!questionId || !selectedOptionId || !st.attemptId) {
      return false;
    }

    const queueItem = {
      question_id: questionId,
      selected_option_id: selectedOptionId,
      sequence_number: sequenceNumber,
      confidence_tag: answerState.getConfidence(questionId) || null,
      saved_at: new Date().toISOString(),
    };

    if (!navigator.onLine) {
      answerState.queuePending(queueItem);
      setAutosaveIndicator("pending", "Pending LAN Sync");
      setStatus("LAN temporary unavailable. Answer saved locally and queued.");
      updateSyncHealthIndicator();
      return false;
    }

    try {
      await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/answers`, {
        method: "POST",
        headers: studentHeaders(),
        body: {
          question_id: questionId,
          selected_option_id: selectedOptionId,
          confidence_tag: queueItem.confidence_tag,
        },
      });
      answerState.markSubmitted(questionId);
      answerState.removePending(questionId);
      setAutosaveIndicator("synced", "Synced");
      updateSyncHealthIndicator();
      return true;
    } catch (error) {
      if (error?.httpStatus && error.httpStatus < 500) {
        setStatus(error.message);
        return false;
      }
      answerState.queuePending(queueItem);
      setAutosaveIndicator("pending", "Pending LAN Sync");
      setStatus("LAN issue detected. Answer saved locally and will auto-sync.");
      updateSyncHealthIndicator();
      return false;
    }
  }

  async function flushPendingQueue() {
    if (!st.attemptId) {
      return;
    }

    const pending = answerState.getPendingQueue();
    if (!pending.length || !navigator.onLine) {
      return;
    }

    let synced = 0;
    for (const item of pending) {
      try {
        await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/answers`, {
          method: "POST",
          headers: studentHeaders(),
          body: {
            question_id: item.question_id,
            selected_option_id: item.selected_option_id,
            confidence_tag: item.confidence_tag || null,
          },
        });
        answerState.markSubmitted(item.question_id);
        answerState.removePending(item.question_id);
        synced += 1;
      } catch (error) {
        if (error?.httpStatus && error.httpStatus < 500) {
          answerState.removePending(item.question_id);
          continue;
        }
        break;
      }
    }

    if (synced > 0) {
      if (answerState.getPendingCount() === 0) {
        setAutosaveIndicator("synced", "Synced");
      } else {
        setAutosaveIndicator("pending", "Pending LAN Sync");
      }
      setStatus(`${synced} locally saved answer(s) synced successfully.`);
    }

    renderAttemptMeta();
    updateSyncHealthIndicator();
    updateMiniProgressWidget();
  }

  async function loadVersion() {
    try {
      const versionPayload = await api("/system/version");
      el.version.textContent = versionPayload.version || "n/a";
    } catch {
      el.version.textContent = "unreachable";
    }
  }

  async function loadExams() {
    try {
      const exams = await api("/student/exams", { headers: studentHeaders() });
      renderExamOptions(exams);
      setStatus(`Loaded ${exams.length} available exam(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function refreshAttemptStatus() {
    if (!st.attemptId) {
      return null;
    }
    const statusPayload = await api(
      `/student/attempts/${encodeURIComponent(st.attemptId)}/status`,
      { headers: studentHeaders() }
    );

    st.totalQuestions = Number(statusPayload.total_question_count || 0);
    timerState.start(statusPayload.expires_at || timerState.getExpiresAt());
    answerState.recordServerAnswered(statusPayload.answered || []);
    renderAttemptMeta(statusPayload);
    updateSyncHealthIndicator();
    const status = String(statusPayload.status || "").toUpperCase();
    if (status === "ACTIVE") {
      setPausedState(false);
      if (!st.finalized) {
        setAttemptControlsEnabled(true);
      }
    } else if (status === "PAUSED") {
      setPausedState(true);
    } else if (status === "FINALIZED" || status === "GRADED" || status === "ARCHIVED") {
      st.finalized = true;
      st.paused = false;
      setAttemptControlsEnabled(false);
      timerState.stop();
      setStatus("Attempt finalized by admin/system. View result.");
    } else {
      setAttemptControlsEnabled(false);
    }

    updateProgress();
    renderPalette();
    return statusPayload;
  }

  async function loadMoraleCoach() {
    if (!st.attemptId || st.finalized || st.paused) {
      return;
    }
    try {
      const data = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/morale`,
        { headers: studentHeaders() }
      );
      el.moraleTitle.textContent = data.title || "Stay focused";
      el.moraleMessage.textContent = data.message || "You are doing well. Keep going.";
      el.moraleTip.textContent = data.focus_tip || "Read carefully and manage pace.";
    } catch {
      return;
    }
  }

  async function fetchQuestion(sequenceNumber) {
    if (!st.attemptId) {
      setStatus("Start exam first.");
      return;
    }

    const sequence = Number(sequenceNumber);
    if (!Number.isInteger(sequence) || sequence <= 0) {
      setStatus("Invalid question number.");
      return;
    }

    if (st.totalQuestions > 0 && sequence > st.totalQuestions) {
      setStatus("You have reached the last question.");
      return;
    }

    try {
      const data = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/questions/${sequence}`,
        { headers: studentHeaders() }
      );
      renderQuestion(data);
      setStatus(`Question ${sequence} loaded.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function startAttempt() {
    try {
      const examId = el.examSelect.value;
      if (!examId) {
        throw new Error("Please select an exam first.");
      }

      const selectedOption = el.examSelect.options[el.examSelect.selectedIndex];
      st.examId = examId;
      st.examName = selectedOption?.dataset?.examName || selectedOption?.textContent || "Exam";

      const startPayload = await api(`/student/exams/${encodeURIComponent(examId)}/start`, {
        method: "POST",
        headers: studentHeaders(),
      });

      st.attemptId = startPayload.attempt_id;
      st.sequence = 1;
      st.totalQuestions = 0;
      st.currentQuestion = null;
      st.finalized = false;
      st.paused = false;
      st.receipt = null;
      st.broadcastCursor = null;
      st.broadcastHistory = [];
      st.revisionMode = false;
      st.autoSubmitInProgress = false;
      st.lowTimeAlerted.clear();
      st.seenBroadcastIds.clear();
      st.questionTimeBySequence = {};
      st.questionTimeStartedAt = null;
      st.answerTimeline = [];
      st.focusStreak = 0;
      answerState.clear();
      setAutosaveIndicator("local", "Local Draft");
      updateSyncHealthIndicator();
      resetInactivityTimer();
      if (el.printResult) {
        el.printResult.disabled = true;
      }
      if (el.receiptBox) {
        el.receiptBox.textContent = "Acknowledgement receipt will appear here after submission.";
      }
      if (el.broadcastFeed) {
        el.broadcastFeed.textContent = "Waiting for admin broadcast messages...";
      }
      if (el.broadcastBadge) {
        el.broadcastBadge.textContent = "No alerts";
      }
      if (el.turboModeHint) {
        el.turboModeHint.hidden = true;
      }
      renderAnswerTimeline();
      updateMiniProgressWidget();
      if (el.breathingPrompt) {
        el.breathingPrompt.textContent = "Use when you feel rushed. Slow inhale-exhale can stabilize focus.";
      }
      document
        .querySelectorAll('input[name="confidence-tag"]')
        .forEach((input) => {
          if (input instanceof HTMLInputElement) {
            input.checked = false;
          }
        });

      timerState.start(startPayload.expires_at);
      await refreshAttemptStatus();
      await loadExamRules();
      await pullBroadcasts();
      applyCachedAttemptState();

      setAttemptControlsEnabled(true);
      if (st.sequence > 1) {
        await fetchQuestion(st.sequence);
      } else {
        renderQuestion(startPayload.first_question);
      }

      await flushPendingQueue();
      await loadMoraleCoach();
      setStatus("Exam started successfully. Read each question carefully.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function saveAndNext() {
    if (!st.attemptId || !st.currentQuestion || st.finalized || st.paused) {
      setStatus("Active exam attempt required.");
      return;
    }

    const selectedOptionId = rememberCurrentSelection();
    if (!selectedOptionId) {
      setStatus("Please select an option before Save & Next.");
      return;
    }

    const synced = await submitAnswerToServer(st.currentQuestion.id, selectedOptionId, st.sequence);
    st.focusStreak += 1;
    appendAnswerTimeline(synced ? "saved" : "queued_sync", st.sequence);
    updateMiniProgressWidget();
    renderAttemptMeta();

    if (st.totalQuestions > 0 && st.sequence >= st.totalQuestions) {
      setStatus("Answer saved. You are on the last question.");
      return;
    }

    await fetchQuestion(st.sequence + 1);
    await flushPendingQueue();
    await loadMoraleCoach();
  }

  function toggleMarkForReview() {
    if (!st.attemptId || st.finalized || st.paused) {
      return;
    }

    const marked = answerState.toggleMarked(st.sequence);
    if (marked) {
      setStatus(`Question ${st.sequence} marked for review.`);
    } else {
      setStatus(`Question ${st.sequence} removed from review list.`);
    }
    updateMarkReviewLabel();
    renderPalette();
  }

  async function jumpToFirstUnanswered() {
    if (!st.attemptId || st.finalized || st.paused) {
      setStatus("Active exam attempt required.");
      return;
    }
    const total = Number(st.totalQuestions || 0);
    if (!total) {
      setStatus("Question palette is not ready yet.");
      return;
    }

    for (let sequence = 1; sequence <= total; sequence += 1) {
      if (!answerState.isAnsweredSequence(sequence)) {
        await fetchQuestion(sequence);
        setStatus(`Jumped to first unanswered question (#${sequence}).`);
        return;
      }
    }
    setStatus("Great work. No unanswered questions found.");
  }

  async function jumpToSequence() {
    if (!st.attemptId || st.finalized || st.paused) {
      setStatus("Active exam attempt required.");
      return;
    }
    const sequence = Number(el.jumpSequence?.value || 0);
    if (!Number.isInteger(sequence) || sequence <= 0) {
      setStatus("Valid question number enter karo.");
      return;
    }
    if (st.totalQuestions > 0 && sequence > st.totalQuestions) {
      setStatus(`Question range 1-${st.totalQuestions} ke beech hona chahiye.`);
      return;
    }
    await fetchQuestion(sequence);
    setStatus(`Jumped to question #${sequence}.`);
  }

  function openSubmitModal() {
    if (!st.attemptId || st.finalized || st.paused) {
      setStatus("No active exam to submit.");
      return;
    }

    const total = Number(st.totalQuestions || 0);
    const answered = answerState.getAnsweredCount(total);
    const confidenceTagged = answerState.getConfidenceTaggedCount(total);
    const marked = answerState.getMarkedCount();
    const unanswered = Math.max(0, total - answered);
    const pendingSync = answerState.getPendingCount();

    const checklist = [
      {
        label: "Answers reviewed",
        ok: answered > 0,
        detail: `${answered}/${total} answered`,
      },
      {
        label: "No pending sync",
        ok: pendingSync === 0,
        detail: `${pendingSync} pending`,
      },
      {
        label: "Unanswered questions acknowledged",
        ok: unanswered === 0 || !uiPrefs.confirmUnanswered,
        detail: `${unanswered} unanswered`,
      },
      {
        label: "Confidence tags added",
        ok: confidenceTagged > 0,
        detail: `${confidenceTagged}/${total} tagged`,
      },
      {
        label: "Revision mode",
        ok: st.revisionMode,
        detail: st.revisionMode ? "visited" : "not used",
      },
      {
        label: "Time awareness",
        ok: timerState.getRemainingSeconds() > 0,
        detail: timerState.getRemainingText(),
      },
      {
        label: "Tab switch warnings reviewed",
        ok: true,
        detail: `${st.warningCount} warning(s)`,
      },
    ];

    el.submitSummary.innerHTML = `
      <div class="summary-row"><span>Total Questions</span><strong>${esc(total)}</strong></div>
      <div class="summary-row"><span>Marked for Review</span><strong>${esc(marked)}</strong></div>
      ${checklist
        .map(
          (item) => `
            <div class="summary-row ${item.ok ? "check-pass" : "check-warn"}">
              <span>${item.ok ? "PASS" : "WARN"} - ${esc(item.label)}</span>
              <strong>${esc(item.detail)}</strong>
            </div>
          `
        )
        .join("")}
    `;

    el.submitModal.hidden = false;
    syncModalOpenState();
  }

  function closeSubmitModal() {
    el.submitModal.hidden = true;
    syncModalOpenState();
  }

  function applyFinalizationUi(finalizePayload, statusMessage) {
    stopQuestionTimeTracking();
    st.finalized = true;
    st.paused = false;
    st.autoSubmitInProgress = false;
    setAttemptControlsEnabled(false);
    timerState.stop();
    if (st.inactivityTimerId) {
      clearTimeout(st.inactivityTimerId);
      st.inactivityTimerId = null;
    }
    closeInactivityModal();
    if (st.moraleTimerId) {
      clearInterval(st.moraleTimerId);
      st.moraleTimerId = null;
    }
    if (st.broadcastTimerId) {
      clearInterval(st.broadcastTimerId);
      st.broadcastTimerId = null;
    }
    if (st.attemptStatusTimerId) {
      clearInterval(st.attemptStatusTimerId);
      st.attemptStatusTimerId = null;
    }
    stopBreathingPrompt();
    clearAttemptCache();
    setAutosaveIndicator("synced", "Finalized");
    if (el.lowTimeAlert) {
      el.lowTimeAlert.hidden = true;
    }
    if (el.turboModeHint) {
      el.turboModeHint.hidden = true;
    }

    renderResultSummary(finalizePayload.result || finalizePayload);
    st.receipt = buildAcknowledgementReceipt(finalizePayload.result || finalizePayload);
    renderReceipt(st.receipt);
    setStatus(statusMessage);
    renderAttemptMeta({
      started_at: null,
      expires_at: timerState.getExpiresAt(),
      status: "FINALIZED",
    });
    closeSubmitModal();
  }

  async function autoSubmitExpiredAttempt() {
    if (!st.attemptId || st.finalized || st.autoSubmitInProgress) {
      return;
    }
    st.autoSubmitInProgress = true;
    setStatus("Time is over. Auto-submitting exam...");
    try {
      await flushPendingQueue();
      const finalizePayload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/auto-submit`,
        {
          method: "POST",
          headers: studentHeaders(),
        }
      );
      applyFinalizationUi(finalizePayload, "Time over. Exam auto-submitted successfully.");
    } catch (error) {
      st.autoSubmitInProgress = false;
      setStatus(`Time over. Auto-submit failed: ${error.message}. Contact admin.`);
    }
  }

  async function confirmSubmitExam() {
    if (!st.attemptId || st.finalized || st.paused) {
      closeSubmitModal();
      return;
    }

    el.confirmSubmit.disabled = true;
    try {
      await flushPendingQueue();
      if (answerState.getPendingCount() > 0) {
        setStatus("Some answers are still waiting for LAN sync. Please wait and retry submit.");
        return;
      }

      const total = Number(st.totalQuestions || 0);
      const answered = answerState.getAnsweredCount(total);
      const unanswered = Math.max(0, total - answered);
      if (uiPrefs.confirmUnanswered && unanswered > 0) {
        const proceed = window.confirm(
          `You still have ${unanswered} unanswered question(s). Submit anyway?`
        );
        if (!proceed) {
          setStatus("Submission cancelled. Please review unanswered questions.");
          return;
        }
      }

      const finalizePayload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/finalize`,
        {
          method: "POST",
          headers: studentHeaders(),
        }
      );
      applyFinalizationUi(finalizePayload, "Exam submitted successfully.");
    } catch (error) {
      setStatus(error.message);
    } finally {
      el.confirmSubmit.disabled = false;
    }
  }

  async function viewResult() {
    if (!st.attemptId) {
      setStatus("No attempt found.");
      return;
    }
    try {
      const resultPayload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/result`,
        { headers: studentHeaders() }
      );
      renderResultSummary(resultPayload);
      if (!st.receipt) {
        st.receipt = buildAcknowledgementReceipt(resultPayload);
      }
      renderReceipt(st.receipt);
      setStatus("Result loaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function logoutStudent() {
    timerState.stop();
    stopQuestionTimeTracking();
    if (st.syncIntervalId) {
      clearInterval(st.syncIntervalId);
      st.syncIntervalId = null;
    }
    if (st.moraleTimerId) {
      clearInterval(st.moraleTimerId);
      st.moraleTimerId = null;
    }
    if (st.inactivityTimerId) {
      clearTimeout(st.inactivityTimerId);
      st.inactivityTimerId = null;
    }
    if (st.heartbeatTimerId) {
      clearInterval(st.heartbeatTimerId);
      st.heartbeatTimerId = null;
    }
    if (st.broadcastTimerId) {
      clearInterval(st.broadcastTimerId);
      st.broadcastTimerId = null;
    }
    if (st.attemptStatusTimerId) {
      clearInterval(st.attemptStatusTimerId);
      st.attemptStatusTimerId = null;
    }
    stopBreathingPrompt();
    closeInactivityModal();
    localStorage.removeItem(STUDENT_SESSION_KEY);
    window.location.href = "/web?target=student&reason=login_required";
  }

  async function restoreLatestCachedAttempt() {
    const cached = findLatestCachedAttemptForStudent();
    if (!cached) {
      return;
    }

    st.attemptId = String(cached.attempt_id);
    st.examId = String(cached.exam_id || "");
    st.examName = String(cached.exam_name || st.examId || "Exam");
    st.sequence = Number(cached.sequence || 1);
    st.totalQuestions = Number(cached.total_questions || 0);
    st.finalized = false;
    st.paused = Boolean(cached.paused);
    st.autoSubmitInProgress = false;
    st.lowTimeAlerted.clear();
    st.focusStreak = Number.isFinite(Number(cached.focus_streak))
      ? Math.max(0, Math.floor(Number(cached.focus_streak)))
      : 0;
    st.questionTimeBySequence =
      cached.question_time_by_sequence && typeof cached.question_time_by_sequence === "object"
        ? { ...cached.question_time_by_sequence }
        : {};
    st.answerTimeline = Array.isArray(cached.answer_timeline)
      ? cached.answer_timeline.slice(-120).map((item) => ({
          sequence: Number(item.sequence || 0),
          action: String(item.action || "updated"),
          at: item.at || new Date().toISOString(),
        }))
      : [];
    st.seenBroadcastIds = new Set(
      Array.isArray(cached.seen_broadcast_ids) ? cached.seen_broadcast_ids.map(String) : []
    );
    st.broadcastHistory = Array.isArray(cached.broadcast_history)
      ? cached.broadcast_history
          .slice(-50)
          .map((item) => ({
            id: item.id,
            created_at: item.created_at,
            message: item.message,
            severity: item.severity || "info",
          }))
          .filter((item) => item.id && item.created_at)
      : [];

    answerState.hydrate(cached);
    timerState.start(cached.expires_at || null);
    renderAnswerTimeline();
    renderBroadcasts(st.broadcastHistory);
    updateMiniProgressWidget();

    try {
      const statusPayload = await refreshAttemptStatus();
      const normalized = String(statusPayload?.status || "").toUpperCase();
      if (statusPayload && normalized === "ACTIVE") {
        setAttemptControlsEnabled(true);
        const sequenceToLoad = Math.max(1, Math.min(st.sequence, st.totalQuestions || st.sequence));
        await fetchQuestion(sequenceToLoad);
        await flushPendingQueue();
        await loadExamRules();
        await pullBroadcasts();
        await loadMoraleCoach();
        resetInactivityTimer();
        setAutosaveIndicator(
          answerState.getPendingCount() > 0 ? "pending" : "local",
          answerState.getPendingCount() > 0 ? "Pending LAN Sync" : "Recovered Draft"
        );
        updateSyncHealthIndicator();
        setStatus("Recovered your local in-progress attempt.");
      } else if (normalized === "PAUSED") {
        setAttemptControlsEnabled(false);
        setStatus("Recovered paused attempt. Wait for admin resume.");
      }
    } catch {
      renderAttemptMeta();
      updateProgress();
      renderPalette();
      setStatus("Recovered local answer draft. Start exam to continue syncing.");
    }
  }

  function bindEvents() {
    el.logoutStudent.addEventListener("click", logoutStudent);
    el.loadExams.addEventListener("click", loadExams);
    el.startAttempt.addEventListener("click", startAttempt);
    el.openOnboarding.addEventListener("click", () => {
      openOnboardingModal();
    });
    if (el.openShortcuts) {
      el.openShortcuts.addEventListener("click", () => {
        openShortcutsModal();
      });
    }
    el.dismissOnboarding.addEventListener("click", () => {
      dismissOnboardingModal(true);
    });
    if (el.closeShortcuts) {
      el.closeShortcuts.addEventListener("click", () => {
        closeShortcutsModal();
      });
    }
    el.continueAfterInactive.addEventListener("click", () => {
      closeInactivityModal();
      resetInactivityTimer();
      setStatus("Inactivity warning cleared. Continue answering.");
    });
    el.fontSizeSelect.addEventListener("change", () => {
      uiPrefs.fontScale = el.fontSizeSelect.value;
      applyUiPrefs();
      persistUiPrefs();
    });
    el.highContrastToggle.addEventListener("change", () => {
      uiPrefs.highContrast = Boolean(el.highContrastToggle.checked);
      applyUiPrefs();
      persistUiPrefs();
    });
    el.confirmUnansweredToggle.addEventListener("change", () => {
      uiPrefs.confirmUnanswered = Boolean(el.confirmUnansweredToggle.checked);
      persistUiPrefs();
    });
    el.questionZoomIn.addEventListener("click", () => {
      setQuestionZoom(uiPrefs.questionZoom + 10);
    });
    el.questionZoomOut.addEventListener("click", () => {
      setQuestionZoom(uiPrefs.questionZoom - 10);
    });
    el.questionZoomReset.addEventListener("click", () => {
      setQuestionZoom(100);
    });

    el.prevQuestion.addEventListener("click", () => {
      fetchQuestion(st.sequence - 1);
    });

    el.saveNext.addEventListener("click", saveAndNext);
    el.markReview.addEventListener("click", toggleMarkForReview);
    el.reportQuestionIssue.addEventListener("click", reportQuestionIssue);
    el.reportTechnicalIssue.addEventListener("click", reportTechnicalIssue);
    el.jumpUnanswered.addEventListener("click", jumpToFirstUnanswered);
    el.jumpSequenceBtn.addEventListener("click", jumpToSequence);
    el.jumpSequence.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        jumpToSequence();
      }
    });
    el.filterAll.addEventListener("click", () => setPaletteFilter("all"));
    el.filterAnswered.addEventListener("click", () => setPaletteFilter("answered"));
    el.filterUnanswered.addEventListener("click", () => setPaletteFilter("unanswered"));
    el.filterReview.addEventListener("click", () => setPaletteFilter("review"));
    el.toggleFaq.addEventListener("click", toggleFaq);
    el.toggleRules.addEventListener("click", toggleRules);
    el.startBreathing.addEventListener("click", startBreathingPrompt);
    el.runDiagnostics.addEventListener("click", runDeviceDiagnostics);
    el.enterRevision.addEventListener("click", enterRevisionMode);
    el.printResult.addEventListener("click", printResultSlip);
    el.submitExam.addEventListener("click", openSubmitModal);
    el.cancelSubmit.addEventListener("click", closeSubmitModal);
    el.confirmSubmit.addEventListener("click", confirmSubmitExam);
    el.viewResult.addEventListener("click", viewResult);
    el.refreshMorale.addEventListener("click", loadMoraleCoach);

    el.optionsList.addEventListener("change", (event) => {
      const input = event.target;
      if (!(input instanceof HTMLInputElement)) {
        return;
      }
      if (input.name !== "selected-option") {
        return;
      }
      rememberCurrentSelection();
      setStatus("Answer saved locally.");
      resetInactivityTimer();
    });

    document
      .querySelectorAll('input[name="confidence-tag"]')
      .forEach((input) => {
        if (!(input instanceof HTMLInputElement)) {
          return;
        }
        input.addEventListener("change", () => {
          if (!st.currentQuestion) {
            return;
          }
          answerState.setConfidence(st.currentQuestion.id, input.value || null);
          setStatus(`Confidence tagged as '${input.value || "none"}'.`);
        });
      });

    el.questionPalette.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const button = target.closest("button[data-sequence]");
      if (!button) {
        return;
      }
      const sequence = Number(button.dataset.sequence);
      fetchQuestion(sequence);
      resetInactivityTimer();
    });

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        resetInactivityTimer();
        return;
      }
      st.warningCount += 1;
      showAntiCheatWarning(
        `Warning ${st.warningCount}: Tab switch detected. Stay on exam screen.`
      );
    });

    document.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      showAntiCheatWarning("Right-click is disabled during the exam.");
    });

    const activityEvents = ["mousemove", "mousedown", "keydown", "touchstart", "wheel"];
    activityEvents.forEach((eventName) => {
      document.addEventListener(eventName, resetInactivityTimer, { passive: true });
    });
    document.addEventListener("keydown", () => {
      st.diagnostics.keyboardSeen = true;
    });
    document.addEventListener("mousemove", () => {
      st.diagnostics.mouseSeen = true;
    });

    window.addEventListener("online", () => {
      flushPendingQueue();
      setStatus("LAN reconnected. Syncing saved answers...");
      updateSyncHealthIndicator();
      pingServerHeartbeat();
      pullBroadcasts();
    });

    window.addEventListener("offline", () => {
      updateSyncHealthIndicator();
      updateHeartbeatIndicator("offline", "Server: Unreachable");
    });

    window.addEventListener("beforeunload", (event) => {
      if (st.attemptId && !st.finalized) {
        event.preventDefault();
        event.returnValue = "";
      }
      timerState.stop();
      if (st.syncIntervalId) {
        clearInterval(st.syncIntervalId);
      }
      if (st.moraleTimerId) {
        clearInterval(st.moraleTimerId);
      }
      if (st.inactivityTimerId) {
        clearTimeout(st.inactivityTimerId);
      }
      if (st.heartbeatTimerId) {
        clearInterval(st.heartbeatTimerId);
      }
      if (st.broadcastTimerId) {
        clearInterval(st.broadcastTimerId);
      }
      if (st.attemptStatusTimerId) {
        clearInterval(st.attemptStatusTimerId);
      }
      stopQuestionTimeTracking();
      stopBreathingPrompt();
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !el.submitModal.hidden) {
        closeSubmitModal();
        return;
      }
      if (event.key === "Escape" && !el.onboardingModal.hidden) {
        dismissOnboardingModal(true);
        return;
      }
      if (event.key === "Escape" && !el.inactivityModal.hidden) {
        closeInactivityModal();
        resetInactivityTimer();
        return;
      }
      if (event.key === "Escape" && el.shortcutsModal && !el.shortcutsModal.hidden) {
        closeShortcutsModal();
        return;
      }
      const target = event.target;
      const isInputTarget =
        target instanceof HTMLInputElement ||
        target instanceof HTMLSelectElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLButtonElement;
      if (event.key === "?" && !isInputTarget) {
        event.preventDefault();
        openShortcutsModal();
        return;
      }
      if (!st.attemptId || st.finalized || st.paused) {
        return;
      }
      if (
        isInputTarget
      ) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === "m") {
        event.preventDefault();
        toggleMarkForReview();
      } else if (key === "n") {
        event.preventDefault();
        saveAndNext();
      } else if (key === "j") {
        event.preventDefault();
        jumpToFirstUnanswered();
      }
    });

    st.syncIntervalId = window.setInterval(() => {
      flushPendingQueue();
      updateSyncHealthIndicator();
    }, 8000);

    st.moraleTimerId = window.setInterval(() => {
      loadMoraleCoach();
    }, 20000);

    st.attemptStatusTimerId = window.setInterval(() => {
      if (!st.attemptId || st.finalized) {
        return;
      }
      refreshAttemptStatus().catch(() => {
        return;
      });
    }, ATTEMPT_STATUS_INTERVAL_MS);
  }

  async function initialize() {
    ensureSession();
    readUiPrefs();
    applyUiPrefs();
    el.examName.textContent = "Exam Name";
    setMoralePlaceholder();
    renderPalette();
    updateProgress();
    setAttemptControlsEnabled(false);
    if (el.printResult) {
      el.printResult.disabled = true;
    }
    if (el.lowTimeAlert) {
      el.lowTimeAlert.hidden = true;
    }
    if (el.turboModeHint) {
      el.turboModeHint.hidden = true;
    }
    if (el.faqContent) {
      el.faqContent.hidden = true;
    }
    if (el.toggleFaq) {
      el.toggleFaq.textContent = "Show";
    }
    if (el.rulesContent) {
      el.rulesContent.hidden = true;
      el.rulesContent.innerHTML = "<p>Rules will load after exam start.</p>";
    }
    if (el.toggleRules) {
      el.toggleRules.textContent = "Show";
    }
    if (el.broadcastFeed) {
      el.broadcastFeed.textContent = "No broadcast messages yet.";
    }
    if (el.broadcastBadge) {
      el.broadcastBadge.textContent = "No alerts";
    }
    st.broadcastHistory = [];
    if (el.shortcutsModal) {
      el.shortcutsModal.hidden = true;
    }
    renderAnswerTimeline();
    updateMiniProgressWidget();
    setAutosaveIndicator("synced", "Waiting");
    updateSyncHealthIndicator();
    updateHeartbeatIndicator("degraded", "Server: Checking...");
    bindEvents();
    maybeShowOnboarding();

    await loadVersion();
    await pingServerHeartbeat();
    st.heartbeatTimerId = window.setInterval(() => {
      pingServerHeartbeat();
    }, HEARTBEAT_INTERVAL_MS);
    st.broadcastTimerId = window.setInterval(() => {
      pullBroadcasts();
    }, BROADCAST_INTERVAL_MS);
    await loadExams();
    await restoreLatestCachedAttempt();
  }

  initialize().catch((error) => {
    setStatus(error.message || "Initialization failed.");
  });
})();
