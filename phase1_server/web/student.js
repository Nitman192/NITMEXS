(() => {
  const STUDENT_SESSION_KEY = "nitmexs_student_session";
  const ATTEMPT_CACHE_PREFIX = "nitmexs_attempt_cache_";
  const STUDENT_ONBOARDING_KEY = "nitmexs_student_onboarding_seen";
  const STUDENT_UI_PREFS_KEY = "nitmexs_student_ui_prefs";
  const INACTIVITY_TIMEOUT_MS = 120000;

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
    syncIntervalId: null,
    warningTimeoutId: null,
    moraleTimerId: null,
    inactivityTimerId: null,
    inactivityModalOpen: false,
    lowTimeAlerted: new Set(),
  };

  const $ = (id) => document.getElementById(id);

  const el = {
    version: $("version"),
    sessionStudent: $("session-student"),
    logoutStudent: $("logout-student"),
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
    submitSummary: $("submit-summary"),
    cancelSubmit: $("cancel-submit"),
    confirmSubmit: $("confirm-submit"),
    onboardingModal: $("onboarding-modal"),
    dismissOnboarding: $("dismiss-onboarding"),
    openOnboarding: $("open-onboarding"),
    fontSizeSelect: $("font-size-select"),
    highContrastToggle: $("high-contrast-toggle"),
    autosaveIndicator: $("autosave-indicator"),
    syncHealthIndicator: $("sync-health-indicator"),
    lowTimeAlert: $("low-time-alert"),
    questionZoomOut: $("question-zoom-out"),
    questionZoomIn: $("question-zoom-in"),
    questionZoomReset: $("question-zoom-reset"),
    questionZoomLabel: $("question-zoom-label"),
    jumpUnanswered: $("jump-unanswered"),
    inactivityModal: $("inactivity-modal"),
    continueAfterInactive: $("continue-after-inactive"),
  };

  const uiPrefs = {
    fontScale: "normal",
    highContrast: false,
    questionZoom: 100,
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
        saved_at: item.saved_at || new Date().toISOString(),
      };
    };

    return {
      clear() {
        draftAnswers = {};
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
    if (st.attemptId && !st.finalized && remainingSeconds > 0) {
      evaluateLowTimeAlerts(remainingSeconds);
    }
    if (remainingSeconds === 0 && st.attemptId && !st.finalized) {
      setStatus("Time is over. Submit Exam to lock your attempt.");
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
      !el.inactivityModal.hidden;
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
      }
    }
  }

  function openInactivityModal() {
    if (!st.attemptId || st.finalized || st.inactivityModalOpen) {
      return;
    }
    st.inactivityModalOpen = true;
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
    if (!st.attemptId || st.finalized) {
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
      if (cache.exam_name) {
        st.examName = String(cache.exam_name);
      }
      if (cache.expires_at) {
        timerState.start(cache.expires_at);
      }
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
    el.prevQuestion.disabled = st.sequence <= 1 || st.finalized;
  }

  function renderPalette() {
    const total = Number(st.totalQuestions || 0);
    if (!total) {
      el.questionPalette.innerHTML = '<p class="palette-placeholder">Question palette will appear after exam start.</p>';
      return;
    }

    const paletteButtons = [];
    for (let sequence = 1; sequence <= total; sequence += 1) {
      const marked = answerState.isMarked(sequence);
      const answered = answerState.isAnsweredSequence(sequence);
      const stateClass = marked ? "review" : answered ? "answered" : "unanswered";
      const currentClass = sequence === st.sequence ? "current" : "";
      paletteButtons.push(
        `<button type="button" class="palette-btn ${stateClass} ${currentClass}" data-sequence="${sequence}">${sequence}</button>`
      );
    }
    el.questionPalette.innerHTML = paletteButtons.join("");
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
    st.currentQuestion = payload.question;
    st.sequence = Number(payload.sequence_number);
    answerState.setSequenceQuestion(st.sequence, payload.question.id);

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

    updateMarkReviewLabel();
    updateProgress();
    renderPalette();
    persistAttemptCache();
    resetInactivityTimer();
  }

  function setAttemptControlsEnabled(enabled) {
    const active = Boolean(enabled) && !st.finalized;
    el.markReview.disabled = !active;
    el.prevQuestion.disabled = !active || st.sequence <= 1;
    el.saveNext.disabled = !active;
    el.submitExam.disabled = !active;
    el.jumpUnanswered.disabled = !active;
  }

  function currentlySelectedOptionId() {
    const selected = el.optionsList.querySelector('input[name="selected-option"]:checked');
    return selected ? selected.value : "";
  }

  function rememberCurrentSelection() {
    if (!st.currentQuestion) {
      return "";
    }
    const selectedOptionId = currentlySelectedOptionId();
    if (!selectedOptionId) {
      return "";
    }
    answerState.rememberSelection(st.currentQuestion.id, selectedOptionId);
    setAutosaveIndicator("local", "Saved Locally");
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

    if ((statusPayload.status || "").toUpperCase() !== "ACTIVE") {
      st.finalized = true;
      setAttemptControlsEnabled(false);
    }

    updateProgress();
    renderPalette();
    return statusPayload;
  }

  async function loadMoraleCoach() {
    if (!st.attemptId || st.finalized) {
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
      st.lowTimeAlerted.clear();
      answerState.clear();
      setAutosaveIndicator("local", "Local Draft");
      updateSyncHealthIndicator();
      resetInactivityTimer();

      timerState.start(startPayload.expires_at);
      await refreshAttemptStatus();
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
    if (!st.attemptId || !st.currentQuestion || st.finalized) {
      setStatus("Active exam attempt required.");
      return;
    }

    const selectedOptionId = rememberCurrentSelection();
    if (!selectedOptionId) {
      setStatus("Please select an option before Save & Next.");
      return;
    }

    await submitAnswerToServer(st.currentQuestion.id, selectedOptionId, st.sequence);
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
    if (!st.attemptId || st.finalized) {
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
    if (!st.attemptId || st.finalized) {
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

  function openSubmitModal() {
    if (!st.attemptId || st.finalized) {
      setStatus("No active exam to submit.");
      return;
    }

    const total = Number(st.totalQuestions || 0);
    const answered = answerState.getAnsweredCount(total);
    const marked = answerState.getMarkedCount();
    const unanswered = Math.max(0, total - answered);
    const pendingSync = answerState.getPendingCount();

    el.submitSummary.innerHTML = `
      <div class="summary-row"><span>Total Questions</span><strong>${esc(total)}</strong></div>
      <div class="summary-row"><span>Answered</span><strong>${esc(answered)}</strong></div>
      <div class="summary-row"><span>Unanswered</span><strong>${esc(unanswered)}</strong></div>
      <div class="summary-row"><span>Marked for Review</span><strong>${esc(marked)}</strong></div>
      <div class="summary-row"><span>Pending Sync</span><strong>${esc(pendingSync)}</strong></div>
      <div class="summary-row"><span>Time Left</span><strong>${esc(timerState.getRemainingText())}</strong></div>
      <div class="summary-row"><span>Tab Switch Warnings</span><strong>${esc(st.warningCount)}</strong></div>
    `;

    el.submitModal.hidden = false;
    syncModalOpenState();
  }

  function closeSubmitModal() {
    el.submitModal.hidden = true;
    syncModalOpenState();
  }

  async function confirmSubmitExam() {
    if (!st.attemptId || st.finalized) {
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

      const finalizePayload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/finalize`,
        {
          method: "POST",
          headers: studentHeaders(),
        }
      );

      st.finalized = true;
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
      clearAttemptCache();
      setAutosaveIndicator("synced", "Finalized");
      if (el.lowTimeAlert) {
        el.lowTimeAlert.hidden = true;
      }

      renderResultSummary(finalizePayload.result || finalizePayload);
      setStatus("Exam submitted successfully.");
      renderAttemptMeta({
        started_at: null,
        expires_at: timerState.getExpiresAt(),
        status: "FINALIZED",
      });
      closeSubmitModal();
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
      setStatus("Result loaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function logoutStudent() {
    timerState.stop();
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
    st.lowTimeAlerted.clear();

    answerState.hydrate(cached);
    timerState.start(cached.expires_at || null);

    try {
      const statusPayload = await refreshAttemptStatus();
      if (statusPayload && (statusPayload.status || "").toUpperCase() === "ACTIVE") {
        setAttemptControlsEnabled(true);
        const sequenceToLoad = Math.max(1, Math.min(st.sequence, st.totalQuestions || st.sequence));
        await fetchQuestion(sequenceToLoad);
        await flushPendingQueue();
        await loadMoraleCoach();
        resetInactivityTimer();
        setAutosaveIndicator(
          answerState.getPendingCount() > 0 ? "pending" : "local",
          answerState.getPendingCount() > 0 ? "Pending LAN Sync" : "Recovered Draft"
        );
        updateSyncHealthIndicator();
        setStatus("Recovered your local in-progress attempt.");
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
    el.dismissOnboarding.addEventListener("click", () => {
      dismissOnboardingModal(true);
    });
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
    el.jumpUnanswered.addEventListener("click", jumpToFirstUnanswered);
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

    window.addEventListener("online", () => {
      flushPendingQueue();
      setStatus("LAN reconnected. Syncing saved answers...");
      updateSyncHealthIndicator();
    });

    window.addEventListener("offline", () => {
      updateSyncHealthIndicator();
    });

    window.addEventListener("beforeunload", () => {
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
      if (!st.attemptId || st.finalized) {
        return;
      }
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLSelectElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLButtonElement
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
    if (el.lowTimeAlert) {
      el.lowTimeAlert.hidden = true;
    }
    setAutosaveIndicator("synced", "Waiting");
    updateSyncHealthIndicator();
    bindEvents();
    maybeShowOnboarding();

    await loadVersion();
    await loadExams();
    await restoreLatestCachedAttempt();
  }

  initialize().catch((error) => {
    setStatus(error.message || "Initialization failed.");
  });
})();
