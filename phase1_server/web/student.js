(() => {
  const STUDENT_SESSION_KEY = "nitmexs_student_session";
  const ATTEMPT_CACHE_PREFIX = "nitmexs_attempt_cache_";
  const RESULT_HISTORY_PREFIX = "nitmexs_result_history_";
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
    currentQuestionOptions: [],
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
    translateMode: false,
    predownloadedCount: 0,
    heartbeatHistory: [],
    syncRetryCount: 0,
    lastSyncError: "",
    clipboardLogs: [],
    tabSwitchReasons: [],
    hiddenSince: null,
    optionMode: "none",
    dragDropMode: false,
    conflictPending: null,
    conflictResolver: null,
    resumeWizardResolver: null,
    examTipsIndex: 0,
    tipsTimerId: null,
    questionTopicById: {},
    codeDraftByQuestion: {},
    inputLatencySamples: [],
    stressLevel: "normal",
    diagramStrokeActive: false,
    captionSize: 16,
    uiStage: "lobby",
    analysisTab: "summary",
    latestResult: null,
    latestAnalysis: null,
    analysisExplanationByQuestion: {},
    availableExams: [],
    utilityTab: "palette",
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
    toggleEliminateMode: $("toggle-eliminate-mode"),
    toggleStrikeMode: $("toggle-strike-mode"),
    submitExam: $("submit-exam"),
    viewResult: $("view-result"),
    resultBox: $("result-box"),
    resultExplainBox: $("result-explain-box"),
    attemptCompareBox: $("attempt-compare-box"),
    antiCheatWarning: $("anti-cheat-warning"),
    submitModal: $("submit-modal"),
    shortcutsModal: $("shortcuts-modal"),
    submitSummary: $("submit-summary"),
    cancelSubmit: $("cancel-submit"),
    closeShortcuts: $("close-shortcuts"),
    confirmSubmit: $("confirm-submit"),
    resumeWizardModal: $("resume-wizard-modal"),
    resumeWizardSummary: $("resume-wizard-summary"),
    resumeFromCache: $("resume-from-cache"),
    discardCacheStartFresh: $("discard-cache-start-fresh"),
    glossaryModal: $("glossary-modal"),
    openGlossary: $("open-glossary"),
    closeGlossary: $("close-glossary"),
    glossaryContent: $("glossary-content"),
    conflictModal: $("conflict-modal"),
    conflictKeepLocal: $("conflict-keep-local"),
    conflictReloadServer: $("conflict-reload-server"),
    onboardingModal: $("onboarding-modal"),
    dismissOnboarding: $("dismiss-onboarding"),
    openOnboarding: $("open-onboarding"),
    fontSizeSelect: $("font-size-select"),
    highContrastToggle: $("high-contrast-toggle"),
    colorblindToggle: $("colorblind-toggle"),
    reducedMotionToggle: $("reduced-motion-toggle"),
    largeCursorToggle: $("large-cursor-toggle"),
    confirmUnansweredToggle: $("confirm-unanswered-toggle"),
    soundAlertToggle: $("sound-alert-toggle"),
    soundVolume: $("sound-volume"),
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
    toggleHardBucket: $("toggle-hard-bucket"),
    toggleEasyBucket: $("toggle-easy-bucket"),
    bucketSummary: $("bucket-summary"),
    predownloadQuestions: $("predownload-questions"),
    fullscreenRetry: $("fullscreen-retry"),
    replayRules: $("replay-rules"),
    toggleTranslate: $("toggle-translate"),
    instantSupport: $("instant-support"),
    roughPad: $("rough-pad"),
    integrityHash: $("integrity-hash"),
    networkQuality: $("network-quality"),
    syncDiagnostics: $("sync-diagnostics"),
    tipsFeed: $("tips-feed"),
    emergencyContactLink: $("emergency-contact-link"),
    clipboardLog: $("clipboard-log"),
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
    inputLatencyMeter: $("input-latency-meter"),
    stressDetector: $("stress-detector"),
    clearDiagram: $("clear-diagram"),
    diagramCanvas: $("diagram-canvas"),
    toggleCalmMode: $("toggle-calm-mode"),
    calmModeOverlay: $("calm-mode-overlay"),
    closeCalmMode: $("close-calm-mode"),
    runPracticeSim: $("run-practice-sim"),
    runMockAnalytics: $("run-mock-analytics"),
    practiceSimBox: $("practice-sim-box"),
    mockAnalyticsBox: $("mock-analytics-box"),
    equationEditor: $("equation-editor"),
    equationPreview: $("equation-preview"),
    codeLanguage: $("code-language"),
    codeEditor: $("code-editor"),
    playQuestionAudio: $("play-question-audio"),
    captionSize: $("caption-size"),
    captionPreview: $("caption-preview"),
    enableDragDropOptions: $("enable-drag-drop-options"),
    generateMatchMode: $("generate-match-mode"),
    matchModeBox: $("match-mode-box"),
    receiptQrBox: $("receipt-qr-box"),
    topicStrengthBox: $("topic-strength-box"),
    weakTopicPlanBox: $("weak-topic-plan-box"),
    previewRules: $("preview-rules"),
    preExamRulesBox: $("pre-exam-rules-box"),
    stageLobby: $("student-stage-lobby"),
    stageExam: $("student-stage-exam"),
    stageAnalysis: $("student-stage-analysis"),
    stagePillLobby: $("stage-pill-lobby"),
    stagePillExam: $("stage-pill-exam"),
    stagePillAnalysis: $("stage-pill-analysis"),
    resultTabSummary: $("result-tab-summary"),
    resultTabAi: $("result-tab-ai"),
    resultSummaryPanel: $("result-summary-panel"),
    resultAnalysisPanel: $("result-analysis-panel"),
    analysisOverviewBox: $("analysis-overview-box"),
    analysisLearningPathBox: $("analysis-learning-path-box"),
    analysisListBox: $("analysis-list-box"),
    examUtilityHub: $("exam-utility-hub"),
    utilityTabPalette: $("utility-tab-palette"),
    utilityTabWorkspace: $("utility-tab-workspace"),
    utilityTabMonitor: $("utility-tab-monitor"),
    utilityTabSupport: $("utility-tab-support"),
    utilityPanelPalette: $("utility-panel-palette"),
    utilityPanelWorkspace: $("utility-panel-workspace"),
    utilityPanelMonitor: $("utility-panel-monitor"),
    utilityPanelSupport: $("utility-panel-support"),
  };

  const uiPrefs = {
    fontScale: "normal",
    highContrast: false,
    colorblind: false,
    reducedMotion: false,
    largeCursor: false,
    questionZoom: 100,
    confirmUnanswered: true,
    soundAlerts: true,
    soundVolume: 60,
  };

  function setStage(nextStage) {
    st.uiStage = nextStage;
    if (el.stageLobby) {
      el.stageLobby.hidden = nextStage !== "lobby";
    }
    if (el.stageExam) {
      el.stageExam.hidden = nextStage !== "exam";
    }
    if (el.stageAnalysis) {
      el.stageAnalysis.hidden = nextStage !== "analysis";
    }

    const examReady = Boolean(st.attemptId);
    const analysisReady = Boolean(st.finalized || st.latestResult);
    const stageMap = {
      lobby: el.stagePillLobby,
      exam: el.stagePillExam,
      analysis: el.stagePillAnalysis,
    };

    Object.entries(stageMap).forEach(([name, node]) => {
      if (!(node instanceof HTMLButtonElement)) {
        return;
      }
      node.classList.toggle("active", name === nextStage);
      node.setAttribute("aria-current", name === nextStage ? "step" : "false");
      if (name === "exam") {
        node.disabled = !examReady;
      } else if (name === "analysis") {
        node.disabled = !analysisReady;
      } else {
        node.disabled = false;
      }
    });
  }

  function setResultTab(nextTab) {
    st.analysisTab = nextTab === "ai" ? "ai" : "summary";
    if (el.resultSummaryPanel) {
      el.resultSummaryPanel.hidden = st.analysisTab !== "summary";
    }
    if (el.resultAnalysisPanel) {
      el.resultAnalysisPanel.hidden = st.analysisTab !== "ai";
    }
    if (el.resultTabSummary) {
      el.resultTabSummary.classList.toggle("active", st.analysisTab === "summary");
      el.resultTabSummary.setAttribute(
        "aria-selected",
        st.analysisTab === "summary" ? "true" : "false"
      );
    }
    if (el.resultTabAi) {
      el.resultTabAi.classList.toggle("active", st.analysisTab === "ai");
      el.resultTabAi.setAttribute(
        "aria-selected",
        st.analysisTab === "ai" ? "true" : "false"
      );
    }
  }

  function setUtilityTab(nextTab) {
    st.utilityTab = ["palette", "workspace", "monitor", "support"].includes(nextTab)
      ? nextTab
      : "palette";
    const tabMap = {
      palette: el.utilityTabPalette,
      workspace: el.utilityTabWorkspace,
      monitor: el.utilityTabMonitor,
      support: el.utilityTabSupport,
    };
    const panelMap = {
      palette: el.utilityPanelPalette,
      workspace: el.utilityPanelWorkspace,
      monitor: el.utilityPanelMonitor,
      support: el.utilityPanelSupport,
    };

    Object.entries(tabMap).forEach(([name, node]) => {
      if (!(node instanceof HTMLButtonElement)) {
        return;
      }
      node.classList.toggle("active", name === st.utilityTab);
      node.setAttribute("aria-selected", name === st.utilityTab ? "true" : "false");
    });
    Object.entries(panelMap).forEach(([name, node]) => {
      if (!node) {
        return;
      }
      node.hidden = name !== st.utilityTab;
    });
  }

  function initializeExamUtilityHub() {
    if (!el.examUtilityHub) {
      return;
    }
    const groupMap = {
      palette: [
        ".palette-card",
      ],
      workspace: [
        ".roughpad-card",
        ".diagram-card",
        ".advanced-card",
      ],
      monitor: [
        ".tools-card",
        ".strategy-card",
        ".timeline-card",
        ".clipboard-card",
      ],
      support: [
        ".morale-card",
        ".rules-card",
        ".broadcast-card",
        ".faq-card",
        ".tips-card",
        ".stress-card",
      ],
    };
    const panelByGroup = {
      palette: el.utilityPanelPalette,
      workspace: el.utilityPanelWorkspace,
      monitor: el.utilityPanelMonitor,
      support: el.utilityPanelSupport,
    };

    Object.entries(groupMap).forEach(([group, selectors]) => {
      const panel = panelByGroup[group];
      if (!panel) {
        return;
      }
      selectors.forEach((selector) => {
        const node = document.querySelector(selector);
        if (!(node instanceof HTMLElement)) {
          return;
        }
        panel.appendChild(node);
      });
    });

    setUtilityTab(st.utilityTab || "palette");
  }

  function getSelectedExamMeta() {
    const examId = el.examSelect?.value || "";
    const selectedOption = el.examSelect?.options?.[el.examSelect.selectedIndex];
    const fromState = st.availableExams.find((exam) => String(exam.id) === String(examId));
    return {
      exam_id: examId || "",
      exam_name:
        fromState?.name ||
        selectedOption?.dataset?.examName ||
        selectedOption?.textContent ||
        "Selected exam",
      duration_minutes:
        Number(fromState?.duration_minutes) ||
        Number(selectedOption?.dataset?.durationMinutes) ||
        null,
    };
  }

  function renderPreExamRulesPreview(data = null) {
    if (!el.preExamRulesBox) {
      return;
    }
    const examMeta = data || getSelectedExamMeta();
    const rules = Array.isArray(examMeta?.rules) && examMeta.rules.length
      ? examMeta.rules
      : [
          "Read each question carefully before selecting an option.",
          "Run device diagnostics before entering the exam.",
          "Keep LAN connection stable and avoid tab/app switching.",
          "Review unanswered or marked questions before final submit.",
        ];
    const durationText = examMeta?.duration_minutes
      ? `${Number(examMeta.duration_minutes)} min`
      : "Duration visible after exam selection";
    el.preExamRulesBox.innerHTML = `
      <p><strong>${esc(examMeta?.exam_name || "Selected exam")}</strong></p>
      <p>Duration: ${esc(durationText)}</p>
      <ol>${rules.map((rule) => `<li>${esc(rule)}</li>`).join("")}</ol>
    `;
  }

  function renderAnalysisExplanation(explanation) {
    if (!explanation || typeof explanation !== "object") {
      return '<div class="small">AI explanation unavailable.</div>';
    }
    const providerStatus =
      explanation.provider_status && typeof explanation.provider_status === "object"
        ? explanation.provider_status
        : {};
    return `
      <div class="analysis-response">
        <div class="summary-row"><span>Why it was wrong</span><strong>${esc(explanation.why_wrong || "-")}</strong></div>
        <div class="summary-row"><span>Core concept</span><strong>${esc(explanation.core_concept || "-")}</strong></div>
        <div class="summary-row"><span>Study tip</span><strong>${esc(explanation.study_tip || "-")}</strong></div>
        <div class="summary-row"><span>Weak topic</span><strong>${esc(explanation.weak_topic || "-")}</strong></div>
        <div class="summary-row"><span>AI Source</span><strong>${esc(formatAiProviderLabel(explanation.provider || providerStatus.resolved_provider || "heuristic"))}</strong></div>
        <div class="small">${esc(formatAiReason(providerStatus.reason))}</div>
      </div>
    `;
  }

  function formatAiProviderLabel(provider) {
    const normalized = String(provider || "heuristic").trim().toLowerCase();
    if (normalized === "openai") {
      return "OpenAI";
    }
    if (normalized === "gemini") {
      return "Gemini";
    }
    return "Heuristic";
  }

  function formatAiReason(reason) {
    const normalized = String(reason || "").trim();
    if (!normalized) {
      return "AI provider status will appear here.";
    }
    const labelMap = {
      no_api_key_configured: "No OpenAI or Gemini API key configured on the server.",
      openai_api_key_missing: "OpenAI provider selected, but the API key is missing.",
      gemini_api_key_missing: "Gemini provider selected, but the API key is missing.",
      openai_request_failed_or_invalid_json: "OpenAI request failed or returned a non-JSON reply, so heuristic fallback was used.",
      gemini_request_failed_or_invalid_json: "Gemini request failed or returned a non-JSON reply, so heuristic fallback was used.",
      live_openai_http_ready: "OpenAI live mode is active through the HTTP integration.",
      live_openai_sdk_ready: "OpenAI live mode is active through the SDK integration.",
      live_gemini_http_ready: "Gemini live mode is active through the HTTP integration.",
      live_gemini_sdk_ready: "Gemini live mode is active through the SDK integration.",
    };
    return labelMap[normalized] || normalized.replace(/_/g, " ");
  }

  function renderAiAnalysis(payload) {
    st.latestAnalysis = payload || null;
    const rows = Array.isArray(payload?.incorrect_or_skipped_questions)
      ? payload.incorrect_or_skipped_questions
      : [];
    const weakTopics = Array.isArray(payload?.weak_topics) ? payload.weak_topics : [];
    const learningPath = Array.isArray(payload?.learning_path) ? payload.learning_path : [];
    const topTopic = weakTopics.length ? weakTopics[0].topic : "No weak topic";
    const providerStatus =
      payload?.provider_status && typeof payload.provider_status === "object"
        ? payload.provider_status
        : {};
    const requestedProvider = formatAiProviderLabel(
      providerStatus.requested_provider || payload?.provider || "heuristic"
    );
    const resolvedProvider = formatAiProviderLabel(
      providerStatus.resolved_provider || payload?.provider || "heuristic"
    );
    const modeLabel = String(providerStatus.mode || "fallback");
    const providerReason = formatAiReason(providerStatus.reason);

    if (el.analysisOverviewBox) {
      el.analysisOverviewBox.innerHTML = `
        <div class="result-grid compact">
          <div class="result-kpi small">
            <p>Weak Questions</p>
            <h5>${esc(String(rows.length))}</h5>
          </div>
          <div class="result-kpi small">
            <p>Top Weak Topic</p>
            <h5>${esc(String(topTopic))}</h5>
          </div>
          <div class="result-kpi small">
            <p>AI Requested</p>
            <h5>${esc(requestedProvider)}</h5>
          </div>
          <div class="result-kpi small">
            <p>AI Active</p>
            <h5>${esc(resolvedProvider)}</h5>
          </div>
          <div class="result-kpi small">
            <p>Mode</p>
            <h5>${esc(modeLabel)}</h5>
          </div>
        </div>
        <p class="result-note">${esc(providerReason)}</p>
        <p class="result-note">${esc(payload?.summary || "Analysis summary will appear here.")}</p>
      `;
    }

    if (el.analysisLearningPathBox) {
      el.analysisLearningPathBox.innerHTML = `
        <div><strong>Weak Topics</strong></div>
        <div class="analysis-chip-grid">
          ${weakTopics.length
            ? weakTopics
                .map(
                  (topic) => `
                    <div class="analysis-chip">
                      <strong>${esc(String(topic.topic || "untagged"))}</strong>
                      <span>${esc(String(topic.count || 0))} weak response(s)</span>
                      <p>${esc(String(topic.recommended_focus || ""))}</p>
                    </div>
                  `
                )
                .join("")
            : '<div class="small">No weak topic cluster detected. Strong attempt.</div>'}
        </div>
        <div style="margin-top:12px"><strong>Personalized Learning Path</strong></div>
        <ol class="guide-list">${learningPath.length ? learningPath.map((item) => `<li>${esc(item)}</li>`).join("") : "<li>No additional learning path needed.</li>"}</ol>
      `;
    }

    if (el.analysisListBox) {
      if (!rows.length) {
        el.analysisListBox.innerHTML = `
          <div class="analysis-empty">
            <strong>All clear</strong>
            <p>No incorrect or skipped questions found for this attempt.</p>
          </div>
        `;
        return;
      }

      el.analysisListBox.innerHTML = rows
        .map((row) => {
          const questionId = String(row.question_id || "");
          const explanation = st.analysisExplanationByQuestion[questionId];
          return `
            <article class="analysis-question-card" data-question-id="${esc(questionId)}">
              <div class="row">
                <div>
                  <p class="section-label">Q${esc(String(row.sequence_number || "-"))} • ${esc(String(row.status || "incorrect").toUpperCase())}</p>
                  <h4>${esc(String(row.topic || "untagged"))}</h4>
                </div>
                <button class="btn-outline analysis-explain-btn" type="button" data-question-id="${esc(questionId)}">
                  Explain with AI
                </button>
              </div>
              <p>${esc(String(row.question_text || "Question unavailable."))}</p>
              <div class="summary-row"><span>Your Answer</span><strong>${esc(String(row.selected_option_text || "Skipped"))}</strong></div>
              <div class="summary-row"><span>Correct Answer</span><strong>${esc(String(row.correct_option_text || "Unavailable"))}</strong></div>
              <div class="analysis-output" data-analysis-output="${esc(questionId)}">
                ${explanation ? renderAnalysisExplanation(explanation.analysis || explanation) : '<div class="small">Click "Explain with AI" to generate contextual feedback.</div>'}
              </div>
            </article>
          `;
        })
        .join("");
    }
  }

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
    let hardSequences = new Set();
    let easySequences = new Set();
    let answeredQuestionIds = new Set();
    let sequenceQuestionMap = new Map();
    let pendingQueue = [];
    let eliminatedOptionsByQuestion = {};
    let struckOptionsByQuestion = {};

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
        hardSequences = new Set();
        easySequences = new Set();
        answeredQuestionIds = new Set();
        sequenceQuestionMap = new Map();
        pendingQueue = [];
        eliminatedOptionsByQuestion = {};
        struckOptionsByQuestion = {};
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
        if (Array.isArray(cache.hard_sequences)) {
          hardSequences = new Set(
            cache.hard_sequences
              .map((value) => Number(value))
              .filter((value) => Number.isInteger(value) && value > 0)
          );
        }
        if (Array.isArray(cache.easy_sequences)) {
          easySequences = new Set(
            cache.easy_sequences
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
        if (cache.eliminated_options_by_question && typeof cache.eliminated_options_by_question === "object") {
          eliminatedOptionsByQuestion = { ...cache.eliminated_options_by_question };
        }
        if (cache.struck_options_by_question && typeof cache.struck_options_by_question === "object") {
          struckOptionsByQuestion = { ...cache.struck_options_by_question };
        }
      },
      serialize() {
        return {
          draft_answers: { ...draftAnswers },
          confidence_by_question: { ...confidenceByQuestion },
          marked_sequences: [...markedSequences],
          hard_sequences: [...hardSequences],
          easy_sequences: [...easySequences],
          answered_question_ids: [...answeredQuestionIds],
          sequence_question_map: [...sequenceQuestionMap.entries()],
          pending_queue: [...pendingQueue],
          eliminated_options_by_question: { ...eliminatedOptionsByQuestion },
          struck_options_by_question: { ...struckOptionsByQuestion },
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
      toggleHard(sequenceNumber) {
        const sequence = Number(sequenceNumber);
        if (!sequence) {
          return false;
        }
        if (hardSequences.has(sequence)) {
          hardSequences.delete(sequence);
        } else {
          hardSequences.add(sequence);
          easySequences.delete(sequence);
        }
        persist();
        return hardSequences.has(sequence);
      },
      toggleEasy(sequenceNumber) {
        const sequence = Number(sequenceNumber);
        if (!sequence) {
          return false;
        }
        if (easySequences.has(sequence)) {
          easySequences.delete(sequence);
        } else {
          easySequences.add(sequence);
          hardSequences.delete(sequence);
        }
        persist();
        return easySequences.has(sequence);
      },
      isHard(sequenceNumber) {
        return hardSequences.has(Number(sequenceNumber));
      },
      isEasy(sequenceNumber) {
        return easySequences.has(Number(sequenceNumber));
      },
      getHardCount() {
        return hardSequences.size;
      },
      getEasyCount() {
        return easySequences.size;
      },
      toggleEliminate(questionId, optionId) {
        const q = String(questionId || "");
        const o = String(optionId || "");
        if (!q || !o) {
          return false;
        }
        const current = new Set(Array.isArray(eliminatedOptionsByQuestion[q]) ? eliminatedOptionsByQuestion[q] : []);
        if (current.has(o)) {
          current.delete(o);
        } else {
          current.add(o);
        }
        eliminatedOptionsByQuestion[q] = [...current];
        persist();
        return current.has(o);
      },
      toggleStrike(questionId, optionId) {
        const q = String(questionId || "");
        const o = String(optionId || "");
        if (!q || !o) {
          return false;
        }
        const current = new Set(Array.isArray(struckOptionsByQuestion[q]) ? struckOptionsByQuestion[q] : []);
        if (current.has(o)) {
          current.delete(o);
        } else {
          current.add(o);
        }
        struckOptionsByQuestion[q] = [...current];
        persist();
        return current.has(o);
      },
      isEliminated(questionId, optionId) {
        const q = String(questionId || "");
        const o = String(optionId || "");
        if (!q || !o) {
          return false;
        }
        const current = new Set(Array.isArray(eliminatedOptionsByQuestion[q]) ? eliminatedOptionsByQuestion[q] : []);
        return current.has(o);
      },
      isStruck(questionId, optionId) {
        const q = String(questionId || "");
        const o = String(optionId || "");
        if (!q || !o) {
          return false;
        }
        const current = new Set(Array.isArray(struckOptionsByQuestion[q]) ? struckOptionsByQuestion[q] : []);
        return current.has(o);
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
    updateStressDetector();
  });

  const answerState = createAnswerState(() => {
    persistAttemptCache();
    updateProgress();
    renderPalette();
    updateBucketSummary();
    updateSyncHealthIndicator();
    updateSyncDiagnostics();
    updateStressDetector();
  });

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const setStatus = (message) => {
    el.status.textContent = message;
  };

  const GLOSSARY = [
    ["Negative Marking", "Wrong answer par score deduction rule."],
    ["Review", "Question marked for later revisit."],
    ["Snapshot", "Exam questions ka locked copy for your attempt."],
    ["Autosave", "Answer local + server sync safeguard."],
    ["Pending Sync", "Answer locally saved hai, server sync pending hai."],
    ["Finalization", "Exam submission lock ho chuka hai."],
  ];

  const INLINE_TRANSLATIONS = [
    ["question", "prashn"],
    ["option", "vikalp"],
    ["submit", "jama karein"],
    ["review", "punaravalokan"],
    ["time", "samay"],
    ["answer", "uttar"],
    ["warning", "chetavani"],
  ];

  const EXAM_DAY_TIPS = [
    "Pehle easy-win questions complete karo, phir doubtful pe jao.",
    "Agar stuck ho to 45-60 sec rule follow karo: mark and move.",
    "Low-time phase me sirf high-confidence attempts prioritize karo.",
    "Har 8-10 question ke baad posture reset aur deep breath lo.",
  ];

  async function updateIntegrityHash() {
    if (!el.integrityHash) {
      return;
    }
    if (!st.attemptId || !window.crypto?.subtle) {
      el.integrityHash.textContent = "Integrity checksum: -";
      return;
    }
    const payload = `${st.studentId}|${st.examId}|${st.attemptId}|${timerState.getExpiresAt() || "-"}`;
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(payload)
    );
    const hex = Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 20);
    el.integrityHash.textContent = `Integrity checksum: ${hex}`;
  }

  function playAlertTone(freqHz = 740, durationMs = 170) {
    if (!uiPrefs.soundAlerts || uiPrefs.soundVolume <= 0) {
      return;
    }
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
      return;
    }
    const ctx = new AudioCtx();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.frequency.value = freqHz;
    gain.gain.value = Math.max(0.01, Math.min(1, uiPrefs.soundVolume / 100));
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start();
    window.setTimeout(() => {
      oscillator.stop();
      ctx.close();
    }, durationMs);
  }

  function updateInputLatencyMeter() {
    if (!el.inputLatencyMeter) {
      return;
    }
    const rows = st.inputLatencySamples.slice(-15);
    if (!rows.length) {
      el.inputLatencyMeter.textContent = "Input latency: waiting...";
      return;
    }
    const avg = rows.reduce((acc, item) => acc + item, 0) / rows.length;
    const rounded = Math.round(avg);
    const status = rounded > 220 ? "high" : rounded > 120 ? "moderate" : "good";
    el.inputLatencyMeter.textContent = `Input latency: ${rounded}ms (${status})`;
  }

  function recordInputLatencySample(startMs) {
    if (!Number.isFinite(startMs)) {
      return;
    }
    const now = typeof performance !== "undefined" ? performance.now() : Date.now();
    const latency = Math.max(0, Math.round(now - startMs));
    st.inputLatencySamples.push(latency);
    if (st.inputLatencySamples.length > 80) {
      st.inputLatencySamples = st.inputLatencySamples.slice(-80);
    }
    updateInputLatencyMeter();
    persistAttemptCache();
  }

  function updateStressDetector() {
    if (!el.stressDetector) {
      return;
    }
    const remaining = timerState.getRemainingSeconds();
    const lowTimePressure = remaining > 0 && remaining <= 300 ? 2 : 0;
    const syncPressure = Math.min(4, answerState.getPendingCount());
    const warningPressure = Math.min(4, st.warningCount);
    const retryPressure = Math.min(4, st.syncRetryCount);
    const clipboardPressure = Math.min(3, st.clipboardLogs.length > 0 ? 1 : 0);
    const pressureScore = lowTimePressure + syncPressure + warningPressure + retryPressure + clipboardPressure;
    const level = pressureScore >= 8 ? "high" : pressureScore >= 4 ? "moderate" : "normal";
    st.stressLevel = level;
    const suggestion =
      level === "high"
        ? "Take 20s breathing reset and focus easy wins."
        : level === "moderate"
          ? "Slow down slightly and validate option text once."
          : "Steady pace.";
    el.stressDetector.textContent = `Stress detector: ${level} (${pressureScore}) | ${suggestion}`;
  }

  function updateCaptionPreview() {
    if (!el.captionPreview) {
      return;
    }
    const size = Number(el.captionSize?.value || st.captionSize || 16);
    st.captionSize = Math.max(12, Math.min(28, size));
    el.captionPreview.style.fontSize = `${st.captionSize}px`;
    const questionText = st.currentQuestion?.text || "Caption preview text";
    el.captionPreview.textContent = `Caption (${st.captionSize}px): ${questionText}`;
  }

  function renderEquationPreview() {
    if (!el.equationPreview) {
      return;
    }
    const raw = String(el.equationEditor?.value || "").trim();
    if (!raw) {
      el.equationPreview.textContent = "Equation preview will appear here.";
      return;
    }
    const pretty = raw
      .replaceAll("\\frac", "frac")
      .replaceAll("sqrt", "√")
      .replaceAll(">=", "≥")
      .replaceAll("<=", "≤")
      .replaceAll("!=", "≠")
      .replaceAll("->", "→")
      .replace(/\^2/g, "²")
      .replace(/\^3/g, "³")
      .replace(/\*+/g, "×");
    el.equationPreview.textContent = `Equation preview: ${pretty}`;
  }

  function persistCodeDraft() {
    if (!st.currentQuestion || !el.codeEditor) {
      return;
    }
    st.codeDraftByQuestion[String(st.currentQuestion.id)] = {
      language: String(el.codeLanguage?.value || "python"),
      source: String(el.codeEditor.value || ""),
      updated_at: new Date().toISOString(),
    };
    persistAttemptCache();
  }

  function loadCodeDraftForCurrentQuestion() {
    if (!st.currentQuestion || !el.codeEditor || !el.codeLanguage) {
      return;
    }
    const draft = st.codeDraftByQuestion[String(st.currentQuestion.id)];
    if (!draft) {
      el.codeEditor.value = "";
      el.codeLanguage.value = "python";
      return;
    }
    el.codeLanguage.value = draft.language || "python";
    el.codeEditor.value = draft.source || "";
  }

  function openCalmMode() {
    if (!el.calmModeOverlay) {
      return;
    }
    el.calmModeOverlay.hidden = false;
    syncModalOpenState();
    startBreathingPrompt();
    setStatus("Calm mode active. Slow inhale-exhale rhythm follow karo.");
  }

  function closeCalmMode() {
    if (!el.calmModeOverlay) {
      return;
    }
    el.calmModeOverlay.hidden = true;
    syncModalOpenState();
    setStatus("Calm mode closed.");
  }

  function runPracticeSimulation() {
    if (!el.practiceSimBox) {
      return;
    }
    const total = Number(st.totalQuestions || 0);
    const answered = answerState.getAnsweredCount(total);
    const review = answerState.getMarkedCount();
    const pending = answerState.getPendingCount();
    const easy = answerState.getEasyCount();
    const hard = answerState.getHardCount();
    const remaining = timerState.getRemainingSeconds();
    const targetRate = total > 0 ? Math.min(100, Math.round((answered / total) * 100)) : 0;
    const recommendation =
      remaining <= 300
        ? "Last-mile mode: marked + easy bucket first."
        : hard > easy
          ? "Hard bucket heavy. Do one quick easy pass."
          : "Maintain current pace with short validation pause every 3 questions.";
    el.practiceSimBox.textContent = JSON.stringify(
      {
        simulation_at: new Date().toISOString(),
        answered,
        review,
        pending_sync: pending,
        hard_bucket: hard,
        easy_bucket: easy,
        projected_completion_percent: targetRate,
        recommendation,
      },
      null,
      2
    );
  }

  function runMockAnalyticsMirror() {
    if (!el.mockAnalyticsBox) {
      return;
    }
    const total = Number(st.totalQuestions || 0);
    const answered = answerState.getAnsweredCount(total);
    const unanswered = Math.max(0, total - answered);
    const confidenceTagged = answerState.getConfidenceTaggedCount(total);
    const avgTime = total
      ? Number(
          (
            Object.values(st.questionTimeBySequence).reduce(
              (acc, value) => acc + Number(value || 0),
              0
            ) / Math.max(1, answered || 1)
          ).toFixed(2)
        )
      : 0;
    el.mockAnalyticsBox.textContent = JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        answered,
        unanswered,
        confidence_tagged: confidenceTagged,
        avg_seconds_per_answered_question: avgTime,
        warning_count: st.warningCount,
        sync_retry_count: st.syncRetryCount,
        stress_level: st.stressLevel,
      },
      null,
      2
    );
  }

  function toggleDragDropAnswerMode() {
    st.dragDropMode = !st.dragDropMode;
    if (el.enableDragDropOptions) {
      el.enableDragDropOptions.textContent = st.dragDropMode
        ? "Drag-Drop Answer Mode: On"
        : "Drag-Drop Answer Mode";
    }
    if (st.currentQuestion && st.currentQuestionOptions.length) {
      renderQuestion({
        question: st.currentQuestion,
        options: st.currentQuestionOptions,
        sequence_number: st.sequence,
      });
    }
    persistAttemptCache();
  }

  function attachDragDropHandlers(optionLabel, optionId) {
    if (!st.dragDropMode || !(optionLabel instanceof HTMLElement)) {
      return;
    }
    optionLabel.draggable = true;
    optionLabel.dataset.optionId = optionId;
    optionLabel.addEventListener("dragstart", (event) => {
      if (!(event.dataTransfer instanceof DataTransfer)) {
        return;
      }
      event.dataTransfer.setData("text/plain", optionId);
      event.dataTransfer.effectAllowed = "move";
    });
    optionLabel.addEventListener("dragover", (event) => {
      event.preventDefault();
      optionLabel.classList.add("drag-hover");
    });
    optionLabel.addEventListener("dragleave", () => {
      optionLabel.classList.remove("drag-hover");
    });
    optionLabel.addEventListener("drop", (event) => {
      event.preventDefault();
      optionLabel.classList.remove("drag-hover");
      const sourceId = event.dataTransfer?.getData("text/plain");
      if (!sourceId || sourceId === optionId) {
        return;
      }
      const current = [...st.currentQuestionOptions];
      const fromIndex = current.findIndex((row) => String(row.id) === String(sourceId));
      const toIndex = current.findIndex((row) => String(row.id) === String(optionId));
      if (fromIndex < 0 || toIndex < 0) {
        return;
      }
      const [moved] = current.splice(fromIndex, 1);
      current.splice(toIndex, 0, moved);
      st.currentQuestionOptions = current;
      appendAnswerTimeline("drag_reorder", st.sequence);
      renderQuestion({
        question: st.currentQuestion,
        options: st.currentQuestionOptions,
        sequence_number: st.sequence,
      });
      setStatus("Option order updated in drag-drop mode.");
    });
  }

  function generateMatchMode() {
    if (!el.matchModeBox || !st.currentQuestionOptions.length) {
      return;
    }
    const left = st.currentQuestionOptions.map((row, idx) => ({
      label: `Item ${idx + 1}`,
      value: row.option_text,
    }));
    const right = [...left]
      .sort(() => Math.random() - 0.5)
      .map((row, idx) => ({ slot: String.fromCharCode(65 + idx), value: row.value }));
    const html = left
      .map((row, index) => {
        const matched = right[index];
        return `<div>${esc(row.label)} -> ${esc(matched.slot)}</div>`;
      })
      .join("");
    el.matchModeBox.innerHTML = `
      <div><strong>Match Mode Preview</strong></div>
      <div style="margin-top:6px">${html}</div>
      <div style="margin-top:6px">Right column options shuffled for practice reasoning.</div>
    `;
    appendAnswerTimeline("match_mode_generated", st.sequence);
  }

  function playQuestionAudio() {
    if (!("speechSynthesis" in window)) {
      setStatus("Audio player unsupported in this browser.");
      return;
    }
    if (!st.currentQuestion) {
      setStatus("Load a question first.");
      return;
    }
    window.speechSynthesis.cancel();
    const parts = [st.currentQuestion.text || ""];
    st.currentQuestionOptions.forEach((option, index) => {
      parts.push(`Option ${String.fromCharCode(65 + index)}. ${option.option_text}`);
    });
    const utterance = new SpeechSynthesisUtterance(parts.join(". "));
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.lang = "en-IN";
    window.speechSynthesis.speak(utterance);
    setStatus("Question audio playback started.");
  }

  function renderReceiptQr(receipt) {
    if (!el.receiptQrBox) {
      return;
    }
    if (!receipt?.receipt_id) {
      el.receiptQrBox.textContent = "Signed QR receipt will appear here after submission.";
      return;
    }
    const seed = `${receipt.receipt_id}|${receipt.student_id}|${receipt.attempt_id}`;
    let cursor = 0;
    const bits = [];
    for (let index = 0; index < 256; index += 1) {
      const code = seed.charCodeAt(cursor % seed.length);
      bits.push((code + index * 17) % 2);
      cursor += 1;
    }
    const cell = 8;
    const size = 16;
    const cells = [];
    for (let y = 0; y < size; y += 1) {
      for (let x = 0; x < size; x += 1) {
        const value = bits[y * size + x];
        if (!value) {
          continue;
        }
        cells.push(
          `<rect x="${x * cell}" y="${y * cell}" width="${cell}" height="${cell}" fill="#111827"></rect>`
        );
      }
    }
    el.receiptQrBox.innerHTML = `
      <div><strong>Signed QR Receipt (visual hash)</strong></div>
      <svg viewBox="0 0 ${size * cell} ${size * cell}" width="180" height="180" role="img" aria-label="Receipt QR visual hash" style="margin-top:8px;border:1px solid #d2dbe8;background:#fff">
        ${cells.join("")}
      </svg>
      <div class="small" style="margin-top:6px">Receipt ${esc(receipt.receipt_id)} | hash-grid signature ready for print/export.</div>
    `;
  }

  function renderTopicStrengthAndWeakPlan(questionResults) {
    const rows = Array.isArray(questionResults) ? questionResults : [];
    if (!el.topicStrengthBox || !el.weakTopicPlanBox) {
      return;
    }
    if (!rows.length) {
      el.topicStrengthBox.textContent = "Topic strength map unavailable for this attempt.";
      el.weakTopicPlanBox.textContent = "Weak-topic action plan unavailable for this attempt.";
      return;
    }
    const topicMap = new Map();
    rows.forEach((row) => {
      const topic = st.questionTopicById[String(row.question_id)] || "untagged";
      if (!topicMap.has(topic)) {
        topicMap.set(topic, { topic, total: 0, correct: 0, attempted: 0 });
      }
      const entry = topicMap.get(topic);
      entry.total += 1;
      if (row.selected_option_id) {
        entry.attempted += 1;
      }
      if (row.is_correct) {
        entry.correct += 1;
      }
    });
    const sorted = Array.from(topicMap.values()).map((row) => ({
      ...row,
      accuracy: row.total > 0 ? Number(((row.correct / row.total) * 100).toFixed(1)) : 0,
      attempt_rate: row.total > 0 ? Number(((row.attempted / row.total) * 100).toFixed(1)) : 0,
    }));
    sorted.sort((a, b) => b.accuracy - a.accuracy);

    el.topicStrengthBox.innerHTML = `
      <div><strong>Topic Strength Map</strong></div>
      <div style="margin-top:8px">
        ${sorted
          .map(
            (row) => `
              <div class="summary-row">
                <span>${esc(row.topic)}</span>
                <strong>${esc(String(row.accuracy))}% acc | ${esc(String(row.attempt_rate))}% attempted</strong>
              </div>
            `
          )
          .join("")}
      </div>
    `;

    const weak = [...sorted].sort((a, b) => a.accuracy - b.accuracy).slice(0, 3);
    const weakPlan = weak.length
      ? weak.map((row, idx) => `${idx + 1}. ${row.topic}: 25 MCQ drill + formula recap + 1 timed set.`)
      : ["No weak topic identified from this attempt."];
    el.weakTopicPlanBox.innerHTML = `
      <div><strong>Weak-Topic Action Plan</strong></div>
      <ul class="guide-list">${weakPlan.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
    `;
  }

  function clearDiagramCanvas() {
    if (!(el.diagramCanvas instanceof HTMLCanvasElement)) {
      return;
    }
    const ctx = el.diagramCanvas.getContext("2d");
    if (!ctx) {
      return;
    }
    ctx.clearRect(0, 0, el.diagramCanvas.width, el.diagramCanvas.height);
  }

  function initializeDiagramCanvas() {
    if (!(el.diagramCanvas instanceof HTMLCanvasElement)) {
      return;
    }
    const canvas = el.diagramCanvas;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#1f6feb";
    ctx.lineWidth = 2;

    const pointFor = (event) => {
      const rect = canvas.getBoundingClientRect();
      const source =
        event instanceof TouchEvent ? event.touches[0] || event.changedTouches[0] : event;
      const x = source.clientX - rect.left;
      const y = source.clientY - rect.top;
      return { x, y };
    };

    const begin = (event) => {
      if (!st.attemptId || st.finalized || st.paused) {
        return;
      }
      const { x, y } = pointFor(event);
      st.diagramStrokeActive = true;
      ctx.beginPath();
      ctx.moveTo(x, y);
      event.preventDefault();
    };

    const draw = (event) => {
      if (!st.diagramStrokeActive) {
        return;
      }
      const { x, y } = pointFor(event);
      ctx.lineTo(x, y);
      ctx.stroke();
      event.preventDefault();
    };

    const end = () => {
      if (!st.diagramStrokeActive) {
        return;
      }
      st.diagramStrokeActive = false;
      appendAnswerTimeline("diagram_updated", st.sequence);
    };

    canvas.addEventListener("mousedown", begin);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", end);
    canvas.addEventListener("mouseleave", end);
    canvas.addEventListener("touchstart", begin, { passive: false });
    canvas.addEventListener("touchmove", draw, { passive: false });
    canvas.addEventListener("touchend", end, { passive: false });
  }

  function renderClipboardLogs() {
    if (!el.clipboardLog) {
      return;
    }
    if (!st.clipboardLogs.length) {
      el.clipboardLog.textContent = "No clipboard attempts yet.";
      return;
    }
    el.clipboardLog.innerHTML = st.clipboardLogs
      .slice(-8)
      .map((entry) => `<div>${esc(formatDate(entry.at))} - ${esc(entry.kind)}</div>`)
      .join("");
  }

  function updateBucketSummary() {
    if (!el.bucketSummary) {
      return;
    }
    el.bucketSummary.textContent = `Hard ${answerState.getHardCount()} | Easy ${answerState.getEasyCount()}`;
  }

  function updateOptionModeButtons() {
    if (el.toggleEliminateMode) {
      el.toggleEliminateMode.textContent = `Eliminate Mode: ${st.optionMode === "eliminate" ? "On" : "Off"}`;
    }
    if (el.toggleStrikeMode) {
      el.toggleStrikeMode.textContent = `Strike Mode: ${st.optionMode === "strike" ? "On" : "Off"}`;
    }
    if (el.enableDragDropOptions) {
      el.enableDragDropOptions.textContent = st.dragDropMode
        ? "Drag-Drop Answer Mode: On"
        : "Drag-Drop Answer Mode";
    }
  }

  function runInlineTranslation(text) {
    if (!st.translateMode) {
      return text;
    }
    let translated = String(text || "");
    for (const [source, target] of INLINE_TRANSLATIONS) {
      const pattern = new RegExp(`\\b${source}\\b`, "gi");
      translated = translated.replace(pattern, target);
    }
    return translated;
  }

  function openGlossaryModal() {
    if (!el.glossaryModal || !el.glossaryContent) {
      return;
    }
    el.glossaryContent.innerHTML = GLOSSARY.map(
      ([term, meaning]) => `<p><strong>${esc(term)}:</strong> ${esc(meaning)}</p>`
    ).join("");
    el.glossaryModal.hidden = false;
    syncModalOpenState();
  }

  function closeGlossaryModal() {
    if (!el.glossaryModal) {
      return;
    }
    el.glossaryModal.hidden = true;
    syncModalOpenState();
  }

  function renderExamTips() {
    if (!el.tipsFeed) {
      return;
    }
    el.tipsFeed.textContent = EXAM_DAY_TIPS[st.examTipsIndex % EXAM_DAY_TIPS.length];
  }

  function startExamTipsFeed() {
    renderExamTips();
    if (st.tipsTimerId) {
      clearInterval(st.tipsTimerId);
    }
    st.tipsTimerId = window.setInterval(() => {
      st.examTipsIndex = (st.examTipsIndex + 1) % EXAM_DAY_TIPS.length;
      renderExamTips();
    }, 15000);
  }

  function stopExamTipsFeed() {
    if (st.tipsTimerId) {
      clearInterval(st.tipsTimerId);
      st.tipsTimerId = null;
    }
  }

  function showConflictResolver(conflict) {
    if (!el.conflictModal || !el.conflictKeepLocal || !el.conflictReloadServer) {
      return Promise.resolve("keep_local");
    }
    st.conflictPending = conflict;
    el.conflictModal.hidden = false;
    syncModalOpenState();
    return new Promise((resolve) => {
      st.conflictResolver = resolve;
    });
  }

  function closeConflictResolver(choice) {
    if (!el.conflictModal) {
      return;
    }
    el.conflictModal.hidden = true;
    syncModalOpenState();
    const resolver = st.conflictResolver;
    st.conflictResolver = null;
    if (typeof resolver === "function") {
      resolver(choice || "keep_local");
    }
  }

  function openResumeWizard(cached) {
    if (!el.resumeWizardModal || !el.resumeWizardSummary) {
      return Promise.resolve("resume");
    }
    el.resumeWizardSummary.innerHTML = `
      <div class="summary-row"><span>Attempt</span><strong>${esc(String(cached.attempt_id || "-"))}</strong></div>
      <div class="summary-row"><span>Exam</span><strong>${esc(String(cached.exam_name || cached.exam_id || "-"))}</strong></div>
      <div class="summary-row"><span>Last Updated</span><strong>${esc(formatDate(cached.updated_at))}</strong></div>
    `;
    el.resumeWizardModal.hidden = false;
    syncModalOpenState();
    return new Promise((resolve) => {
      st.resumeWizardResolver = resolve;
    });
  }

  function closeResumeWizard(choice) {
    if (!el.resumeWizardModal) {
      return;
    }
    el.resumeWizardModal.hidden = true;
    syncModalOpenState();
    const resolver = st.resumeWizardResolver;
    st.resumeWizardResolver = null;
    if (typeof resolver === "function") {
      resolver(choice || "resume");
    }
  }

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
    updateStressDetector();
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
        uiPrefs.colorblind = Boolean(parsed.colorblind);
        uiPrefs.reducedMotion = Boolean(parsed.reduced_motion);
        uiPrefs.largeCursor = Boolean(parsed.large_cursor);
        const nextZoom = Number(parsed.question_zoom);
        if (!Number.isNaN(nextZoom)) {
          uiPrefs.questionZoom = Math.min(160, Math.max(80, Math.round(nextZoom)));
        }
        if (typeof parsed.confirm_unanswered === "boolean") {
          uiPrefs.confirmUnanswered = parsed.confirm_unanswered;
        }
        if (typeof parsed.sound_alerts === "boolean") {
          uiPrefs.soundAlerts = parsed.sound_alerts;
        }
        const nextVolume = Number(parsed.sound_volume);
        if (!Number.isNaN(nextVolume)) {
          uiPrefs.soundVolume = Math.min(100, Math.max(0, Math.round(nextVolume)));
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
        colorblind: uiPrefs.colorblind,
        reduced_motion: uiPrefs.reducedMotion,
        large_cursor: uiPrefs.largeCursor,
        question_zoom: uiPrefs.questionZoom,
        confirm_unanswered: uiPrefs.confirmUnanswered,
        sound_alerts: uiPrefs.soundAlerts,
        sound_volume: uiPrefs.soundVolume,
      })
    );
  }

  function applyUiPrefs() {
    document.body.dataset.fontScale = uiPrefs.fontScale;
    document.body.classList.toggle("student-high-contrast", uiPrefs.highContrast);
    document.body.classList.toggle("student-colorblind", uiPrefs.colorblind);
    document.body.classList.toggle("student-reduced-motion", uiPrefs.reducedMotion);
    document.body.classList.toggle("student-large-cursor", uiPrefs.largeCursor);
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
    if (el.colorblindToggle) {
      el.colorblindToggle.checked = uiPrefs.colorblind;
    }
    if (el.reducedMotionToggle) {
      el.reducedMotionToggle.checked = uiPrefs.reducedMotion;
    }
    if (el.largeCursorToggle) {
      el.largeCursorToggle.checked = uiPrefs.largeCursor;
    }
    if (el.soundAlertToggle) {
      el.soundAlertToggle.checked = uiPrefs.soundAlerts;
    }
    if (el.soundVolume) {
      el.soundVolume.value = String(uiPrefs.soundVolume);
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
      (el.shortcutsModal ? !el.shortcutsModal.hidden : false) ||
      (el.resumeWizardModal ? !el.resumeWizardModal.hidden : false) ||
      (el.glossaryModal ? !el.glossaryModal.hidden : false) ||
      (el.conflictModal ? !el.conflictModal.hidden : false) ||
      (el.calmModeOverlay ? !el.calmModeOverlay.hidden : false);
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
      st.heartbeatHistory.push({ at: new Date().toISOString(), latency_ms: latencyMs });
      if (st.heartbeatHistory.length > 40) {
        st.heartbeatHistory = st.heartbeatHistory.slice(-40);
      }
      if (latencyMs > 1500) {
        updateHeartbeatIndicator("degraded", `Server: Slow (${latencyMs}ms)`);
      } else {
        updateHeartbeatIndicator("online", `Server: OK (${latencyMs}ms)`);
      }
      updateNetworkQuality();
    } catch {
      st.heartbeatHistory.push({ at: new Date().toISOString(), latency_ms: null });
      if (st.heartbeatHistory.length > 40) {
        st.heartbeatHistory = st.heartbeatHistory.slice(-40);
      }
      updateHeartbeatIndicator("offline", "Server: Unreachable");
      updateNetworkQuality();
    }
  }

  function updateNetworkQuality() {
    if (!el.networkQuality) {
      return;
    }
    const recent = st.heartbeatHistory.slice(-12);
    if (!recent.length) {
      el.networkQuality.textContent = "Network quality: waiting...";
      return;
    }
    const ok = recent.filter((row) => typeof row.latency_ms === "number");
    const avg = ok.length
      ? Math.round(ok.reduce((acc, row) => acc + Number(row.latency_ms || 0), 0) / ok.length)
      : 0;
    const offlineCount = recent.length - ok.length;
    const spark = recent
      .map((row) => {
        if (typeof row.latency_ms !== "number") {
          return "x";
        }
        if (row.latency_ms < 300) {
          return "_";
        }
        if (row.latency_ms < 900) {
          return "-";
        }
        if (row.latency_ms < 1800) {
          return "~";
        }
        return "!";
      })
      .join("");
    const quality =
      offlineCount > 0 ? "Unstable" : avg > 1200 ? "Slow" : avg > 600 ? "Moderate" : "Good";
    el.networkQuality.textContent = `Network quality: ${quality} | avg=${avg}ms | offline=${offlineCount} | ${spark}`;
  }

  function updateSyncDiagnostics() {
    if (!el.syncDiagnostics) {
      return;
    }
    const pending = answerState.getPendingCount();
    const lastError = st.lastSyncError ? ` | last_error=${st.lastSyncError}` : "";
    el.syncDiagnostics.textContent = `Sync diagnostics: retries=${st.syncRetryCount} | pending=${pending} | predownloaded=${st.predownloadedCount}${lastError}`;
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
      renderPreExamRulesPreview();
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
      renderPreExamRulesPreview(data);
    } catch (error) {
      el.rulesContent.innerHTML = `<p>${esc(error.message || "Unable to load rules.")}</p>`;
      renderPreExamRulesPreview();
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
    if (!st.attemptId || st.finalized) {
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
        const newest = rows[rows.length - 1];
        const severity = String(newest?.severity || "info").toLowerCase();
        if (severity === "critical") {
          playAlertTone(360, 260);
        } else if (severity === "warn") {
          playAlertTone(520, 180);
        }
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
    renderReceiptQr(receipt);
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
    playAlertTone(680, 180);
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

  function resultHistoryKey() {
    return `${RESULT_HISTORY_PREFIX}${st.studentId || "unknown"}`;
  }

  function readResultHistory() {
    try {
      const raw = localStorage.getItem(resultHistoryKey());
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function writeResultHistory(rows) {
    localStorage.setItem(resultHistoryKey(), JSON.stringify(rows.slice(-20)));
  }

  function buildCoachingPlan(percentage, attemptedRatio, accuracyRatio) {
    const recommendations = [];
    if (percentage < 40) {
      recommendations.push("Concept reset: core topics revise with solved examples.");
    } else if (percentage < 70) {
      recommendations.push("Targeted practice: weak topics par 20-30 focused MCQs/day.");
    } else {
      recommendations.push("Maintain pace: timed mocks se stability preserve karo.");
    }
    if (attemptedRatio < 0.75) {
      recommendations.push("Attempt strategy improve karo: easy-first pass mandatory rakho.");
    }
    if (accuracyRatio < 0.6) {
      recommendations.push("Accuracy drills: elimination + re-read before locking answer.");
    }
    if (!recommendations.length) {
      recommendations.push("Balanced performance. Maintain revision cadence.");
    }
    return recommendations;
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
    const attemptedRatio = totalQuestions > 0 ? attempted / totalQuestions : 0;
    const accuracyRatio = attempted > 0 ? correct / attempted : 0;

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

    const history = readResultHistory();
    const last = history.length ? history[history.length - 1] : null;
    const delta =
      last && typeof last.percentage === "number"
        ? Number((percentage - Number(last.percentage || 0)).toFixed(2))
        : null;
    const filteredHistory = history.filter((row) => row.attempt_id !== st.attemptId);
    const nextHistory = [
      ...filteredHistory,
      {
        attempt_id: st.attemptId,
        exam_id: st.examId,
        exam_name: st.examName,
        percentage,
        score: totalScore,
        total_possible: totalPossible,
        created_at: new Date().toISOString(),
      },
    ];
    writeResultHistory(nextHistory);

    if (el.attemptCompareBox) {
      const compareRows = nextHistory.slice(-5).reverse();
      const trend = compareRows
        .map(
          (row) =>
            `<div>${esc(formatDate(row.created_at))} - ${esc(String(row.exam_name || row.exam_id))}: ${esc(Number(row.percentage || 0).toFixed(2))}%</div>`
        )
        .join("");
      el.attemptCompareBox.innerHTML = `
        <div><strong>Attempt Compare</strong></div>
        <div>${delta == null ? "First attempt baseline created." : `Delta vs previous: ${delta >= 0 ? "+" : ""}${delta}%`}</div>
        <div style="margin-top:6px">${trend || "No previous history."}</div>
      `;
    }

    if (el.resultExplainBox) {
      const coachingPlan = buildCoachingPlan(percentage, attemptedRatio, accuracyRatio);
      el.resultExplainBox.innerHTML = `
        <div><strong>Result Explanation</strong></div>
        <div class="summary-row"><span>Attempt Rate</span><strong>${(attemptedRatio * 100).toFixed(1)}%</strong></div>
        <div class="summary-row"><span>Accuracy</span><strong>${(accuracyRatio * 100).toFixed(1)}%</strong></div>
        <div class="summary-row"><span>Confidence Tags Used</span><strong>${answerState.getConfidenceTaggedCount(totalQuestions)}</strong></div>
        <div style="margin-top:8px"><strong>Adaptive Coaching Plan</strong></div>
        <ul class="guide-list">${coachingPlan.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      `;
    }

    renderTopicStrengthAndWeakPlan(questionResults);
  }

  async function explainQuestionWithAi(questionId, triggerButton = null) {
    if (!st.attemptId || !questionId) {
      return;
    }
    if (triggerButton instanceof HTMLButtonElement) {
      triggerButton.disabled = true;
      triggerButton.textContent = "Explaining...";
    }
    try {
      const payload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/analysis/explain`,
        {
          method: "POST",
          headers: studentHeaders(),
          body: { question_id: questionId },
        }
      );
      st.analysisExplanationByQuestion[String(questionId)] = payload;
      renderAiAnalysis(st.latestAnalysis);
      setResultTab("ai");
      setStatus(
        `AI explanation generated (${formatAiProviderLabel(
          payload.provider || payload.analysis?.provider || "heuristic"
        )}).`
      );
    } catch (error) {
      setStatus(error.message);
    } finally {
      if (triggerButton instanceof HTMLButtonElement) {
        triggerButton.disabled = false;
        triggerButton.textContent = "Explain with AI";
      }
    }
  }

  async function loadPostExamInsights(statusMessage = "Result loaded.", preferredTab = "summary") {
    if (!st.attemptId) {
      return;
    }
    try {
      const resultPayload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/result`,
        { headers: studentHeaders() }
      );
      st.latestResult = resultPayload;
      renderResultSummary(resultPayload);
      if (!st.receipt) {
        st.receipt = buildAcknowledgementReceipt(resultPayload);
      }
      renderReceipt(st.receipt);

      const analysisPayload = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/analysis`,
        { headers: studentHeaders() }
      );
      renderAiAnalysis(analysisPayload);
      setStage("analysis");
      setResultTab(preferredTab);
      setStatus(statusMessage);
    } catch (error) {
      setStage("analysis");
      setResultTab("summary");
      setStatus(error.message);
    }
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
      heartbeat_history: st.heartbeatHistory,
      sync_retry_count: st.syncRetryCount,
      last_sync_error: st.lastSyncError,
      clipboard_logs: st.clipboardLogs,
      tab_switch_reasons: st.tabSwitchReasons,
      option_mode: st.optionMode,
      drag_drop_mode: st.dragDropMode,
      translate_mode: st.translateMode,
      predownloaded_count: st.predownloadedCount,
      question_topic_by_id: st.questionTopicById,
      code_draft_by_question: st.codeDraftByQuestion,
      input_latency_samples: st.inputLatencySamples,
      stress_level: st.stressLevel,
      caption_size: st.captionSize,
      rough_pad: el.roughPad ? el.roughPad.value : "",
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
      if (Array.isArray(cache.heartbeat_history)) {
        st.heartbeatHistory = cache.heartbeat_history.slice(-40);
      }
      if (Array.isArray(cache.clipboard_logs)) {
        st.clipboardLogs = cache.clipboard_logs.slice(-60);
      }
      if (Array.isArray(cache.tab_switch_reasons)) {
        st.tabSwitchReasons = cache.tab_switch_reasons.slice(-20);
      }
      if (typeof cache.sync_retry_count === "number") {
        st.syncRetryCount = Math.max(0, Math.floor(cache.sync_retry_count));
      }
      if (typeof cache.last_sync_error === "string") {
        st.lastSyncError = cache.last_sync_error;
      }
      if (typeof cache.option_mode === "string") {
        st.optionMode = cache.option_mode;
      }
      st.dragDropMode = Boolean(cache.drag_drop_mode);
      st.translateMode = Boolean(cache.translate_mode);
      st.predownloadedCount = Number(cache.predownloaded_count || 0);
      if (cache.question_topic_by_id && typeof cache.question_topic_by_id === "object") {
        st.questionTopicById = { ...cache.question_topic_by_id };
      }
      if (cache.code_draft_by_question && typeof cache.code_draft_by_question === "object") {
        st.codeDraftByQuestion = { ...cache.code_draft_by_question };
      }
      if (Array.isArray(cache.input_latency_samples)) {
        st.inputLatencySamples = cache.input_latency_samples
          .map((value) => Number(value))
          .filter((value) => Number.isFinite(value))
          .slice(-80);
      }
      if (typeof cache.stress_level === "string") {
        st.stressLevel = cache.stress_level;
      }
      if (Number.isFinite(Number(cache.caption_size))) {
        st.captionSize = Number(cache.caption_size);
      }
      if (el.roughPad && typeof cache.rough_pad === "string") {
        el.roughPad.value = cache.rough_pad;
      }
      if (cache.exam_name) {
        st.examName = String(cache.exam_name);
      }
      if (cache.expires_at) {
        timerState.start(cache.expires_at);
      }
      renderAnswerTimeline();
      renderClipboardLogs();
      updateOptionModeButtons();
      updateBucketSummary();
      updateSyncDiagnostics();
      updateNetworkQuality();
      updateInputLatencyMeter();
      updateStressDetector();
      if (el.captionSize) {
        el.captionSize.value = String(st.captionSize);
      }
      updateCaptionPreview();
      renderEquationPreview();
      runMockAnalyticsMirror();
      if (el.toggleTranslate) {
        el.toggleTranslate.textContent = st.translateMode ? "Inline Translate: On" : "Inline Translate: Off";
      }
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
    updateBucketSummary();
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
      const hardClass = answerState.isHard(sequence) ? "bucket-hard" : "";
      const easyClass = answerState.isEasy(sequence) ? "bucket-easy" : "";
      const currentClass = sequence === st.sequence ? "current" : "";
      paletteButtons.push(
        `<button type="button" class="palette-btn ${stateClass} ${hardClass} ${easyClass} ${currentClass}" data-sequence="${sequence}">${sequence}</button>`
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
    st.availableExams = Array.isArray(exams) ? exams.slice() : [];
    const previousValue = el.examSelect.value;
    el.examSelect.innerHTML = '<option value="">Choose an available exam...</option>';

    for (const exam of exams) {
      const option = document.createElement("option");
      option.value = exam.id;
      option.dataset.examName = exam.name;
      option.dataset.durationMinutes = String(exam.duration_minutes || "");
      option.textContent = `${exam.name} (${exam.duration_minutes} min)`;
      el.examSelect.appendChild(option);
    }

    if (previousValue && exams.some((exam) => exam.id === previousValue)) {
      el.examSelect.value = previousValue;
    }
    renderPreExamRulesPreview();
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
    st.currentQuestionOptions = Array.isArray(payload.options) ? payload.options : [];
    st.sequence = Number(payload.sequence_number);
    answerState.setSequenceQuestion(st.sequence, payload.question.id);
    st.questionTopicById[String(payload.question.id)] = String(payload.question.topic || "untagged");
    startQuestionTimeTracking(st.sequence);

    el.examName.textContent = st.examName || st.examId || "Exam";
    el.questionText.textContent = runInlineTranslation(
      payload.question.text || "Question text unavailable."
    );

    const selectedOptionId = answerState.getSelection(payload.question.id);
    el.optionsList.innerHTML = "";

    for (const option of st.currentQuestionOptions) {
      const label = document.createElement("label");
      label.className = "choice-option";
      const eliminated = answerState.isEliminated(payload.question.id, option.id);
      const struck = answerState.isStruck(payload.question.id, option.id);
      if (eliminated) {
        label.classList.add("eliminated-option");
      }
      if (struck) {
        label.classList.add("struck-option");
      }

      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "selected-option";
      radio.value = option.id;
      radio.checked = selectedOptionId === option.id;
      radio.disabled = eliminated;

      const text = document.createElement("span");
      text.textContent = runInlineTranslation(option.option_text);
      text.className = "option-text";

      const tools = document.createElement("span");
      tools.className = "option-tools";

      const eliminateBtn = document.createElement("button");
      eliminateBtn.type = "button";
      eliminateBtn.className = "btn-outline option-mini-btn";
      eliminateBtn.dataset.optionId = option.id;
      eliminateBtn.dataset.action = "eliminate";
      eliminateBtn.textContent = eliminated ? "Un-eliminate" : "Eliminate";

      const strikeBtn = document.createElement("button");
      strikeBtn.type = "button";
      strikeBtn.className = "btn-outline option-mini-btn";
      strikeBtn.dataset.optionId = option.id;
      strikeBtn.dataset.action = "strike";
      strikeBtn.textContent = struck ? "Un-strike" : "Strike";

      label.appendChild(radio);
      label.appendChild(text);
      tools.appendChild(eliminateBtn);
      tools.appendChild(strikeBtn);
      label.appendChild(tools);
      attachDragDropHandlers(label, String(option.id));
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
    updateBucketSummary();
    updateOptionModeButtons();
    loadCodeDraftForCurrentQuestion();
    updateCaptionPreview();
    renderEquationPreview();
    runMockAnalyticsMirror();
    persistAttemptCache();
    resetInactivityTimer();
    updateMiniProgressWidget();
    updateStressDetector();
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
    if (el.toggleHardBucket) {
      el.toggleHardBucket.disabled = !active;
    }
    if (el.toggleEasyBucket) {
      el.toggleEasyBucket.disabled = !active;
    }
    if (el.toggleEliminateMode) {
      el.toggleEliminateMode.disabled = !active;
    }
    if (el.toggleStrikeMode) {
      el.toggleStrikeMode.disabled = !active;
    }
    if (el.predownloadQuestions) {
      el.predownloadQuestions.disabled = !active;
    }
    if (el.fullscreenRetry) {
      el.fullscreenRetry.disabled = !active;
    }
    if (el.replayRules) {
      el.replayRules.disabled = !active;
    }
    if (el.toggleTranslate) {
      el.toggleTranslate.disabled = !active;
    }
    if (el.instantSupport) {
      el.instantSupport.disabled = !active;
    }
    if (el.roughPad) {
      el.roughPad.disabled = !active;
    }
    if (el.equationEditor) {
      el.equationEditor.disabled = !active;
    }
    if (el.codeEditor) {
      el.codeEditor.disabled = !active;
    }
    if (el.codeLanguage) {
      el.codeLanguage.disabled = !active;
    }
    if (el.captionSize) {
      el.captionSize.disabled = !active;
    }
    if (el.playQuestionAudio) {
      el.playQuestionAudio.disabled = !active;
    }
    if (el.enableDragDropOptions) {
      el.enableDragDropOptions.disabled = !active;
    }
    if (el.generateMatchMode) {
      el.generateMatchMode.disabled = !active;
    }
    if (el.runPracticeSim) {
      el.runPracticeSim.disabled = !active;
    }
    if (el.runMockAnalytics) {
      el.runMockAnalytics.disabled = !active;
    }
    if (el.toggleCalmMode) {
      el.toggleCalmMode.disabled = !active;
    }
    if (el.clearDiagram) {
      el.clearDiagram.disabled = !active;
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
      st.syncRetryCount += 1;
      st.lastSyncError = "offline";
      setAutosaveIndicator("pending", "Pending LAN Sync");
      setStatus("LAN temporary unavailable. Answer saved locally and queued.");
      updateSyncHealthIndicator();
      updateSyncDiagnostics();
      updateStressDetector();
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
      st.lastSyncError = "";
      setAutosaveIndicator("synced", "Synced");
      updateSyncHealthIndicator();
      updateSyncDiagnostics();
      updateStressDetector();
      return true;
    } catch (error) {
      if (
        error?.httpStatus === 409 ||
        /conflict|concurrency/i.test(String(error?.message || ""))
      ) {
        const choice = await showConflictResolver({
          question_id: questionId,
          selected_option_id: selectedOptionId,
        });
        if (choice === "reload_server") {
          await refreshAttemptStatus();
          await fetchQuestion(st.sequence);
          setStatus("Server state reloaded after conflict.");
          return false;
        }
      }
      if (error?.httpStatus && error.httpStatus < 500) {
        st.syncRetryCount += 1;
        st.lastSyncError = String(error.message || "client_error");
        updateSyncDiagnostics();
        setStatus(error.message);
        updateStressDetector();
        return false;
      }
      answerState.queuePending(queueItem);
      st.syncRetryCount += 1;
      st.lastSyncError = String(error.message || "network_error");
      setAutosaveIndicator("pending", "Pending LAN Sync");
      setStatus("LAN issue detected. Answer saved locally and will auto-sync.");
      updateSyncHealthIndicator();
      updateSyncDiagnostics();
      updateStressDetector();
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
        st.lastSyncError = "";
        synced += 1;
      } catch (error) {
        if (error?.httpStatus && error.httpStatus < 500) {
          st.syncRetryCount += 1;
          st.lastSyncError = String(error.message || "client_error");
          answerState.removePending(item.question_id);
          continue;
        }
        st.syncRetryCount += 1;
        st.lastSyncError = String(error?.message || "sync_error");
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
    updateSyncDiagnostics();
    updateStressDetector();
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
      setStage("exam");
    } else if (status === "PAUSED") {
      setPausedState(true);
      setStage("exam");
    } else if (status === "FINALIZED" || status === "GRADED" || status === "ARCHIVED") {
      st.finalized = true;
      st.paused = false;
      setAttemptControlsEnabled(false);
      timerState.stop();
      setStatus("Attempt finalized by admin/system. View result.");
      setStage("analysis");
      if (!st.latestResult) {
        loadPostExamInsights("Attempt finalized by admin/system. Result loaded.", "summary").catch(() => {
          return;
        });
      }
    } else {
      setAttemptControlsEnabled(false);
    }

    updateProgress();
    renderPalette();
    updateIntegrityHash().catch(() => {
      return;
    });
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
      st.currentQuestionOptions = [];
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
      st.heartbeatHistory = [];
      st.syncRetryCount = 0;
      st.lastSyncError = "";
      st.clipboardLogs = [];
      st.tabSwitchReasons = [];
      st.optionMode = "none";
      st.dragDropMode = false;
      st.questionTopicById = {};
      st.codeDraftByQuestion = {};
      st.inputLatencySamples = [];
      st.stressLevel = "normal";
      st.captionSize = 16;
      st.latestResult = null;
      st.latestAnalysis = null;
      st.analysisExplanationByQuestion = {};
      st.utilityTab = "palette";
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
      if (el.receiptQrBox) {
        el.receiptQrBox.textContent = "Signed QR receipt will appear here after submission.";
      }
      if (el.topicStrengthBox) {
        el.topicStrengthBox.textContent = "Topic strength map will appear here after submission.";
      }
      if (el.weakTopicPlanBox) {
        el.weakTopicPlanBox.textContent = "Weak-topic action plan will appear here after submission.";
      }
      if (el.analysisOverviewBox) {
        el.analysisOverviewBox.textContent = "AI exam analysis will appear here after submission.";
      }
      if (el.analysisLearningPathBox) {
        el.analysisLearningPathBox.textContent = "Personalized learning path will appear here after submission.";
      }
      if (el.analysisListBox) {
        el.analysisListBox.textContent = "Incorrect and skipped questions will appear here after submission.";
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
      renderClipboardLogs();
      updateMiniProgressWidget();
      updateBucketSummary();
      updateOptionModeButtons();
      updateSyncDiagnostics();
      updateNetworkQuality();
      updateInputLatencyMeter();
      updateStressDetector();
      if (el.practiceSimBox) {
        el.practiceSimBox.textContent = "Practice simulation output will appear here.";
      }
      if (el.mockAnalyticsBox) {
        el.mockAnalyticsBox.textContent = "Mock analytics mirror will appear here.";
      }
      if (el.matchModeBox) {
        el.matchModeBox.textContent = "Match mode not generated yet.";
      }
      if (el.equationEditor) {
        el.equationEditor.value = "";
      }
      if (el.codeEditor) {
        el.codeEditor.value = "";
      }
      if (el.captionSize) {
        el.captionSize.value = "16";
      }
      updateCaptionPreview();
      clearDiagramCanvas();
      await updateIntegrityHash();
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
      startExamTipsFeed();
      setStage("exam");
      setResultTab("summary");
      setUtilityTab("palette");
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

  function toggleHardBucket() {
    if (!st.attemptId || st.finalized || st.paused) {
      return;
    }
    const active = answerState.toggleHard(st.sequence);
    updateBucketSummary();
    setStatus(active ? `Q${st.sequence} added to hard bucket.` : `Q${st.sequence} removed from hard bucket.`);
  }

  function toggleEasyBucket() {
    if (!st.attemptId || st.finalized || st.paused) {
      return;
    }
    const active = answerState.toggleEasy(st.sequence);
    updateBucketSummary();
    setStatus(active ? `Q${st.sequence} added to easy bucket.` : `Q${st.sequence} removed from easy bucket.`);
  }

  function toggleOptionMode(nextMode) {
    st.optionMode = st.optionMode === nextMode ? "none" : nextMode;
    updateOptionModeButtons();
  }

  async function predownloadOfflinePacket() {
    if (!st.attemptId || st.finalized || st.paused) {
      setStatus("Start active attempt first.");
      return;
    }
    const total = Number(st.totalQuestions || 0);
    if (!total) {
      setStatus("Question count unavailable.");
      return;
    }
    let loaded = 0;
    for (let sequence = 1; sequence <= total; sequence += 1) {
      try {
        const questionPayload = await api(
          `/student/attempts/${encodeURIComponent(st.attemptId)}/questions/${sequence}`,
          { headers: studentHeaders() }
        );
        answerState.setSequenceQuestion(sequence, questionPayload.question.id);
        st.questionTopicById[String(questionPayload.question.id)] = String(
          questionPayload.question.topic || "untagged"
        );
        loaded += 1;
      } catch {
        break;
      }
    }
    st.predownloadedCount = loaded;
    persistAttemptCache();
    setStatus(`Offline packet prepared: ${loaded}/${total} questions cached.`);
  }

  async function retryFullscreen() {
    if (!document.documentElement.requestFullscreen) {
      setStatus("Fullscreen API unsupported in this browser.");
      return;
    }
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      }
      setStatus("Fullscreen active.");
    } catch (error) {
      setStatus(`Fullscreen request failed: ${error.message}`);
    }
  }

  function replayRulesAcknowledgement() {
    if (!el.rulesContent) {
      return;
    }
    loadExamRules();
    el.rulesContent.hidden = false;
    if (el.toggleRules) {
      el.toggleRules.textContent = "Hide";
    }
    setStatus("Rules replay opened.");
  }

  function toggleInlineTranslate() {
    st.translateMode = !st.translateMode;
    if (el.toggleTranslate) {
      el.toggleTranslate.textContent = st.translateMode ? "Inline Translate: On" : "Inline Translate: Off";
    }
    if (st.currentQuestion && st.currentQuestionOptions.length) {
      renderQuestion({
        question: st.currentQuestion,
        options: st.currentQuestionOptions,
        sequence_number: st.sequence,
      });
    }
    setStatus(st.translateMode ? "Inline translation enabled." : "Inline translation disabled.");
  }

  async function instantSupportRequest() {
    if (!st.attemptId || st.finalized) {
      setStatus("Active attempt required.");
      return;
    }
    try {
      await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/technical-issue`, {
        method: "POST",
        headers: studentHeaders(),
        body: {
          issue_type: "instant_support",
          note: "Student requested instant support from quick action.",
        },
      });
      setStatus("Instant support request sent to proctor/admin.");
      playAlertTone(520, 140);
    } catch (error) {
      setStatus(error.message);
    }
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
    const hardCount = answerState.getHardCount();
    const easyCount = answerState.getEasyCount();
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
      {
        label: "Strategy buckets",
        ok: hardCount + easyCount > 0,
        detail: `hard=${hardCount}, easy=${easyCount}`,
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
    st.optionMode = "none";
    st.autoSubmitInProgress = false;
    setAttemptControlsEnabled(false);
    timerState.stop();
    if (st.inactivityTimerId) {
      clearTimeout(st.inactivityTimerId);
      st.inactivityTimerId = null;
    }
    closeInactivityModal();
    closeGlossaryModal();
    closeShortcutsModal();
    closeConflictResolver("keep_local");
    closeResumeWizard("resume");
    closeCalmMode();
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
    stopExamTipsFeed();
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
    st.latestResult = finalizePayload.result || finalizePayload;
    setStage("analysis");
    setResultTab("summary");
    setStatus(statusMessage);
    renderAttemptMeta({
      started_at: null,
      expires_at: timerState.getExpiresAt(),
      status: "FINALIZED",
    });
    closeSubmitModal();
    updateOptionModeButtons();
    loadPostExamInsights(statusMessage, "summary").catch(() => {
      return;
    });
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
    await loadPostExamInsights("Result loaded.", "summary");
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
    stopExamTipsFeed();
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
    const resumeChoice = await openResumeWizard(cached);
    if (resumeChoice === "fresh") {
      const key = `${ATTEMPT_CACHE_PREFIX}${cached.attempt_id}`;
      localStorage.removeItem(key);
      setStatus("Local draft discarded. Fresh start mode enabled.");
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
    st.heartbeatHistory = Array.isArray(cached.heartbeat_history)
      ? cached.heartbeat_history.slice(-40)
      : [];
    st.syncRetryCount = Number(cached.sync_retry_count || 0);
    st.lastSyncError = String(cached.last_sync_error || "");
    st.clipboardLogs = Array.isArray(cached.clipboard_logs)
      ? cached.clipboard_logs.slice(-60)
      : [];
    st.tabSwitchReasons = Array.isArray(cached.tab_switch_reasons)
      ? cached.tab_switch_reasons.slice(-20)
      : [];
    st.optionMode = String(cached.option_mode || "none");
    st.dragDropMode = Boolean(cached.drag_drop_mode);
    st.translateMode = Boolean(cached.translate_mode);
    st.predownloadedCount = Number(cached.predownloaded_count || 0);
    st.latestResult = null;
    st.latestAnalysis = null;
    st.analysisExplanationByQuestion = {};
    st.questionTopicById =
      cached.question_topic_by_id && typeof cached.question_topic_by_id === "object"
        ? { ...cached.question_topic_by_id }
        : {};
    st.codeDraftByQuestion =
      cached.code_draft_by_question && typeof cached.code_draft_by_question === "object"
        ? { ...cached.code_draft_by_question }
        : {};
    st.inputLatencySamples = Array.isArray(cached.input_latency_samples)
      ? cached.input_latency_samples
          .map((value) => Number(value))
          .filter((value) => Number.isFinite(value))
          .slice(-80)
      : [];
    st.stressLevel = String(cached.stress_level || "normal");
    st.captionSize = Number.isFinite(Number(cached.caption_size))
      ? Number(cached.caption_size)
      : 16;
    if (el.roughPad && typeof cached.rough_pad === "string") {
      el.roughPad.value = cached.rough_pad;
    }
    if (el.captionSize) {
      el.captionSize.value = String(st.captionSize);
    }

    answerState.hydrate(cached);
    timerState.start(cached.expires_at || null);
    renderAnswerTimeline();
    renderClipboardLogs();
    renderBroadcasts(st.broadcastHistory);
    updateOptionModeButtons();
    updateBucketSummary();
    updateSyncDiagnostics();
    updateNetworkQuality();
    updateInputLatencyMeter();
    updateStressDetector();
    updateCaptionPreview();
    renderEquationPreview();
    runMockAnalyticsMirror();
    if (el.toggleTranslate) {
      el.toggleTranslate.textContent = st.translateMode ? "Inline Translate: On" : "Inline Translate: Off";
    }
    updateMiniProgressWidget();
    setUtilityTab("palette");

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
    if (el.examSelect) {
      el.examSelect.addEventListener("change", () => {
        renderPreExamRulesPreview();
      });
    }
    if (el.previewRules) {
      el.previewRules.addEventListener("click", () => {
        renderPreExamRulesPreview();
        setStatus("Pre-exam rules preview refreshed.");
      });
    }
    if (el.resultTabSummary) {
      el.resultTabSummary.addEventListener("click", () => {
        setResultTab("summary");
      });
    }
    if (el.resultTabAi) {
      el.resultTabAi.addEventListener("click", () => {
        setResultTab("ai");
      });
    }
    if (el.utilityTabWorkspace) {
      el.utilityTabWorkspace.addEventListener("click", () => {
        setUtilityTab("workspace");
      });
    }
    if (el.utilityTabPalette) {
      el.utilityTabPalette.addEventListener("click", () => {
        setUtilityTab("palette");
      });
    }
    if (el.utilityTabMonitor) {
      el.utilityTabMonitor.addEventListener("click", () => {
        setUtilityTab("monitor");
      });
    }
    if (el.utilityTabSupport) {
      el.utilityTabSupport.addEventListener("click", () => {
        setUtilityTab("support");
      });
    }
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
    if (el.resumeFromCache) {
      el.resumeFromCache.addEventListener("click", () => {
        closeResumeWizard("resume");
      });
    }
    if (el.discardCacheStartFresh) {
      el.discardCacheStartFresh.addEventListener("click", () => {
        closeResumeWizard("fresh");
      });
    }
    if (el.conflictKeepLocal) {
      el.conflictKeepLocal.addEventListener("click", () => {
        closeConflictResolver("keep_local");
      });
    }
    if (el.conflictReloadServer) {
      el.conflictReloadServer.addEventListener("click", () => {
        closeConflictResolver("reload_server");
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
    if (el.colorblindToggle) {
      el.colorblindToggle.addEventListener("change", () => {
        uiPrefs.colorblind = Boolean(el.colorblindToggle.checked);
        applyUiPrefs();
        persistUiPrefs();
      });
    }
    if (el.reducedMotionToggle) {
      el.reducedMotionToggle.addEventListener("change", () => {
        uiPrefs.reducedMotion = Boolean(el.reducedMotionToggle.checked);
        applyUiPrefs();
        persistUiPrefs();
      });
    }
    if (el.largeCursorToggle) {
      el.largeCursorToggle.addEventListener("change", () => {
        uiPrefs.largeCursor = Boolean(el.largeCursorToggle.checked);
        applyUiPrefs();
        persistUiPrefs();
      });
    }
    if (el.soundAlertToggle) {
      el.soundAlertToggle.addEventListener("change", () => {
        uiPrefs.soundAlerts = Boolean(el.soundAlertToggle.checked);
        persistUiPrefs();
      });
    }
    if (el.soundVolume) {
      el.soundVolume.addEventListener("input", () => {
        uiPrefs.soundVolume = Number(el.soundVolume.value || "60");
        persistUiPrefs();
      });
    }
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
    if (el.toggleHardBucket) {
      el.toggleHardBucket.addEventListener("click", toggleHardBucket);
    }
    if (el.toggleEasyBucket) {
      el.toggleEasyBucket.addEventListener("click", toggleEasyBucket);
    }
    if (el.toggleEliminateMode) {
      el.toggleEliminateMode.addEventListener("click", () => {
        toggleOptionMode("eliminate");
      });
    }
    if (el.toggleStrikeMode) {
      el.toggleStrikeMode.addEventListener("click", () => {
        toggleOptionMode("strike");
      });
    }
    if (el.predownloadQuestions) {
      el.predownloadQuestions.addEventListener("click", predownloadOfflinePacket);
    }
    if (el.fullscreenRetry) {
      el.fullscreenRetry.addEventListener("click", retryFullscreen);
    }
    if (el.replayRules) {
      el.replayRules.addEventListener("click", replayRulesAcknowledgement);
    }
    if (el.openGlossary) {
      el.openGlossary.addEventListener("click", openGlossaryModal);
    }
    if (el.closeGlossary) {
      el.closeGlossary.addEventListener("click", closeGlossaryModal);
    }
    if (el.toggleTranslate) {
      el.toggleTranslate.addEventListener("click", toggleInlineTranslate);
    }
    if (el.instantSupport) {
      el.instantSupport.addEventListener("click", instantSupportRequest);
    }
    if (el.roughPad) {
      el.roughPad.addEventListener("input", () => {
        persistAttemptCache();
      });
    }
    if (el.runPracticeSim) {
      el.runPracticeSim.addEventListener("click", runPracticeSimulation);
    }
    if (el.runMockAnalytics) {
      el.runMockAnalytics.addEventListener("click", runMockAnalyticsMirror);
    }
    if (el.equationEditor) {
      el.equationEditor.addEventListener("input", () => {
        renderEquationPreview();
        persistAttemptCache();
      });
    }
    if (el.codeEditor) {
      el.codeEditor.addEventListener("input", persistCodeDraft);
    }
    if (el.codeLanguage) {
      el.codeLanguage.addEventListener("change", persistCodeDraft);
    }
    if (el.captionSize) {
      el.captionSize.addEventListener("input", () => {
        updateCaptionPreview();
        persistAttemptCache();
      });
    }
    if (el.playQuestionAudio) {
      el.playQuestionAudio.addEventListener("click", playQuestionAudio);
    }
    if (el.enableDragDropOptions) {
      el.enableDragDropOptions.addEventListener("click", toggleDragDropAnswerMode);
    }
    if (el.generateMatchMode) {
      el.generateMatchMode.addEventListener("click", generateMatchMode);
    }
    if (el.toggleCalmMode) {
      el.toggleCalmMode.addEventListener("click", openCalmMode);
    }
    if (el.closeCalmMode) {
      el.closeCalmMode.addEventListener("click", closeCalmMode);
    }
    if (el.clearDiagram) {
      el.clearDiagram.addEventListener("click", () => {
        clearDiagramCanvas();
        appendAnswerTimeline("diagram_cleared", st.sequence);
      });
    }
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
    if (el.analysisListBox) {
      el.analysisListBox.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
          return;
        }
        const button = target.closest("button[data-question-id]");
        if (!(button instanceof HTMLButtonElement)) {
          return;
        }
        explainQuestionWithAi(button.dataset.questionId || "", button);
      });
    }
    el.startBreathing.addEventListener("click", startBreathingPrompt);
    el.runDiagnostics.addEventListener("click", runDeviceDiagnostics);
    el.enterRevision.addEventListener("click", enterRevisionMode);
    el.printResult.addEventListener("click", printResultSlip);
    el.submitExam.addEventListener("click", openSubmitModal);
    el.cancelSubmit.addEventListener("click", closeSubmitModal);
    el.confirmSubmit.addEventListener("click", confirmSubmitExam);
    el.viewResult.addEventListener("click", viewResult);
    el.refreshMorale.addEventListener("click", loadMoraleCoach);

    el.optionsList.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement) || !st.currentQuestion) {
        return;
      }
      const miniButton = target.closest("button[data-action][data-option-id]");
      if (miniButton) {
        event.preventDefault();
        const optionId = miniButton.dataset.optionId || "";
        const action = miniButton.dataset.action || "";
        if (action === "eliminate") {
          answerState.toggleEliminate(st.currentQuestion.id, optionId);
          appendAnswerTimeline("option_eliminated", st.sequence);
          renderQuestion({
            question: st.currentQuestion,
            options: st.currentQuestionOptions,
            sequence_number: st.sequence,
          });
        } else if (action === "strike") {
          answerState.toggleStrike(st.currentQuestion.id, optionId);
          appendAnswerTimeline("option_struck", st.sequence);
          renderQuestion({
            question: st.currentQuestion,
            options: st.currentQuestionOptions,
            sequence_number: st.sequence,
          });
        }
        return;
      }

      if (st.optionMode !== "none") {
        const label = target.closest("label.choice-option");
        const radio = label?.querySelector('input[name="selected-option"]');
        if (radio instanceof HTMLInputElement) {
          event.preventDefault();
          if (st.optionMode === "eliminate") {
            answerState.toggleEliminate(st.currentQuestion.id, radio.value);
            appendAnswerTimeline("option_eliminated", st.sequence);
          } else if (st.optionMode === "strike") {
            answerState.toggleStrike(st.currentQuestion.id, radio.value);
            appendAnswerTimeline("option_struck", st.sequence);
          }
          renderQuestion({
            question: st.currentQuestion,
            options: st.currentQuestionOptions,
            sequence_number: st.sequence,
          });
        }
      }
    });

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
        if (st.hiddenSince && st.attemptId && !st.finalized) {
          const reason = window.prompt(
            "Tab switch reason (optional):",
            "Accidental switch"
          );
          st.tabSwitchReasons.push({
            at: new Date().toISOString(),
            reason: String(reason || "not_provided"),
          });
          if (st.tabSwitchReasons.length > 20) {
            st.tabSwitchReasons = st.tabSwitchReasons.slice(-20);
          }
          persistAttemptCache();
        }
        st.hiddenSince = null;
        return;
      }
      st.hiddenSince = new Date().toISOString();
      st.warningCount += 1;
      playAlertTone(460, 190);
      showAntiCheatWarning(
        `Warning ${st.warningCount}: Tab switch detected. Stay on exam screen.`
      );
      updateStressDetector();
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
    document.addEventListener("click", () => {
      const start = typeof performance !== "undefined" ? performance.now() : Date.now();
      window.requestAnimationFrame(() => {
        recordInputLatencySample(start);
      });
    });
    document.addEventListener("copy", (event) => {
      event.preventDefault();
      st.clipboardLogs.push({ at: new Date().toISOString(), kind: "copy_blocked" });
      if (st.clipboardLogs.length > 60) {
        st.clipboardLogs = st.clipboardLogs.slice(-60);
      }
      renderClipboardLogs();
      persistAttemptCache();
      playAlertTone(430, 120);
      updateStressDetector();
    });
    document.addEventListener("cut", (event) => {
      event.preventDefault();
      st.clipboardLogs.push({ at: new Date().toISOString(), kind: "cut_blocked" });
      if (st.clipboardLogs.length > 60) {
        st.clipboardLogs = st.clipboardLogs.slice(-60);
      }
      renderClipboardLogs();
      persistAttemptCache();
      playAlertTone(430, 120);
      updateStressDetector();
    });
    document.addEventListener("paste", (event) => {
      event.preventDefault();
      st.clipboardLogs.push({ at: new Date().toISOString(), kind: "paste_blocked" });
      if (st.clipboardLogs.length > 60) {
        st.clipboardLogs = st.clipboardLogs.slice(-60);
      }
      renderClipboardLogs();
      persistAttemptCache();
      playAlertTone(430, 120);
      updateStressDetector();
    });

    window.addEventListener("online", () => {
      flushPendingQueue();
      setStatus("LAN reconnected. Syncing saved answers...");
      updateSyncHealthIndicator();
      pingServerHeartbeat();
      pullBroadcasts();
      updateSyncDiagnostics();
      updateStressDetector();
    });

    window.addEventListener("offline", () => {
      updateSyncHealthIndicator();
      updateHeartbeatIndicator("offline", "Server: Unreachable");
      updateNetworkQuality();
      updateSyncDiagnostics();
      playAlertTone(420, 150);
      updateStressDetector();
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
      stopExamTipsFeed();
      stopQuestionTimeTracking();
      stopBreathingPrompt();
    });

    window.addEventListener("keydown", (event) => {
      const start = typeof performance !== "undefined" ? performance.now() : Date.now();
      window.requestAnimationFrame(() => {
        recordInputLatencySample(start);
      });
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
      if (event.key === "Escape" && el.glossaryModal && !el.glossaryModal.hidden) {
        closeGlossaryModal();
        return;
      }
      if (event.key === "Escape" && el.conflictModal && !el.conflictModal.hidden) {
        closeConflictResolver("keep_local");
        return;
      }
      if (event.key === "Escape" && el.resumeWizardModal && !el.resumeWizardModal.hidden) {
        closeResumeWizard("resume");
        return;
      }
      if (event.key === "Escape" && el.calmModeOverlay && !el.calmModeOverlay.hidden) {
        closeCalmMode();
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
    if (el.resultExplainBox) {
      el.resultExplainBox.textContent = "Result explanation cards will appear here after submission.";
    }
    if (el.attemptCompareBox) {
      el.attemptCompareBox.textContent = "Attempt comparison insights will appear here after at least 2 attempts.";
    }
    if (el.topicStrengthBox) {
      el.topicStrengthBox.textContent = "Topic strength map will appear here after submission.";
    }
    if (el.weakTopicPlanBox) {
      el.weakTopicPlanBox.textContent = "Weak-topic action plan will appear here after submission.";
    }
    if (el.analysisOverviewBox) {
      el.analysisOverviewBox.textContent = "AI exam analysis will appear here after submission.";
    }
    if (el.analysisLearningPathBox) {
      el.analysisLearningPathBox.textContent = "Personalized learning path will appear here after submission.";
    }
    if (el.analysisListBox) {
      el.analysisListBox.textContent = "Incorrect and skipped questions will appear here after submission.";
    }
    if (el.networkQuality) {
      el.networkQuality.textContent = "Network quality: waiting...";
    }
    if (el.syncDiagnostics) {
      el.syncDiagnostics.textContent = "Sync diagnostics: waiting...";
    }
    if (el.integrityHash) {
      el.integrityHash.textContent = "Integrity checksum: -";
    }
    if (el.clipboardLog) {
      el.clipboardLog.textContent = "No clipboard attempts yet.";
    }
    if (el.tipsFeed) {
      el.tipsFeed.textContent = "Tip feed loading...";
    }
    if (el.inputLatencyMeter) {
      el.inputLatencyMeter.textContent = "Input latency: waiting...";
    }
    if (el.stressDetector) {
      el.stressDetector.textContent = "Stress detector: normal";
    }
    if (el.practiceSimBox) {
      el.practiceSimBox.textContent = "Practice simulation output will appear here.";
    }
    if (el.mockAnalyticsBox) {
      el.mockAnalyticsBox.textContent = "Mock analytics mirror will appear here.";
    }
    if (el.matchModeBox) {
      el.matchModeBox.textContent = "Match mode not generated yet.";
    }
    if (el.equationPreview) {
      el.equationPreview.textContent = "Equation preview will appear here.";
    }
    if (el.receiptQrBox) {
      el.receiptQrBox.textContent = "Signed QR receipt will appear here after submission.";
    }
    if (el.roughPad) {
      el.roughPad.value = "";
    }
    if (el.equationEditor) {
      el.equationEditor.value = "";
    }
    if (el.codeEditor) {
      el.codeEditor.value = "";
    }
    if (el.captionSize) {
      el.captionSize.value = "16";
    }
    updateCaptionPreview();
    st.broadcastHistory = [];
    if (el.shortcutsModal) {
      el.shortcutsModal.hidden = true;
    }
    if (el.resumeWizardModal) {
      el.resumeWizardModal.hidden = true;
    }
    if (el.glossaryModal) {
      el.glossaryModal.hidden = true;
    }
    if (el.conflictModal) {
      el.conflictModal.hidden = true;
    }
    if (el.calmModeOverlay) {
      el.calmModeOverlay.hidden = true;
    }
    st.dragDropMode = false;
    st.questionTopicById = {};
    st.codeDraftByQuestion = {};
    st.inputLatencySamples = [];
    st.stressLevel = "normal";
    st.captionSize = 16;
    st.uiStage = "lobby";
    st.analysisTab = "summary";
    st.latestResult = null;
    st.latestAnalysis = null;
    st.analysisExplanationByQuestion = {};
    st.availableExams = [];
    renderAnswerTimeline();
    renderClipboardLogs();
    updateBucketSummary();
    updateOptionModeButtons();
    updateMiniProgressWidget();
    updateSyncDiagnostics();
    updateInputLatencyMeter();
    updateStressDetector();
    initializeDiagramCanvas();
    clearDiagramCanvas();
    renderExamTips();
    startExamTipsFeed();
    initializeExamUtilityHub();
    setStage("lobby");
    setResultTab("summary");
    setUtilityTab("palette");
    renderPreExamRulesPreview();
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
