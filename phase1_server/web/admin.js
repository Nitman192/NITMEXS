(() => {
  const SESSION_KEY = "nitmexs_admin_session";
  const DRAWER_STATE_KEY = "nitmexs_admin_drawer_collapsed";
  const $ = (id) => document.getElementById(id);
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  const friendlyFieldLabel = (field) => {
    const map = {
      student_id: "Student ID",
      admin_id: "Admin ID",
      access_key: "access key",
      password: "password",
      display_name: "display name",
      new_exam_name: "exam name",
      question_text: "question text",
      marks_awarded: "marks",
    };
    if (!field) return "";
    return map[field] || String(field).replaceAll("_", " ");
  };
  const extractFieldFromLoc = (loc) => {
    if (!Array.isArray(loc)) return "";
    for (let index = loc.length - 1; index >= 0; index -= 1) {
      const item = loc[index];
      if (typeof item === "string" && !["body", "query", "path"].includes(item)) {
        return item;
      }
    }
    return "";
  };
  const friendlyErrorText = (message, field = "") => {
    const text = String(message || "").trim();
    const label = friendlyFieldLabel(field);
    if (!text) return "";
    if (/field required/i.test(text)) {
      return label ? `Please enter ${label}.` : "Please fill in the required details and try again.";
    }
    const minMatch = text.match(/at least (\d+) characters?/i);
    if (minMatch) {
      return label
        ? `${label.charAt(0).toUpperCase() + label.slice(1)} must be at least ${minMatch[1]} characters long.`
        : `Please enter at least ${minMatch[1]} characters.`;
    }
    const maxMatch = text.match(/at most (\d+) characters?/i);
    if (maxMatch) {
      return label
        ? `${label.charAt(0).toUpperCase() + label.slice(1)} must be ${maxMatch[1]} characters or fewer.`
        : `Please keep the text within ${maxMatch[1]} characters.`;
    }
    if (/invalid .*credentials|incorrect|authentication failed/i.test(text)) {
      return "The ID or password you entered is not correct. Please try again.";
    }
    if (/trusted host machine/i.test(text)) {
      return "This admin action works only on the trusted host machine.";
    }
    if (/already exists/i.test(text)) {
      return label
        ? `This ${label.toLowerCase()} is already in use. Please choose a different one.`
        : "This value is already in use. Please choose a different one.";
    }
    if (/not found/i.test(text)) {
      return "The requested record could not be found.";
    }
    if (/input should be|unable to validate/i.test(text)) {
      return label
        ? `Please check ${label} and try again.`
        : "Please check the entered details and try again.";
    }
    return text.charAt(0).toUpperCase() + text.slice(1);
  };
  const explainApiError = (detail) => {
    if (detail == null || detail === "") return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => explainApiError(item)).filter(Boolean)[0] || "";
    }
    if (typeof detail === "object") {
      if (typeof detail.msg === "string") {
        const field = extractFieldFromLoc(detail.loc);
        return friendlyErrorText(detail.msg, field);
      }
      if (typeof detail.detail === "string") return friendlyErrorText(detail.detail);
      return Object.entries(detail)
        .map(([, value]) => explainApiError(value))
        .filter(Boolean)[0] || "";
    }
    return String(detail);
  };

  const st = {
    adminId: "",
    role: "superadmin",
    exams: [],
    questions: [],
    selectedExamId: "",
    selectedQuestion: null,
    activeTab: "dashboard",
    examResults: [],
    analyticsData: null,
    analyticsUi: {
      showQuestionIds: false,
      questionSearch: "",
      questionFilter: "all",
      questionSort: "correct_desc",
      difficultySearch: "",
      difficultyFilter: "all",
      difficultySort: "difficulty_index_asc",
    },
    drawerCollapsed: false,
  };

  const el = {
    sessionAdmin: $("session-admin"),
    version: $("version"),
    selectedExamChip: $("selected-exam-chip"),
    adminDrawer: $("admin-drawer"),
    toggleAdminDrawer: $("toggle-admin-drawer"),
    openDownloadsTop: $("open-downloads-top"),
    logoutAdmin: $("logout-admin"),
    status: $("admin-status"),
    loadExams: $("load-exams"),
    newExamName: $("new-exam-name"),
    newExamDuration: $("new-exam-duration"),
    newExamNegativeMarking: $("new-exam-negative-marking"),
    createExam: $("create-exam"),
    examSelect: $("exam-select"),
    referenceExamSelect: $("reference-exam-select"),
    customRulesText: $("custom-rules-text"),
    saveCustomRules: $("save-custom-rules"),
    saveReferenceExam: $("save-reference-exam"),
    publishExam: $("publish-exam"),
    closeExam: $("close-exam"),
    deleteExam: $("delete-exam"),
    refreshLive: $("refresh-live"),
    pauseExam: $("pause-exam"),
    resumeExam: $("resume-exam"),
    examControlReason: $("exam-control-reason"),
    freezeTimerToggle: $("freeze-timer-toggle"),
    forceAttemptId: $("force-attempt-id"),
    forceSubmitAttempt: $("force-submit-attempt"),
    forceSubmitExpired: $("force-submit-expired"),
    broadcastMessage: $("broadcast-message"),
    broadcastSeverity: $("broadcast-severity"),
    sendBroadcast: $("send-broadcast"),
    liveSummary: $("live-summary"),
    forceSubmitResult: $("force-submit-result"),
    broadcastResult: $("broadcast-result"),
    activeBody: $("active-body"),
    questionCsvFile: $("question-csv-file"),
    uploadQuestionCsv: $("upload-question-csv"),
    questionUploadResult: $("question-upload-result"),
    examPackFile: $("exam-pack-file"),
    uploadExamPack: $("upload-exam-pack"),
    examPackResult: $("exam-pack-result"),
    loadQuestions: $("load-questions"),
    questionType: $("question-type"),
    questionTopic: $("question-topic"),
    questionDifficulty: $("question-difficulty"),
    questionMarks: $("question-marks"),
    questionText: $("question-text"),
    questionOptions: $("question-options"),
    wordTargetMin: $("word-target-min"),
    wordTargetMax: $("word-target-max"),
    wordHardMax: $("word-hard-max"),
    createQuestion: $("create-question"),
    questionCreateResult: $("question-create-result"),
    questionsBody: $("questions-body"),
    studentPreviewBox: $("student-preview-box"),
    studentIdInput: $("student-id-input"),
    studentNameInput: $("student-name-input"),
    studentPasswordInput: $("student-password-input"),
    studentPasswordToggle: $("student-password-toggle"),
    studentPasswordCapsWarning: $("student-password-caps-warning"),
    createStudentId: $("create-student-id"),
    studentPrefix: $("student-prefix"),
    studentCount: $("student-count"),
    generateStudentIds: $("generate-student-ids"),
    studentCsvFile: $("student-csv-file"),
    uploadStudentCsv: $("upload-student-csv"),
    exportStudentCsv: $("export-student-csv"),
    refreshStudentIds: $("refresh-student-ids"),
    studentIdResult: $("student-id-result"),
    studentCsvResult: $("student-csv-result"),
    studentsBody: $("students-body"),
    loadFibReview: $("load-fib-review"),
    fibReviewBody: $("fib-review-body"),
    loadSubjectiveReview: $("load-subjective-review"),
    subjectiveReviewBody: $("subjective-review-body"),
    auditEntityType: $("audit-entity-type"),
    auditEntityId: $("audit-entity-id"),
    auditEventType: $("audit-event-type"),
    loadAuditEvents: $("load-audit-events"),
    auditEventsBody: $("audit-events-body"),
    loadAccessProfile: $("load-access-profile"),
    accessProfileBox: $("access-profile-box"),
    loadMetrics: $("load-metrics"),
    metricsBox: $("metrics-box"),
    generateExamSummary: $("generate-exam-summary"),
    loadExamAnalytics: $("load-exam-analytics"),
    loadExamAnalyticsSecondary: $("load-exam-analytics-secondary"),
    examSummaryBox: $("exam-summary-box"),
    analyticsBox: $("analytics-box"),
    dashboardOverview: $("dashboard-overview"),
    loadAiStatus: $("load-ai-status"),
    aiStatusBox: $("ai-status-box"),
    aiQuestionText: $("ai-question-text"),
    aiQuestionType: $("ai-question-type"),
    aiQuestionTopic: $("ai-question-topic"),
    aiQuestionMarks: $("ai-question-marks"),
    aiRefineQuestion: $("ai-refine-question"),
    aiQuestionResult: $("ai-question-result"),
    aiRubricQuestion: $("ai-rubric-question"),
    aiRubricType: $("ai-rubric-type"),
    aiRubricMarks: $("ai-rubric-marks"),
    aiRubricSuggest: $("ai-rubric-suggest"),
    aiRubricResult: $("ai-rubric-result"),
    aiFibQuestion: $("ai-fib-question"),
    aiFibAnswers: $("ai-fib-answers"),
    aiFibCluster: $("ai-fib-cluster"),
    aiFibResult: $("ai-fib-result"),
    aiSubjectiveQuestion: $("ai-subjective-question"),
    aiSubjectiveType: $("ai-subjective-type"),
    aiSubjectiveMarks: $("ai-subjective-marks"),
    aiSubjectiveAnswer: $("ai-subjective-answer"),
    aiSubjectiveSuggest: $("ai-subjective-suggest"),
    aiSubjectiveResult: $("ai-subjective-result"),
    aiSummarizeAnalytics: $("ai-summarize-analytics"),
    aiAnalyticsBox: $("ai-analytics-box"),
    refreshResults: $("refresh-results"),
    publishResults: $("publish-results"),
    unpublishResults: $("unpublish-results"),
    downloadResultsCsv: $("download-results-csv"),
    downloadPendingCsv: $("download-pending-csv"),
    resultsPublicationBox: $("results-publication-box"),
    resultsCandidatesBody: $("results-candidates-body"),
    loadArtifacts: $("load-artifacts"),
    artifactsBody: $("artifacts-body"),
    adminAccountsPanel: $("admin-accounts-panel"),
    newAdminId: $("new-admin-id"),
    newAdminName: $("new-admin-name"),
    newAdminRole: $("new-admin-role"),
    newAdminKey: $("new-admin-key"),
    newAdminKeyToggle: $("new-admin-key-toggle"),
    newAdminKeyCapsWarning: $("new-admin-key-caps-warning"),
    createAdminAccount: $("create-admin-account"),
    loadAdminAccounts: $("load-admin-accounts"),
    adminAccountResult: $("admin-account-result"),
    adminAccountsBody: $("admin-accounts-body"),
    errorDialog: $("admin-error-dialog"),
    errorText: $("admin-error-text"),
    errorClose: $("admin-error-close"),
  };

  const adminTabButtons = () => Array.from(document.querySelectorAll("[data-admin-tab]"));
  const adminTabPanels = () => Array.from(document.querySelectorAll("[data-admin-panel]"));

  function openDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "open");
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }

  function showErrorDialog(message) {
    if (!el.errorDialog || !el.errorText) return;
    el.errorText.textContent = String(message ?? "Something went wrong.");
    openDialog(el.errorDialog);
  }

  function setStatus(message, isError = false) {
    if (!el.status) return;
    el.status.textContent = String(message ?? "");
    el.status.classList.toggle("error", isError);
    if (isError && message) {
      showErrorDialog(message);
    }
  }

  function bindPasswordControls(input, toggle, warning) {
    if (!input || !toggle) return;
    let capsLockOn = false;

    const syncToggle = () => {
      const isVisible = input.type === "text";
      toggle.textContent = isVisible ? "Hide" : "Show";
      toggle.setAttribute("aria-pressed", String(isVisible));
      toggle.setAttribute("aria-label", `${isVisible ? "Hide" : "Show"} password`);
    };

    const syncWarning = () => {
      if (!warning) return;
      warning.hidden = !(capsLockOn && document.activeElement === input);
    };

    const detectCapsLock = (event) => {
      if (typeof event?.getModifierState === "function") {
        capsLockOn = event.getModifierState("CapsLock");
      }
      syncWarning();
    };

    toggle.addEventListener("click", () => {
      input.type = input.type === "password" ? "text" : "password";
      syncToggle();
      input.focus({ preventScroll: true });
      syncWarning();
    });

    input.addEventListener("keydown", detectCapsLock);
    input.addEventListener("keyup", detectCapsLock);
    input.addEventListener("focus", syncWarning);
    input.addEventListener("blur", () => {
      capsLockOn = false;
      syncWarning();
    });

    syncToggle();
    syncWarning();
  }

  function setAdminTab(tabName) {
    st.activeTab = tabName || "dashboard";
    adminTabButtons().forEach((button) => {
      button.classList.toggle("active", button.dataset.adminTab === st.activeTab);
    });
    adminTabPanels().forEach((panel) => {
      const isActive = panel.dataset.adminPanel === st.activeTab;
      panel.hidden = !isActive;
      panel.classList.toggle("active", isActive);
    });
  }

  function applyAdminDrawerState(collapsed) {
    st.drawerCollapsed = Boolean(collapsed);
    el.adminDrawer?.classList.toggle("collapsed", st.drawerCollapsed);
    document.body.classList.toggle("admin-drawer-collapsed", st.drawerCollapsed);
    if (el.toggleAdminDrawer) {
      el.toggleAdminDrawer.textContent = st.drawerCollapsed ? "Expand" : "Collapse";
      el.toggleAdminDrawer.setAttribute("aria-expanded", String(!st.drawerCollapsed));
      el.toggleAdminDrawer.setAttribute(
        "aria-label",
        st.drawerCollapsed ? "Expand navigation drawer" : "Collapse navigation drawer",
      );
    }
    try {
      localStorage.setItem(DRAWER_STATE_KEY, st.drawerCollapsed ? "1" : "0");
    } catch {
      // Ignore local storage failures and continue with the default drawer state.
    }
  }

  function loadAdminDrawerState() {
    try {
      return localStorage.getItem(DRAWER_STATE_KEY) === "1";
    } catch {
      return false;
    }
  }

  function updateSelectedExamChip() {
    if (!el.selectedExamChip) return;
    const current = st.exams.find((item) => item.id === selectedExamId());
    el.selectedExamChip.textContent = current ? current.name : "No exam selected";
    if (el.dashboardOverview) {
      el.dashboardOverview.innerHTML = current
        ? `
          <div class="admin-mini-grid">
            <article class="box"><span class="small">Exam</span><strong>${esc(current.name)}</strong></article>
            <article class="box"><span class="small">Status</span><strong>${esc(current.status)}</strong></article>
            <article class="box"><span class="small">Results</span><strong>${current.results_published ? "Published" : "Draft / Private"}</strong></article>
          </div>
        `
        : '<p class="small">Select an exam to load live control, review, and result workflows.</p>';
    }
  }

  function readSession() {
    try {
      return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
    } catch {
      return null;
    }
  }

  function ensureSession() {
    const session = readSession();
    if (!session?.admin_id) {
      window.location.href = "/web?target=admin&reason=login_required";
      throw new Error("Admin login required");
    }
    st.adminId = session.admin_id;
    st.role = session.role || "superadmin";
    el.sessionAdmin.textContent = session.admin_id;
    if (el.adminAccountsPanel) {
      el.adminAccountsPanel.hidden = st.role !== "superadmin";
    }
  }

  function headers(extra = {}) {
    return {
      "x-admin": "true",
      "x-admin-id": st.adminId,
      ...extra,
    };
  }

  async function api(path, options = {}) {
    const req = {
      ...options,
      headers: headers(options.headers || {}),
    };
    if (req.body && typeof req.body !== "string" && !(req.body instanceof FormData)) {
      req.headers["Content-Type"] = "application/json";
      req.body = JSON.stringify(req.body);
    }
    const res = await fetch(path, req);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(
        explainApiError(payload.detail) ||
          explainApiError(payload.error) ||
          `HTTP ${res.status}`,
      );
    }
    return payload.data ?? payload;
  }

  async function download(path) {
    const res = await fetch(path, { headers: headers() });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(
        explainApiError(payload.detail) ||
          explainApiError(payload.error) ||
          `HTTP ${res.status}`,
      );
    }
    return res.text();
  }

  async function downloadBlob(path) {
    const res = await fetch(path, { headers: headers() });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(
        explainApiError(payload.detail) ||
          explainApiError(payload.error) ||
          `HTTP ${res.status}`,
      );
    }
    return {
      blob: await res.blob(),
      fileName:
        String(res.headers.get("content-disposition") || "")
          .match(/filename=\"?([^\";]+)\"?/)?.[1] || "download.bin",
    };
  }

  function triggerBlobDownload(blob, fileName) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName || "download.bin";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function openBlobPage(path) {
    const { blob } = await downloadBlob(path);
    const url = URL.createObjectURL(blob);
    const win = window.open(url, "_blank", "noopener");
    if (!win) {
      throw new Error("Preview popup blocked by browser.");
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    return win;
  }

  function selectedExamId() {
    return el.examSelect.value || st.selectedExamId || "";
  }

  function requireExam() {
    const examId = selectedExamId();
    if (!examId) throw new Error("Select an exam first.");
    return examId;
  }

  function prettyJson(value) {
    return JSON.stringify(value, null, 2);
  }

  function formatNumber(value, digits = 0) {
    const amount = Number(value || 0);
    return Number.isFinite(amount) ? amount.toFixed(digits) : "0";
  }

  function formatPercent(value) {
    return `${formatNumber(value, 1)}%`;
  }

  function compactId(value) {
    const text = String(value || "");
    return text.length > 12 ? `${text.slice(0, 8)}...` : text;
  }

  function percentWidth(value) {
    const amount = Number(value || 0);
    if (!Number.isFinite(amount)) return 0;
    return Math.max(0, Math.min(100, amount));
  }

  function performanceTone(value) {
    const amount = Number(value || 0);
    if (amount >= 70) return "good";
    if (amount >= 40) return "mid";
    return "risk";
  }

  function normalizeSearchText(value) {
    return String(value || "").trim().toLowerCase();
  }

  function getQuestionLookup() {
    return new Map(st.questions.map((question) => [question.id, question]));
  }

  function summarizeQuestionText(value) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!text) return "Question text unavailable";
    if (text.length <= 120) return text;
    return `${text.slice(0, 117)}...`;
  }

  function buildAnalyticsQuestionData(item, questionLookup) {
    const question = questionLookup.get(item.question_id);
    return {
      ...item,
      question_text:
        String(item.question_text || question?.text || "").trim() || "Question text unavailable",
      topic: item.topic || question?.topic || "",
      topic_tag: item.topic_tag || question?.topic_tag || question?.topic || "",
      difficulty: item.difficulty || question?.difficulty || "",
    };
  }

  function renderQuestionCell(item, { showQuestionIds = false } = {}) {
    const meta = [];
    if (showQuestionIds && item.question_id) {
      meta.push(`<span class="analytics-question-id mono">ID: ${esc(item.question_id)}</span>`);
    }
    if (item.topic_tag) {
      meta.push(`<span class="analytics-question-meta">${esc(item.topic_tag)}</span>`);
    }
    return `
      <div class="analytics-question-cell">
        <strong>${esc(summarizeQuestionText(item.question_text))}</strong>
        ${meta.length ? `<div class="analytics-question-meta-row">${meta.join("")}</div>` : ""}
      </div>
    `;
  }

  function questionMatchesSearch(item, query) {
    if (!query) return true;
    const haystack = [
      item.question_text,
      item.question_id,
      item.topic,
      item.topic_tag,
      item.difficulty,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  }

  function sortQuestionMetrics(rows, sortBy) {
    const list = [...rows];
    const compareText = (a, b) =>
      summarizeQuestionText(a.question_text).localeCompare(summarizeQuestionText(b.question_text));
    list.sort((left, right) => {
      switch (sortBy) {
        case "question_asc":
          return compareText(left, right);
        case "attempts_desc":
          return Number(right.total_attempts || 0) - Number(left.total_attempts || 0);
        case "attempts_asc":
          return Number(left.total_attempts || 0) - Number(right.total_attempts || 0);
        case "score_desc":
          return Number(right.average_score || 0) - Number(left.average_score || 0);
        case "score_asc":
          return Number(left.average_score || 0) - Number(right.average_score || 0);
        case "correct_asc":
          return Number(left.difficulty_index || 0) - Number(right.difficulty_index || 0);
        case "correct_desc":
        default:
          return Number(right.difficulty_index || 0) - Number(left.difficulty_index || 0);
      }
    });
    return list;
  }

  function filterQuestionMetrics(rows) {
    const query = normalizeSearchText(st.analyticsUi.questionSearch);
    const filter = st.analyticsUi.questionFilter || "all";
    const list = rows.filter((row) => {
      if (!questionMatchesSearch(row, query)) return false;
      if (filter === "all") return true;
      return performanceTone(row.difficulty_index) === filter;
    });
    return sortQuestionMetrics(list, st.analyticsUi.questionSort);
  }

  function getDifficultyFilterOptions(cells) {
    const values = Array.from(
      new Set(
        cells
          .map((cell) => String(cell.difficulty || "").trim())
          .filter(Boolean),
      ),
    ).sort((a, b) => a.localeCompare(b));
    return values;
  }

  function sortDifficultyCells(cells, sortBy) {
    const list = [...cells];
    const compareText = (a, b) =>
      summarizeQuestionText(a.question_text).localeCompare(summarizeQuestionText(b.question_text));
    list.sort((left, right) => {
      switch (sortBy) {
        case "question_asc":
          return compareText(left, right);
        case "topic_asc":
          return String(left.topic_tag || left.topic || "").localeCompare(
            String(right.topic_tag || right.topic || ""),
          );
        case "difficulty_index_desc":
          return Number(right.difficulty_index || 0) - Number(left.difficulty_index || 0);
        case "discrimination_desc":
          return Number(right.discrimination_index || 0) - Number(left.discrimination_index || 0);
        case "difficulty_index_asc":
        default:
          return Number(left.difficulty_index || 0) - Number(right.difficulty_index || 0);
      }
    });
    return list;
  }

  function filterDifficultyCells(cells) {
    const query = normalizeSearchText(st.analyticsUi.difficultySearch);
    const filter = st.analyticsUi.difficultyFilter || "all";
    const list = cells.filter((cell) => {
      if (!questionMatchesSearch(cell, query)) return false;
      if (filter === "all") return true;
      return String(cell.difficulty || "").trim().toLowerCase() === filter;
    });
    return sortDifficultyCells(list, st.analyticsUi.difficultySort);
  }

  function analyticsControlValue(control) {
    if (control.type === "checkbox") return control.checked;
    return control.value;
  }

  function renderAnalyticsToolbar(summary = {}) {
    return `
      <section class="analytics-toolbar analytics-toolbar-global">
        <div class="analytics-toolbar-info">
          <strong>Analytics Controls</strong>
          <span class="small">Search, sort, and filter question-based tables without losing the overall graph view.</span>
        </div>
        <label class="analytics-inline-check">
          <input type="checkbox" data-analytics-control="showQuestionIds" ${st.analyticsUi.showQuestionIds ? "checked" : ""}>
          Show Question IDs
        </label>
        <span class="analytics-summary-chip">Finalized Attempts: ${Number(summary.total_attempts || 0)}</span>
      </section>
    `;
  }

  function renderQuestionAnalyticsControls(totalRows, visibleRows) {
    return `
      <div class="analytics-filter-bar">
        <input
          type="search"
          value="${esc(st.analyticsUi.questionSearch)}"
          data-analytics-control="questionSearch"
          placeholder="Search by question, topic, difficulty, or ID"
        >
        <select data-analytics-control="questionFilter">
          <option value="all"${st.analyticsUi.questionFilter === "all" ? " selected" : ""}>All performance bands</option>
          <option value="good"${st.analyticsUi.questionFilter === "good" ? " selected" : ""}>Strong only</option>
          <option value="mid"${st.analyticsUi.questionFilter === "mid" ? " selected" : ""}>Medium only</option>
          <option value="risk"${st.analyticsUi.questionFilter === "risk" ? " selected" : ""}>Needs review only</option>
        </select>
        <select data-analytics-control="questionSort">
          <option value="correct_desc"${st.analyticsUi.questionSort === "correct_desc" ? " selected" : ""}>Sort: Highest correct rate</option>
          <option value="correct_asc"${st.analyticsUi.questionSort === "correct_asc" ? " selected" : ""}>Sort: Lowest correct rate</option>
          <option value="attempts_desc"${st.analyticsUi.questionSort === "attempts_desc" ? " selected" : ""}>Sort: Highest attempts</option>
          <option value="attempts_asc"${st.analyticsUi.questionSort === "attempts_asc" ? " selected" : ""}>Sort: Lowest attempts</option>
          <option value="score_desc"${st.analyticsUi.questionSort === "score_desc" ? " selected" : ""}>Sort: Highest avg score</option>
          <option value="score_asc"${st.analyticsUi.questionSort === "score_asc" ? " selected" : ""}>Sort: Lowest avg score</option>
          <option value="question_asc"${st.analyticsUi.questionSort === "question_asc" ? " selected" : ""}>Sort: Question A-Z</option>
        </select>
        <span class="analytics-results-chip">Showing ${visibleRows} of ${totalRows}</span>
      </div>
    `;
  }

  function renderDifficultyAnalyticsControls(totalRows, visibleRows, difficultyOptions) {
    return `
      <div class="analytics-filter-bar">
        <input
          type="search"
          value="${esc(st.analyticsUi.difficultySearch)}"
          data-analytics-control="difficultySearch"
          placeholder="Search by question, topic, difficulty, or ID"
        >
        <select data-analytics-control="difficultyFilter">
          <option value="all"${st.analyticsUi.difficultyFilter === "all" ? " selected" : ""}>All difficulty levels</option>
          ${difficultyOptions
            .map(
              (value) =>
                `<option value="${esc(value.toLowerCase())}"${st.analyticsUi.difficultyFilter === value.toLowerCase() ? " selected" : ""}>${esc(value)}</option>`,
            )
            .join("")}
        </select>
        <select data-analytics-control="difficultySort">
          <option value="difficulty_index_asc"${st.analyticsUi.difficultySort === "difficulty_index_asc" ? " selected" : ""}>Sort: Lowest difficulty index</option>
          <option value="difficulty_index_desc"${st.analyticsUi.difficultySort === "difficulty_index_desc" ? " selected" : ""}>Sort: Highest difficulty index</option>
          <option value="discrimination_desc"${st.analyticsUi.difficultySort === "discrimination_desc" ? " selected" : ""}>Sort: Highest discrimination</option>
          <option value="topic_asc"${st.analyticsUi.difficultySort === "topic_asc" ? " selected" : ""}>Sort: Topic A-Z</option>
          <option value="question_asc"${st.analyticsUi.difficultySort === "question_asc" ? " selected" : ""}>Sort: Question A-Z</option>
        </select>
        <span class="analytics-results-chip">Showing ${visibleRows} of ${totalRows}</span>
      </div>
    `;
  }

  function renderDistribution(buckets, totalAttempts) {
    if (!buckets.length) {
      return '<p class="small">Score distribution abhi available nahi hai.</p>';
    }
    const maxCount = Math.max(...buckets.map((item) => Number(item.count || 0)), 1);
    return buckets
      .map((bucket) => {
        const count = Number(bucket.count || 0);
        const width = maxCount > 0 ? (count / maxCount) * 100 : 0;
        return `
          <div class="dist-row">
            <span>${esc(bucket.label)}</span>
            <div class="dist-bar"><div style="width:${width}%"></div></div>
            <span>${count}</span>
          </div>
        `;
      })
      .join("");
  }

  function renderTopicCards(cells) {
    if (!cells.length) {
      return '<p class="small">Topic heatmap tab populate hoga jab attempts complete honge.</p>';
    }
    return `
      <div class="analytics-card-grid">
        ${cells
          .map(
            (cell) => `
              <article class="analytics-mini-card tone-${performanceTone(cell.performance_index)}">
                <p class="analytics-mini-label">${esc(cell.topic_tag || "Topic")}</p>
                <strong>${formatPercent(cell.performance_index)}</strong>
                <span>${Number(cell.question_count || 0)} question(s)</span>
                <span>${Number(cell.total_attempts || 0)} attempt touchpoints</span>
                <span>Avg score ${formatNumber(cell.average_score, 2)}</span>
              </article>
            `,
          )
          .join("")}
      </div>
    `;
  }

  function renderQuestionMetrics(rows, totalRows = rows.length) {
    if (!totalRows) {
      return '<p class="small">Per-question metrics abhi ready nahi hain.</p>';
    }
    if (!rows.length) {
      return '<p class="small">No questions match the current search or filter.</p>';
    }
    return `
      ${renderQuestionAnalyticsControls(totalRows, rows.length)}
      <div class="table-wrap analytics-table-wrap">
        <table class="analytics-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Attempts</th>
              <th>Correct Rate</th>
              <th>Avg Score</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (row) => `
                  <tr>
                    <td>${renderQuestionCell(row, { showQuestionIds: st.analyticsUi.showQuestionIds })}</td>
                    <td>${Number(row.total_attempts || 0)}</td>
                    <td>
                      <div class="analytics-meter">
                        <div class="analytics-meter-fill tone-${performanceTone(row.difficulty_index)}" style="width:${percentWidth(row.difficulty_index)}%"></div>
                      </div>
                      <span class="analytics-meter-label">${formatPercent(row.difficulty_index)}</span>
                    </td>
                    <td>${formatNumber(row.average_score, 2)}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderDifficultyHeatmap(cells, totalRows = cells.length, difficultyOptions = []) {
    if (!totalRows) {
      return '<p class="small">Difficulty heatmap abhi empty hai.</p>';
    }
    if (!cells.length) {
      return '<p class="small">No questions match the current search or filter.</p>';
    }
    return `
      ${renderDifficultyAnalyticsControls(totalRows, cells.length, difficultyOptions)}
      <div class="table-wrap analytics-table-wrap">
        <table class="analytics-table">
          <thead>
            <tr>
              <th>Question</th>
              <th>Topic</th>
              <th>Difficulty</th>
              <th>Difficulty Index</th>
              <th>Discrimination</th>
            </tr>
          </thead>
          <tbody>
            ${cells
              .map(
                (cell) => `
                  <tr>
                    <td>${renderQuestionCell(cell, { showQuestionIds: st.analyticsUi.showQuestionIds })}</td>
                    <td>${esc(cell.topic_tag || cell.topic || "-")}</td>
                    <td>${esc(cell.difficulty || "-")}</td>
                    <td>
                      <span class="analytics-pill tone-${performanceTone(cell.difficulty_index)}">${formatPercent(cell.difficulty_index)}</span>
                    </td>
                    <td>${cell.discrimination_index == null ? "-" : formatNumber(cell.discrimination_index, 2)}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderAnalyticsDashboard(summaryData, difficultyData, topicData, distributionData) {
    const summary = summaryData.summary || {};
    const questionMetrics = summaryData.question_metrics || [];
    const topicCells = topicData.cells || [];
    const difficultyCells = difficultyData.cells || [];
    const buckets = distributionData.buckets || [];
    const totalAttempts = Number(summary.total_attempts ?? distributionData.total_attempts ?? 0);
    const filteredQuestionMetrics = filterQuestionMetrics(questionMetrics);
    const filteredDifficultyCells = filterDifficultyCells(difficultyCells);
    const difficultyOptions = getDifficultyFilterOptions(difficultyCells);

    return `
      ${renderAnalyticsToolbar(summary)}
      <section class="analytics-grid">
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Total Attempts</p>
          <strong>${totalAttempts}</strong>
          <span>Completed attempts in this exam</span>
        </article>
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Mean Score</p>
          <strong>${formatNumber(summary.mean_score, 2)}</strong>
          <span>Average marks scored by cadets</span>
        </article>
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Pass Rate</p>
          <strong>${formatPercent(summary.pass_rate)}</strong>
          <span>Pass percentage across finalized results</span>
        </article>
      </section>
      <section class="analytics-stack">
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Score Distribution</h3>
              <p class="small">Score bands shown as a histogram-style bar chart.</p>
            </div>
          </div>
          <div class="analytics-distribution">
            ${renderDistribution(buckets, totalAttempts)}
          </div>
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Topic Performance</h3>
              <p class="small">Weak and strong topics in a quick visual card layout.</p>
            </div>
          </div>
          ${renderTopicCards(topicCells)}
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Question Performance</h3>
              <p class="small">Question text primary view me hai. Search, sort, ya performance band se list narrow karo.</p>
            </div>
          </div>
          ${renderQuestionMetrics(filteredQuestionMetrics, questionMetrics.length)}
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Difficulty Heatmap</h3>
              <p class="small">Readable question text ke saath difficulty, topic, aur discrimination ko compare karo.</p>
            </div>
          </div>
          ${renderDifficultyHeatmap(filteredDifficultyCells, difficultyCells.length, difficultyOptions)}
        </article>
      </section>
    `;
  }

  function metricRows(metrics, name) {
    return Array.isArray(metrics?.[name]) ? metrics[name] : [];
  }

  function sumMetricCounts(rows) {
    return rows.reduce((total, row) => total + Number(row.count || 0), 0);
  }

  function sumMetricValue(rows, field = "total_value") {
    return rows.reduce((total, row) => total + Number(row[field] || 0), 0);
  }

  function averageMetricValue(rows) {
    const count = sumMetricCounts(rows);
    return count ? sumMetricValue(rows) / count : 0;
  }

  function maxMetricValue(rows) {
    return rows.reduce((max, row) => Math.max(max, Number(row.max_value || 0)), 0);
  }

  function latestMetricUpdate(...groups) {
    const timestamps = groups
      .flat()
      .map((row) => {
        const stamp = Date.parse(row.updated_at || "");
        return Number.isNaN(stamp) ? null : stamp;
      })
      .filter((value) => value != null);
    if (!timestamps.length) return "No telemetry yet";
    return new Date(Math.max(...timestamps)).toLocaleString();
  }

  function msTone(value, warn = 400, risk = 1200) {
    const amount = Number(value || 0);
    if (amount >= risk) return "risk";
    if (amount >= warn) return "mid";
    return "good";
  }

  function countTone(value, warn = 1, risk = 5) {
    const amount = Number(value || 0);
    if (amount >= risk) return "risk";
    if (amount >= warn) return "mid";
    return "good";
  }

  function renderMetricsEndpointTable(rows) {
    if (!rows.length) {
      return '<p class="small">Request timing data abhi collect nahi hui hai.</p>';
    }
    return `
      <div class="table-wrap analytics-table-wrap">
        <table class="analytics-table">
          <thead>
            <tr>
              <th>Endpoint</th>
              <th>Samples</th>
              <th>Average</th>
              <th>Peak</th>
              <th>Health</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map((row) => {
                const averageMs = Number(row.average_ms || 0);
                const tone = msTone(averageMs);
                return `
                  <tr>
                    <td><span class="mono">${esc(row.key || "endpoint")}</span></td>
                    <td>${Number(row.count || 0)}</td>
                    <td>${formatNumber(averageMs, 1)} ms</td>
                    <td>${formatNumber(row.max_value, 1)} ms</td>
                    <td><span class="analytics-pill tone-${tone}">${tone === "good" ? "Stable" : tone === "mid" ? "Watch" : "Slow"}</span></td>
                  </tr>
                `;
              })
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderMetricsDashboard(metrics) {
    const requestRows = metricRows(metrics, "request_duration_ms")
      .map((row) => ({
        ...row,
        average_ms: Number(row.count || 0) ? Number(row.total_value || 0) / Number(row.count || 1) : 0,
      }))
      .sort((left, right) => Number(right.average_ms || 0) - Number(left.average_ms || 0));
    const gradingRows = metricRows(metrics, "finalize_to_grade_ms");
    const conflictRows = metricRows(metrics, "concurrency_conflict_count");
    const autoExpireRows = metricRows(metrics, "auto_expire_count");
    const alertRaisedRows = metricRows(metrics, "proctor_alert_raised_count");
    const alertAckRows = metricRows(metrics, "proctor_alert_acknowledged_count");
    const alertResolvedRows = metricRows(metrics, "proctor_alert_resolved_count");
    const alertAutoResolvedRows = metricRows(metrics, "proctor_alert_auto_resolved_count");
    const alertAckMsRows = metricRows(metrics, "proctor_alert_ack_ms");
    const alertResolutionMsRows = metricRows(metrics, "proctor_alert_resolution_ms");

    const requestSampleCount = sumMetricCounts(requestRows);
    const avgRequestMs = averageMetricValue(requestRows);
    const avgGradingMs = averageMetricValue(gradingRows);
    const conflictCount = sumMetricCounts(conflictRows);
    const autoExpireCount = sumMetricCounts(autoExpireRows);
    const alertRaisedCount = sumMetricCounts(alertRaisedRows);
    const latestUpdate = latestMetricUpdate(
      requestRows,
      gradingRows,
      conflictRows,
      autoExpireRows,
      alertRaisedRows,
      alertAckRows,
      alertResolvedRows,
      alertAutoResolvedRows,
      alertAckMsRows,
      alertResolutionMsRows,
    );

    return `
      <section class="analytics-toolbar">
        <div class="analytics-toolbar-info">
          <strong>Operational Health Overview</strong>
          <span>Metrics ko readable cards aur tables me convert kiya gaya hai, taaki raw JSON ke bina bhi system health samajh aaye.</span>
        </div>
        <div class="analytics-inline-check">
          <span class="analytics-pill tone-${countTone(conflictCount + autoExpireCount, 1, 4)}">Last update: ${esc(latestUpdate)}</span>
        </div>
      </section>
      <section class="analytics-grid">
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Request Samples</p>
          <strong>${requestSampleCount}</strong>
          <span>Tracked API timing samples</span>
        </article>
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Average Response</p>
          <strong>${formatNumber(avgRequestMs, 1)} ms</strong>
          <span>Across recorded admin and student API traffic</span>
        </article>
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Average Grading Delay</p>
          <strong>${formatNumber(avgGradingMs, 1)} ms</strong>
          <span>Submit-to-grade pipeline performance</span>
        </article>
      </section>
      <section class="analytics-stack">
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Endpoint Response Time</h3>
              <p class="small">Ye table batati hai kaunse routes stable hain aur kaunse routes slow ho rahe hain.</p>
            </div>
          </div>
          ${renderMetricsEndpointTable(requestRows)}
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Processing and Reliability</h3>
              <p class="small">Exam engine ke operational counters ko quick cards me dekho.</p>
            </div>
          </div>
          <div class="analytics-card-grid">
            <article class="analytics-mini-card tone-${msTone(avgGradingMs, 600, 1800)}">
              <p class="analytics-mini-label">Grading Average</p>
              <strong>${formatNumber(avgGradingMs, 1)} ms</strong>
              <span>Average submit-to-grade delay</span>
              <span>Peak ${formatNumber(maxMetricValue(gradingRows), 1)} ms</span>
            </article>
            <article class="analytics-mini-card tone-${countTone(conflictCount, 1, 3)}">
              <p class="analytics-mini-label">Concurrency Conflicts</p>
              <strong>${conflictCount}</strong>
              <span>Concurrent write conflicts detected</span>
              <span>Lower is better</span>
            </article>
            <article class="analytics-mini-card tone-${countTone(autoExpireCount, 2, 8)}">
              <p class="analytics-mini-label">Auto Expire Events</p>
              <strong>${autoExpireCount}</strong>
              <span>Attempts auto-submitted after expiry</span>
              <span>Review if unexpected</span>
            </article>
          </div>
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Proctor Alert Lifecycle</h3>
              <p class="small">Raised, acknowledged, aur resolved alert flow ko ek nazar me dekho.</p>
            </div>
          </div>
          <div class="analytics-card-grid">
            <article class="analytics-mini-card tone-${countTone(alertRaisedCount, 1, 5)}">
              <p class="analytics-mini-label">Alerts Raised</p>
              <strong>${alertRaisedCount}</strong>
              <span>Integrity or proctor alerts triggered</span>
            </article>
            <article class="analytics-mini-card tone-${countTone(sumMetricCounts(alertAckRows), 2, 8)}">
              <p class="analytics-mini-label">Acknowledged</p>
              <strong>${sumMetricCounts(alertAckRows)}</strong>
              <span>Alerts acknowledged by operators</span>
              <span>Avg ack ${formatNumber(averageMetricValue(alertAckMsRows), 1)} ms</span>
            </article>
            <article class="analytics-mini-card tone-${countTone(sumMetricCounts(alertResolvedRows), 2, 8)}">
              <p class="analytics-mini-label">Resolved</p>
              <strong>${sumMetricCounts(alertResolvedRows)}</strong>
              <span>Alerts resolved manually</span>
              <span>Avg resolve ${formatNumber(averageMetricValue(alertResolutionMsRows), 1)} ms</span>
            </article>
            <article class="analytics-mini-card tone-${countTone(sumMetricCounts(alertAutoResolvedRows), 3, 10)}">
              <p class="analytics-mini-label">Auto Resolved</p>
              <strong>${sumMetricCounts(alertAutoResolvedRows)}</strong>
              <span>Alerts cleared by automatic recovery</span>
            </article>
          </div>
        </article>
      </section>
    `;
  }

  function renderExamSummary(resultsData, analyticsData) {
    const summary = analyticsData.summaryData.summary || {};
    const topicCells = [...(analyticsData.topicData.cells || [])];
    const buckets = analyticsData.distributionData.buckets || [];
    const strongestTopics = [...topicCells]
      .sort((left, right) => Number(right.performance_index || 0) - Number(left.performance_index || 0))
      .slice(0, 3);
    const weakTopics = [...topicCells]
      .sort((left, right) => Number(left.performance_index || 0) - Number(right.performance_index || 0))
      .slice(0, 3);
    const totalCadets = Number(resultsData.candidates?.length || summary.total_attempts || 0);
    const pendingReview = Number(resultsData.pending_review_count || 0);
    const readyResults = Number(resultsData.ready_result_count || 0);
    const published = Boolean(resultsData.results_published);
    const publishedLabel = published ? "Published" : pendingReview > 0 ? "Waiting for review" : "Ready to publish";
    const publishedTone = published ? "good" : pendingReview > 0 ? "risk" : "mid";

    return `
      <section class="analytics-toolbar">
        <div class="analytics-toolbar-info">
          <strong>Exam Summary Snapshot</strong>
          <span>High-level graphical summary for quick reporting and publication decisions.</span>
        </div>
        <div class="analytics-inline-check">
          <span class="analytics-pill tone-${publishedTone}">${publishedLabel}</span>
        </div>
      </section>
      <section class="analytics-grid">
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Cadets Processed</p>
          <strong>${totalCadets}</strong>
          <span>Total attempts visible in result review</span>
        </article>
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Results Ready</p>
          <strong>${readyResults}</strong>
          <span>Final results ready for publish/export</span>
        </article>
        <article class="analytics-kpi">
          <p class="analytics-kpi-label">Pending Review</p>
          <strong>${pendingReview}</strong>
          <span>FIB or subjective answers still awaiting examiner action</span>
        </article>
      </section>
      <section class="analytics-stack">
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Score Distribution</h3>
              <p class="small">Score bands show overall performance spread across finalized attempts.</p>
            </div>
          </div>
          <div class="analytics-distribution">
            ${renderDistribution(buckets, Number(summary.total_attempts || totalCadets))}
          </div>
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Publication Readiness</h3>
              <p class="small">Use these signals before publishing or exporting final results.</p>
            </div>
          </div>
          <div class="analytics-card-grid">
            <article class="analytics-mini-card tone-${published ? "good" : "mid"}">
              <p class="analytics-mini-label">Publish State</p>
              <strong>${published ? "Live" : "Private"}</strong>
              <span>${published ? "Cadet result documents can now be exported." : "Results are still admin-controlled."}</span>
            </article>
            <article class="analytics-mini-card tone-${pendingReview > 0 ? "risk" : "good"}">
              <p class="analytics-mini-label">Review Gate</p>
              <strong>${pendingReview > 0 ? "Blocked" : "Clear"}</strong>
              <span>${pendingReview > 0 ? "Pending reviews should be resolved first." : "No pending review blockers detected."}</span>
            </article>
            <article class="analytics-mini-card tone-${performanceTone(summary.pass_rate)}">
              <p class="analytics-mini-label">Pass Rate</p>
              <strong>${formatPercent(summary.pass_rate)}</strong>
              <span>Average performance trend for this exam</span>
            </article>
          </div>
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Strongest Topics</h3>
              <p class="small">Top-performing areas based on topic heatmap data.</p>
            </div>
          </div>
          ${renderTopicCards(strongestTopics)}
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Needs Attention</h3>
              <p class="small">Lower-performing topics that may need revision planning.</p>
            </div>
          </div>
          ${renderTopicCards(weakTopics)}
        </article>
      </section>
    `;
  }

  async function ensureAnalyticsQuestionCache() {
    if (st.questions.length) return;
    try {
      st.questions = await api("/admin/questions");
    } catch {
      st.questions = [];
    }
  }

  function prepareAnalyticsPayload(summaryData, difficultyData, topicData, distributionData) {
    const questionLookup = getQuestionLookup();
    return {
      summaryData: {
        ...summaryData,
        question_metrics: (summaryData.question_metrics || []).map((item) =>
          buildAnalyticsQuestionData(item, questionLookup),
        ),
      },
      difficultyData: {
        ...difficultyData,
        cells: (difficultyData.cells || []).map((item) =>
          buildAnalyticsQuestionData(item, questionLookup),
        ),
      },
      topicData,
      distributionData,
    };
  }

  function renderAnalyticsDashboardFromState(focusState = null) {
    if (!st.analyticsData || !el.analyticsBox) return;
    el.analyticsBox.innerHTML = renderAnalyticsDashboard(
      st.analyticsData.summaryData,
      st.analyticsData.difficultyData,
      st.analyticsData.topicData,
      st.analyticsData.distributionData,
    );
    if (!focusState?.control) return;
    const target = el.analyticsBox.querySelector(
      `[data-analytics-control="${focusState.control}"]`,
    );
    if (!target) return;
    target.focus({ preventScroll: true });
    if (
      typeof focusState.cursor === "number" &&
      typeof target.setSelectionRange === "function"
    ) {
      target.setSelectionRange(focusState.cursor, focusState.cursor);
    }
  }

  function handleAnalyticsControlEvent(event) {
    const control = event.target.closest("[data-analytics-control]");
    if (!control || !st.analyticsData) return;
    const controlName = control.dataset.analyticsControl;
    if (!controlName) return;
    const focusState = {
      control: controlName,
      cursor:
        typeof control.selectionStart === "number" ? control.selectionStart : null,
    };
    st.analyticsUi[controlName] = analyticsControlValue(control);
    renderAnalyticsDashboardFromState(focusState);
  }

  function updateExamSelections(exams, preferredId = "") {
    st.exams = exams;
    const selected = preferredId || selectedExamId();
    const examOptions = ['<option value="">Select exam...</option>']
      .concat(
        exams.map(
          (exam) =>
            `<option value="${esc(exam.id)}">${esc(exam.name)} (${esc(exam.status)})</option>`,
        ),
      )
      .join("");
    const referenceOptions = ['<option value="">Reference exam (optional)</option>']
      .concat(
        exams.map(
          (exam) => `<option value="${esc(exam.id)}">${esc(exam.name)}</option>`,
        ),
      )
      .join("");
    el.examSelect.innerHTML = examOptions;
    el.referenceExamSelect.innerHTML = referenceOptions;
    if (selected && exams.some((exam) => exam.id === selected)) {
      el.examSelect.value = selected;
      const currentExam = exams.find((exam) => exam.id === selected);
      el.referenceExamSelect.value = currentExam?.reference_exam_id || "";
      el.customRulesText.value = (currentExam?.custom_rules || []).join("\n");
      st.selectedExamId = selected;
    } else if (el.customRulesText) {
      el.customRulesText.value = "";
      st.selectedExamId = "";
    }
    updateSelectedExamChip();
  }

  async function loadVersion() {
    try {
      const version = await fetch("/system/version");
      const payload = await version.json();
      el.version.textContent = payload.data?.version || payload.version || "n/a";
    } catch {
      el.version.textContent = "offline";
    }
  }

  async function loadExams(preferredId = "") {
    const exams = await api("/admin/exams");
    updateExamSelections(exams, preferredId);
    setStatus(exams.length ? "Exams loaded." : "No exams found yet.");
  }

  async function createExam() {
    const name = (el.newExamName.value || "").trim();
    const duration_minutes = Number(el.newExamDuration.value || 0);
    const negative_marking = Number(el.newExamNegativeMarking.value || 0);
    if (!name) throw new Error("Exam name is required.");
    const exam = await api("/admin/exams", {
      method: "POST",
      body: { name, duration_minutes, negative_marking },
    });
    el.newExamName.value = "";
    await loadExams(exam.id);
    setStatus(`Exam '${exam.name}' created.`);
  }

  async function saveReferenceExam() {
    const examId = requireExam();
    const referenceExamId = el.referenceExamSelect.value || null;
    await api(`/admin/exams/${examId}/reference-exam`, {
      method: "PATCH",
      body: { reference_exam_id: referenceExamId },
    });
    await loadExams(examId);
    setStatus("Reference exam updated.");
  }

  async function saveCustomRules() {
    const examId = requireExam();
    const custom_rules = parseLines(el.customRulesText.value);
    const data = await api(`/admin/exams/${examId}/rules`, {
      method: "PATCH",
      body: { custom_rules },
    });
    await loadExams(examId);
    el.customRulesText.value = (data.custom_rules || []).join("\n");
    setStatus("Custom exam rules updated.");
  }

  async function publishExam() {
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/publish`, { method: "POST" });
    await loadExams(examId);
    setStatus(`Exam '${data.name}' is now active.`);
  }

  async function closeExam() {
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/close`, { method: "POST" });
    await loadExams(examId);
    setStatus(`Exam '${data.name}' closed.`);
  }

  async function deleteExam() {
    const examId = requireExam();
    const label = el.examSelect.options[el.examSelect.selectedIndex]?.textContent || examId;
    if (
      !window.confirm(
        `Delete '${label}'? Active exams or exams with attempts cannot be removed.`,
      )
    ) {
      return;
    }
    const data = await api(`/admin/exams/${examId}`, { method: "DELETE" });
    await loadExams();
    setStatus(`Deleted exam '${data.exam_id}'.`);
  }

  function renderPreview(question) {
    const type = question.question_type || "mcq_single";
    const options = (question.options || [])
      .map(
        (opt) =>
          `<li>${esc(opt.option_text)}${opt.is_correct ? " <strong>(correct)</strong>" : ""}</li>`,
      )
      .join("");
    const accepted = (question.accepted_answers || [])
      .map((item) => `<li>${esc(item.answer_text)}</li>`)
      .join("");
    const wordPolicy = [question.word_target_min, question.word_target_max, question.word_hard_max].some(
      (value) => value != null,
    )
      ? `<p><strong>Word policy:</strong> ${question.word_target_min ?? "-"} to ${question.word_target_max ?? "-"}, hard max ${question.word_hard_max ?? "-"}</p>`
      : "";
    if (type === "fib_text") {
      return `<div><p><strong>Fill in the blank:</strong> ${esc(question.text)}</p><input class="army-text-input" type="text" placeholder="Cadet types the missing word here" disabled>${accepted ? `<p><strong>Accepted answers</strong></p><ul>${accepted}</ul>` : ""}</div>`;
    }
    if (type === "short_answer" || type === "long_answer") {
      return `<div><p><strong>${type === "short_answer" ? "Short answer" : "Long answer"}:</strong> ${esc(question.text)}</p>${wordPolicy}<textarea class="army-textarea" rows="${type === "long_answer" ? 8 : 4}" placeholder="Cadet writes the answer here" disabled></textarea></div>`;
    }
    return `<div><p><strong>${type === "true_false" ? "True / False" : "MCQ"}:</strong> ${esc(question.text)}</p><ul>${options}</ul></div>`;
  }

  function renderQuestions(questions) {
    st.questions = questions;
    el.questionsBody.innerHTML = "";
    if (!questions.length) {
      el.questionsBody.innerHTML = '<tr><td colspan="7">No questions found.</td></tr>';
      return;
    }
    questions.forEach((question) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${esc(question.id)}</td>
        <td>${esc(question.question_type)}</td>
        <td>${esc(question.topic)}</td>
        <td>${esc(question.marks)}</td>
        <td>${esc(question.text)}</td>
        <td><button type="button" data-action="preview" data-question-id="${esc(question.id)}">Preview</button></td>
        <td><button type="button" data-action="attach" data-question-id="${esc(question.id)}">Add to Selected Exam</button></td>
      `;
      el.questionsBody.appendChild(tr);
    });
  }

  function parseLines(text) {
    return String(text || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function parseQuestionPayload() {
    const question_type = el.questionType.value;
    const text = (el.questionText.value || "").trim();
    const topic = (el.questionTopic.value || "").trim();
    const difficulty = (el.questionDifficulty.value || "").trim();
    const marks = Number(el.questionMarks.value || 0);
    const rawLines = parseLines(el.questionOptions.value);
    const payload = { text, topic, difficulty, marks, question_type };

    if (!text || !topic || !difficulty || !marks) {
      throw new Error("Question text, topic, difficulty, and marks are required.");
    }

    if (question_type === "mcq_single") {
      payload.options = rawLines.map((line) => {
        const [option_text, flag] = line.split("::").map((part) => part.trim());
        return { option_text, is_correct: String(flag || "").toLowerCase() === "true" };
      });
    } else if (question_type === "true_false") {
      const correct = (rawLines[0] || "true").toLowerCase();
      payload.options = [{ option_text: correct, is_correct: true }];
    } else if (question_type === "fib_text") {
      payload.accepted_answers = rawLines;
    } else {
      payload.word_target_min = Number(el.wordTargetMin.value || 0) || null;
      payload.word_target_max = Number(el.wordTargetMax.value || 0) || null;
      payload.word_hard_max = Number(el.wordHardMax.value || 0) || null;
    }
    return payload;
  }

  async function createQuestion() {
    const payload = parseQuestionPayload();
    const data = await api("/admin/questions", { method: "POST", body: payload });
    el.questionCreateResult.textContent = prettyJson(data);
    el.questionText.value = "";
    el.questionOptions.value = "";
    el.wordTargetMin.value = "";
    el.wordTargetMax.value = "";
    el.wordHardMax.value = "";
    await loadQuestions();
    setStatus("Question created.");
  }

  async function loadQuestions() {
    const questions = await api("/admin/questions");
    renderQuestions(questions);
    setStatus(questions.length ? `Loaded ${questions.length} questions.` : "No questions found.");
  }

  async function attachQuestionToExam(questionId) {
    const examId = requireExam();
    await api(`/admin/exams/${examId}/add-questions`, {
      method: "POST",
      body: { question_ids: [questionId] },
    });
    setStatus(`Question linked to exam '${examId}'.`);
  }

  async function uploadCsv(fileInput, path, target) {
    const file = fileInput.files?.[0];
    if (!file) throw new Error("Select a CSV file first.");
    const form = new FormData();
    form.append("file", file);
    const data = await api(path, { method: "POST", body: form, headers: {} });
    target.textContent = prettyJson(data);
    return data;
  }

  function renderActiveAttempts(rows) {
    el.activeBody.innerHTML = "";
    if (!rows.length) {
      el.activeBody.innerHTML = '<tr><td colspan="5">No active attempts.</td></tr>';
      return;
    }
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${esc(row.attempt_id)}</td>
        <td>${esc(row.student_id)}</td>
        <td>${esc(row.answered_question_count)}</td>
        <td>${esc(row.total_question_count)}</td>
        <td>${esc(row.expires_at)}</td>
      `;
      el.activeBody.appendChild(tr);
    });
  }

  async function refreshLiveStatus() {
    const examId = requireExam();
    const [liveStatus, activeAttempts] = await Promise.all([
      api(`/admin/exams/${examId}/live-status`),
      api(`/admin/exams/${examId}/active-attempts`),
    ]);
    el.liveSummary.textContent = prettyJson(liveStatus);
    renderActiveAttempts(activeAttempts);
    setStatus("Live status refreshed.");
  }

  async function applyExamControl(action) {
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/${action}`, {
      method: "POST",
      body: {
        reason: (el.examControlReason.value || "").trim() || null,
        freeze_timer: action === "pause" ? Boolean(el.freezeTimerToggle.checked) : false,
      },
    });
    el.forceSubmitResult.textContent = prettyJson(data);
    await refreshLiveStatus();
    setStatus(`${action} applied.`);
  }

  async function forceSubmitAttempt() {
    const attemptId = (el.forceAttemptId.value || "").trim();
    if (!attemptId) throw new Error("Attempt ID is required.");
    const data = await api(`/admin/attempts/${attemptId}/force-submit`, {
      method: "POST",
      body: { reason: (el.examControlReason.value || "").trim() || null },
    });
    el.forceSubmitResult.textContent = prettyJson(data);
    setStatus("Attempt force-submitted.");
    if (selectedExamId()) await refreshLiveStatus();
  }

  async function forceSubmitExpired() {
    const examId = selectedExamId();
    const suffix = examId ? `?exam_id=${encodeURIComponent(examId)}` : "";
    const data = await api(`/admin/attempts/force-submit-expired${suffix}`, { method: "POST" });
    el.forceSubmitResult.textContent = prettyJson(data);
    setStatus("Expired attempts force-submit executed.");
    if (examId) await refreshLiveStatus();
  }

  async function sendBroadcast() {
    const examId = requireExam();
    const message = (el.broadcastMessage.value || "").trim();
    if (!message) throw new Error("Broadcast message is required.");
    const data = await api(`/admin/exams/${examId}/broadcast`, {
      method: "POST",
      body: {
        message,
        severity: el.broadcastSeverity.value || "info",
      },
    });
    el.broadcastResult.textContent = prettyJson(data);
    el.broadcastMessage.value = "";
    setStatus("Broadcast sent.");
  }

  async function loadStudents() {
    const data = await api("/admin/students");
    const students = data.students || [];
    el.studentsBody.innerHTML = students.length
      ? students
          .map(
            (item) =>
              `<tr><td>${esc(item.student_id)}</td><td>${esc(item.display_name || "")}</td><td>${esc(item.status || "ACTIVE")}</td><td>${esc(item.created_at || "")}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="4">No student accounts found.</td></tr>';
  }

  async function createStudent() {
    const student_id = (el.studentIdInput.value || "").trim();
    if (!student_id) throw new Error("Student ID is required.");
    const display_name = (el.studentNameInput.value || "").trim() || null;
    const password = (el.studentPasswordInput.value || "").trim() || null;
    const data = await api("/admin/students/register", {
      method: "POST",
      body: { student_id, display_name, password },
    });
    el.studentIdResult.textContent = prettyJson(data);
    el.studentIdInput.value = "";
    el.studentNameInput.value = "";
    el.studentPasswordInput.value = "";
    await loadStudents();
    setStatus("Student account created.");
  }

  async function generateStudents() {
    const prefix = (el.studentPrefix.value || "cadet").trim();
    const count = Number(el.studentCount.value || 0);
    const data = await api("/admin/students/generate", {
      method: "POST",
      body: { prefix, count },
    });
    el.studentIdResult.textContent = prettyJson(data);
    await loadStudents();
    setStatus("Student IDs generated.");
  }

  async function importStudents() {
    const data = await uploadCsv(
      el.studentCsvFile,
      "/admin/students/import-csv",
      el.studentCsvResult,
    );
    await loadStudents();
    setStatus(`Imported student CSV. Inserted: ${data.inserted}`);
  }

  async function exportStudents() {
    const csv = await download("/admin/students/export-csv");
    el.studentCsvResult.textContent = csv;
    setStatus("Student CSV exported to preview box.");
  }

  async function loadAdminAccounts() {
    if (st.role !== "superadmin") return;
    const accounts = await api("/admin/accounts");
    el.adminAccountsBody.innerHTML = accounts.length
      ? accounts
          .map(
            (item) =>
              `<tr><td>${esc(item.admin_id)}</td><td>${esc(item.display_name || "")}</td><td>${esc(item.role)}</td><td>${esc(item.status)}</td><td>${esc(item.created_by || "")}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="5">No admin accounts found.</td></tr>';
  }

  async function createAdminAccount() {
    if (st.role !== "superadmin") throw new Error("Only superadmin can create admin accounts.");
    const admin_id = (el.newAdminId.value || "").trim();
    const display_name = (el.newAdminName.value || "").trim() || null;
    const role = el.newAdminRole.value || "examiner";
    const access_key = (el.newAdminKey.value || "").trim();
    const data = await api("/admin/accounts", {
      method: "POST",
      body: { admin_id, display_name, role, access_key },
    });
    el.adminAccountResult.textContent = prettyJson(data);
    el.newAdminId.value = "";
    el.newAdminName.value = "";
    el.newAdminKey.value = "";
    await loadAdminAccounts();
    setStatus(`Admin account '${data.admin_id}' created.`);
  }

  function renderFibQueue(items) {
    el.fibReviewBody.innerHTML = "";
    if (!items.length) {
      el.fibReviewBody.innerHTML = '<tr><td colspan="7">No FIB reviews pending.</td></tr>';
      return;
    }
    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${esc(item.question_text)}</td>
        <td>${esc(item.normalized_text_answer)}</td>
        <td>${esc(item.sample_answer)}</td>
        <td>${esc(item.submission_count)}</td>
        <td>
          <select data-role="fib-decision">
            <option value="accepted">Accept</option>
            <option value="rejected">Reject</option>
          </select>
        </td>
        <td><input data-role="fib-canonical" value="${esc(item.sample_answer || item.normalized_text_answer)}"></td>
        <td><button type="button" data-action="fib-apply" data-question-id="${esc(item.question_id)}" data-normalized="${esc(item.normalized_text_answer)}">Apply</button></td>
      `;
      el.fibReviewBody.appendChild(tr);
    });
  }

  async function loadFibReview() {
    const examId = requireExam();
    const items = await api(`/admin/exams/${examId}/fib-review-queue`);
    renderFibQueue(items);
    setStatus(items.length ? "FIB review queue loaded." : "No FIB review pending.");
  }

  async function applyFibDecision(button) {
    const row = button.closest("tr");
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/fib-review-decisions`, {
      method: "POST",
      body: {
        question_id: button.dataset.questionId,
        normalized_text_answer: button.dataset.normalized,
        decision: row.querySelector('[data-role="fib-decision"]').value,
        canonical_answer_text: row.querySelector('[data-role="fib-canonical"]').value,
      },
    });
    setStatus(`FIB decision applied for ${data.impacted_attempt_count} attempt(s).`);
    await loadFibReview();
  }

  function renderSubjectiveQueue(items) {
    el.subjectiveReviewBody.innerHTML = "";
    if (!items.length) {
      el.subjectiveReviewBody.innerHTML = '<tr><td colspan="8">No subjective reviews pending.</td></tr>';
      return;
    }
    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${esc(item.student_id)}</td>
        <td>${esc(item.question_text)}</td>
        <td>${esc(item.question_type)}</td>
        <td>${esc(item.word_count ?? 0)} / ${esc(item.word_target_max ?? "-")}</td>
        <td>${esc(item.text_answer || "")}</td>
        <td><input data-role="subjective-marks" type="number" min="0" max="${esc(item.max_marks)}" step="0.5" value="0" style="width:90px"></td>
        <td><input data-role="subjective-note" placeholder="Optional note"></td>
        <td><button type="button" data-action="subjective-save" data-attempt-id="${esc(item.attempt_id)}" data-question-id="${esc(item.question_id)}">Save</button></td>
      `;
      el.subjectiveReviewBody.appendChild(tr);
    });
  }

  async function loadSubjectiveReview() {
    const examId = requireExam();
    const items = await api(`/admin/exams/${examId}/subjective-review-queue`);
    renderSubjectiveQueue(items);
    setStatus(items.length ? "Subjective review queue loaded." : "No subjective reviews pending.");
  }

  async function saveSubjectiveReview(button) {
    const row = button.closest("tr");
    const marks_awarded = Number(
      row.querySelector('[data-role="subjective-marks"]').value || 0,
    );
    const review_note = row.querySelector('[data-role="subjective-note"]').value || null;
    const data = await api(`/admin/attempts/${button.dataset.attemptId}/subjective-review`, {
      method: "POST",
      body: {
        question_id: button.dataset.questionId,
        marks_awarded,
        review_note,
      },
    });
    setStatus(`Subjective marks saved. Pending review count: ${data.pending_review_count}`);
    await loadSubjectiveReview();
  }

  async function loadAudit() {
    const params = new URLSearchParams();
    if (el.auditEntityType.value.trim()) params.set("entity_type", el.auditEntityType.value.trim());
    if (el.auditEntityId.value.trim()) params.set("entity_id", el.auditEntityId.value.trim());
    if (el.auditEventType.value.trim()) params.set("event_type", el.auditEventType.value.trim());
    const query = params.toString();
    const data = await api(`/admin/audit/events${query ? `?${query}` : ""}`);
    const events = data.events || [];
    el.auditEventsBody.innerHTML = events.length
      ? events
          .map(
            (event) =>
              `<tr><td>${esc(event.created_at)}</td><td>${esc(`${event.entity_type}:${event.entity_id}`)}</td><td>${esc(event.event_type)}</td><td>${esc(event.actor_id || "")}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="4">No audit events found.</td></tr>';
    setStatus(`Loaded ${events.length} audit event(s).`);
  }

  async function loadAccessProfile() {
    const data = await fetch("/system/access-profile");
    const payload = await data.json();
    el.accessProfileBox.textContent = prettyJson(payload.data ?? payload);
  }

  async function loadMetrics() {
    const data = await api("/admin/system/metrics");
    if (!el.metricsBox) return;
    el.metricsBox.innerHTML = renderMetricsDashboard(data);
    setStatus("Operational health dashboard loaded.");
  }

  async function loadAnalytics() {
    const examId = requireExam();
    st.analyticsUi = {
      ...st.analyticsUi,
      questionSearch: "",
      questionFilter: "all",
      questionSort: "correct_desc",
      difficultySearch: "",
      difficultyFilter: "all",
      difficultySort: "difficulty_index_asc",
    };
    await ensureAnalyticsQuestionCache();
    const [summary, difficultyHeatmap, topicHeatmap, scoreDistribution] = await Promise.all([
      api(`/admin/exams/${examId}/analytics`),
      api(`/admin/exams/${examId}/analytics/difficulty-heatmap`),
      api(`/admin/exams/${examId}/analytics/topic-heatmap`),
      api(`/admin/exams/${examId}/analytics/score-distribution`),
    ]);
    st.analyticsData = prepareAnalyticsPayload(
      summary,
      difficultyHeatmap,
      topicHeatmap,
      scoreDistribution,
    );
    renderAnalyticsDashboardFromState();
    setStatus("Analytics dashboard loaded.");
  }

  async function generateExamSummary() {
    const examId = requireExam();
    if (!el.examSummaryBox) return;
    await ensureAnalyticsQuestionCache();
    const [resultsData, summary, difficultyHeatmap, topicHeatmap, scoreDistribution] = await Promise.all([
      api(`/admin/exams/${examId}/results`),
      api(`/admin/exams/${examId}/analytics`),
      api(`/admin/exams/${examId}/analytics/difficulty-heatmap`),
      api(`/admin/exams/${examId}/analytics/topic-heatmap`),
      api(`/admin/exams/${examId}/analytics/score-distribution`),
    ]);
    const analyticsPayload = prepareAnalyticsPayload(
      summary,
      difficultyHeatmap,
      topicHeatmap,
      scoreDistribution,
    );
    st.analyticsData = analyticsPayload;
    el.examSummaryBox.innerHTML = renderExamSummary(resultsData, analyticsPayload);
    setStatus("Graphical exam summary generated.");
  }

  async function loadAiStatus() {
    if (!el.aiStatusBox) return;
    const data = await api("/admin/ai/status");
    el.aiStatusBox.textContent = prettyJson(data);
    setStatus(data.reachable ? "Offline AI sidecar reachable." : "Offline AI sidecar unavailable; heuristic mode active.");
  }

  async function refineQuestionWithAi() {
    const data = await api("/admin/ai/question-refine", {
      method: "POST",
      body: {
        question_text: (el.aiQuestionText.value || "").trim(),
        question_type: el.aiQuestionType.value || "mcq_single",
        topic: (el.aiQuestionTopic.value || "General").trim() || "General",
        marks: Number(el.aiQuestionMarks.value || 1),
      },
    });
    el.aiQuestionResult.textContent = prettyJson(data);
    setStatus("AI question refinement generated.");
  }

  async function suggestRubricWithAi() {
    const data = await api("/admin/ai/rubric-suggest", {
      method: "POST",
      body: {
        question_text: (el.aiRubricQuestion.value || "").trim(),
        question_type: el.aiRubricType.value || "short_answer",
        max_marks: Number(el.aiRubricMarks.value || 1),
      },
    });
    el.aiRubricResult.textContent = prettyJson(data);
    setStatus("AI rubric suggestion generated.");
  }

  async function clusterFibWithAi() {
    const answers = parseLines(el.aiFibAnswers.value);
    const data = await api("/admin/ai/fib-cluster", {
      method: "POST",
      body: {
        question_text: (el.aiFibQuestion.value || "").trim(),
        answers,
      },
    });
    el.aiFibResult.textContent = prettyJson(data);
    setStatus("AI FIB clustering generated.");
  }

  async function suggestSubjectiveWithAi() {
    const data = await api("/admin/ai/subjective-suggest", {
      method: "POST",
      body: {
        question_text: (el.aiSubjectiveQuestion.value || "").trim(),
        question_type: el.aiSubjectiveType.value || "short_answer",
        answer_text: (el.aiSubjectiveAnswer.value || "").trim(),
        max_marks: Number(el.aiSubjectiveMarks.value || 1),
      },
    });
    el.aiSubjectiveResult.textContent = prettyJson(data);
    setStatus("AI subjective suggestion generated.");
  }

  async function summarizeAnalyticsWithAi() {
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/ai/analytics-summary`, { method: "POST" });
    el.aiAnalyticsBox.textContent = prettyJson(data);
    setStatus("AI exam summary generated.");
  }

  function renderResultsTable(data) {
    st.examResults = data.candidates || [];
    el.resultsPublicationBox.textContent = prettyJson({
      exam_id: data.exam_id,
      exam_name: data.exam_name,
      results_published: data.results_published,
      results_published_at: data.results_published_at,
      results_published_by: data.results_published_by,
      pending_review_count: data.pending_review_count,
      ready_result_count: data.ready_result_count,
    });
    el.resultsCandidatesBody.innerHTML = st.examResults.length
      ? st.examResults
          .map(
            (item) => `
              <tr>
                <td>${esc(item.display_name || item.student_id)}<br><span class="small mono">${esc(item.student_id)}</span></td>
                <td><span class="mono">${esc(item.attempt_id)}</span></td>
                <td>${item.total_score == null ? "-" : esc(formatNumber(item.total_score, 2))} / ${item.total_possible_marks == null ? "-" : esc(formatNumber(item.total_possible_marks, 2))}</td>
                <td>${item.percentage == null ? "-" : esc(formatPercent(item.percentage))}</td>
                <td>${esc(item.pending_review_count)}</td>
                <td>${item.pending_review_count > 0 ? "Pending Review" : item.passed == null ? "Awaiting Result" : item.passed ? "Pass" : "Fail"}</td>
                <td class="result-action-cell">
                  <button type="button" data-action="result-preview" data-attempt-id="${esc(item.attempt_id)}">Preview Result</button>
                  <button type="button" data-action="result-print" data-attempt-id="${esc(item.attempt_id)}">Print Result</button>
                  <button type="button" data-action="result-pdf" data-attempt-id="${esc(item.attempt_id)}">Download PDF</button>
                  <button type="button" data-action="result-share" data-attempt-id="${esc(item.attempt_id)}">Share / Export</button>
                </td>
              </tr>
            `,
          )
          .join("")
      : '<tr><td colspan="7">No candidate results available yet.</td></tr>';
  }

  async function refreshResults() {
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/results`);
    renderResultsTable(data);
    setStatus("Exam result list loaded.");
  }

  async function publishResults() {
    const examId = requireExam();
    const data = await api(`/admin/exams/${examId}/results/publish`, { method: "POST" });
    await loadExams(examId);
    await refreshResults();
    setStatus(`Results published by ${data.results_published_by}.`);
  }

  async function unpublishResults() {
    const examId = requireExam();
    await api(`/admin/exams/${examId}/results/unpublish`, { method: "POST" });
    await loadExams(examId);
    await refreshResults();
    setStatus("Results reverted to admin-only unpublished state.");
  }

  async function downloadResultsCsv() {
    const examId = requireExam();
    const { blob, fileName } = await downloadBlob(`/admin/exams/${examId}/results/export.csv`);
    triggerBlobDownload(blob, fileName);
    setStatus("Published result CSV downloaded.");
    await loadArtifacts().catch(() => {});
  }

  async function downloadPendingReviewCsv() {
    const examId = requireExam();
    const { blob, fileName } = await downloadBlob(`/admin/exams/${examId}/results/pending-review.csv`);
    triggerBlobDownload(blob, fileName);
    setStatus("Pending review CSV downloaded.");
    await loadArtifacts().catch(() => {});
  }

  async function handleResultAction(button) {
    const attemptId = button.dataset.attemptId;
    if (!attemptId) throw new Error("Attempt ID missing.");
    if (button.dataset.action === "result-preview" || button.dataset.action === "result-print") {
      const win = await openBlobPage(`/admin/attempts/${attemptId}/result-preview`);
      if (button.dataset.action === "result-print") {
        setTimeout(() => {
          try {
            win.print();
          } catch {
            // Browser handles print fallback through the preview page button.
          }
        }, 500);
      }
      setStatus(button.dataset.action === "result-print" ? "Printable result preview opened." : "Result preview opened.");
      await loadArtifacts().catch(() => {});
      return;
    }
    if (button.dataset.action === "result-pdf") {
      const { blob, fileName } = await downloadBlob(`/admin/attempts/${attemptId}/result-sheet.pdf`);
      triggerBlobDownload(blob, fileName);
      setStatus("Result PDF downloaded.");
      await loadArtifacts().catch(() => {});
      return;
    }
    if (button.dataset.action === "result-share") {
      const { blob } = await downloadBlob(`/admin/attempts/${attemptId}/result-preview`);
      const htmlFile =
        typeof File === "function"
          ? new File([blob], `result_preview_${attemptId}.html`, { type: "text/html" })
          : null;
      if (htmlFile && navigator.share && navigator.canShare?.({ files: [htmlFile] })) {
        await navigator.share({ title: "NITMEXS Result Preview", files: [htmlFile] });
      } else {
        triggerBlobDownload(blob, htmlFile?.name || `result_preview_${attemptId}.html`);
      }
      setStatus("Result preview prepared for local export/share.");
    }
  }

  async function loadArtifacts() {
    const examId = selectedExamId() || "";
    const query = examId ? `?exam_id=${encodeURIComponent(examId)}` : "";
    const data = await api(`/admin/artifacts${query}`);
    el.artifactsBody.innerHTML = data.length
      ? data
          .map(
            (item) => `
              <tr>
                <td>${esc(item.created_at)}</td>
                <td>${esc(item.artifact_type)}</td>
                <td>${esc(item.file_name)}</td>
                <td>${esc(item.reference_code)}</td>
                <td>${esc(item.created_by)}</td>
              </tr>
            `,
          )
          .join("")
      : '<tr><td colspan="5">No generated artifacts yet.</td></tr>';
  }

  function bindQuestionTable() {
    el.questionsBody.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const question = st.questions.find((item) => item.id === button.dataset.questionId);
      if (button.dataset.action === "preview") {
        st.selectedQuestion = question || null;
        el.studentPreviewBox.innerHTML = question
          ? renderPreview(question)
          : '<p class="small">Question not found.</p>';
        return;
      }
      if (button.dataset.action === "attach") {
        try {
          await attachQuestionToExam(button.dataset.questionId);
        } catch (error) {
          setStatus(error.message, true);
        }
      }
    });
  }

  function bindReviewTables() {
    el.fibReviewBody.addEventListener("click", async (event) => {
      const button = event.target.closest('button[data-action="fib-apply"]');
      if (!button) return;
      try {
        await applyFibDecision(button);
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    el.subjectiveReviewBody.addEventListener("click", async (event) => {
      const button = event.target.closest('button[data-action="subjective-save"]');
      if (!button) return;
      try {
        await saveSubjectiveReview(button);
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  }

  function bindResultTable() {
    el.resultsCandidatesBody?.addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      try {
        await handleResultAction(button);
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  }

  function bindEvents() {
    bindPasswordControls(
      el.studentPasswordInput,
      el.studentPasswordToggle,
      el.studentPasswordCapsWarning,
    );
    bindPasswordControls(
      el.newAdminKey,
      el.newAdminKeyToggle,
      el.newAdminKeyCapsWarning,
    );
    el.logoutAdmin.addEventListener("click", () => {
      localStorage.removeItem(SESSION_KEY);
      window.location.href = "/web";
    });
    el.toggleAdminDrawer?.addEventListener("click", () => {
      applyAdminDrawerState(!st.drawerCollapsed);
    });
    el.openDownloadsTop?.addEventListener("click", () => setAdminTab("downloads"));
    el.errorClose?.addEventListener("click", () => closeDialog(el.errorDialog));
    el.errorDialog?.addEventListener("click", (event) => {
      if (event.target === el.errorDialog) closeDialog(el.errorDialog);
    });
    el.analyticsBox?.addEventListener("input", handleAnalyticsControlEvent);
    el.analyticsBox?.addEventListener("change", handleAnalyticsControlEvent);
    adminTabButtons().forEach((button) => {
      button.addEventListener("click", () => setAdminTab(button.dataset.adminTab));
    });
    el.loadExams.addEventListener("click", () => loadExams().catch((error) => setStatus(error.message, true)));
    el.createExam.addEventListener("click", () => createExam().catch((error) => setStatus(error.message, true)));
    el.examSelect.addEventListener("change", () => {
      st.selectedExamId = el.examSelect.value;
      const exam = st.exams.find((item) => item.id === st.selectedExamId);
      el.referenceExamSelect.value = exam?.reference_exam_id || "";
      el.customRulesText.value = (exam?.custom_rules || []).join("\n");
      updateSelectedExamChip();
      loadArtifacts().catch(() => {});
    });
    el.saveCustomRules.addEventListener("click", () => saveCustomRules().catch((error) => setStatus(error.message, true)));
    el.saveReferenceExam.addEventListener("click", () => saveReferenceExam().catch((error) => setStatus(error.message, true)));
    el.publishExam.addEventListener("click", () => publishExam().catch((error) => setStatus(error.message, true)));
    el.closeExam.addEventListener("click", () => closeExam().catch((error) => setStatus(error.message, true)));
    el.deleteExam.addEventListener("click", () => deleteExam().catch((error) => setStatus(error.message, true)));
    el.refreshLive.addEventListener("click", () => refreshLiveStatus().catch((error) => setStatus(error.message, true)));
    el.pauseExam.addEventListener("click", () => applyExamControl("pause").catch((error) => setStatus(error.message, true)));
    el.resumeExam.addEventListener("click", () => applyExamControl("resume").catch((error) => setStatus(error.message, true)));
    el.forceSubmitAttempt.addEventListener("click", () => forceSubmitAttempt().catch((error) => setStatus(error.message, true)));
    el.forceSubmitExpired.addEventListener("click", () => forceSubmitExpired().catch((error) => setStatus(error.message, true)));
    el.sendBroadcast.addEventListener("click", () => sendBroadcast().catch((error) => setStatus(error.message, true)));
    el.uploadQuestionCsv.addEventListener("click", () => uploadCsv(el.questionCsvFile, "/admin/questions/import-csv", el.questionUploadResult).then(() => loadQuestions()).catch((error) => setStatus(error.message, true)));
    el.uploadExamPack.addEventListener("click", () => uploadCsv(el.examPackFile, "/admin/exams/import-question-pack-csv", el.examPackResult).then((data) => loadExams(data.exam_id)).catch((error) => setStatus(error.message, true)));
    el.loadQuestions.addEventListener("click", () => loadQuestions().catch((error) => setStatus(error.message, true)));
    el.createQuestion.addEventListener("click", () => createQuestion().catch((error) => { el.questionCreateResult.textContent = error.message; setStatus(error.message, true); }));
    el.createStudentId.addEventListener("click", () => createStudent().catch((error) => setStatus(error.message, true)));
    el.generateStudentIds.addEventListener("click", () => generateStudents().catch((error) => setStatus(error.message, true)));
    el.uploadStudentCsv.addEventListener("click", () => importStudents().catch((error) => setStatus(error.message, true)));
    el.exportStudentCsv.addEventListener("click", () => exportStudents().catch((error) => setStatus(error.message, true)));
    el.refreshStudentIds.addEventListener("click", () => loadStudents().catch((error) => setStatus(error.message, true)));
    el.loadFibReview.addEventListener("click", () => loadFibReview().catch((error) => setStatus(error.message, true)));
    el.loadSubjectiveReview.addEventListener("click", () => loadSubjectiveReview().catch((error) => setStatus(error.message, true)));
    el.loadAuditEvents.addEventListener("click", () => loadAudit().catch((error) => setStatus(error.message, true)));
    el.loadAccessProfile.addEventListener("click", () => loadAccessProfile().catch((error) => setStatus(error.message, true)));
    el.loadMetrics.addEventListener("click", () => loadMetrics().catch((error) => setStatus(error.message, true)));
    el.generateExamSummary?.addEventListener("click", () => generateExamSummary().catch((error) => setStatus(error.message, true)));
    el.loadExamAnalytics.addEventListener("click", () => loadAnalytics().catch((error) => setStatus(error.message, true)));
    el.loadExamAnalyticsSecondary?.addEventListener("click", () => loadAnalytics().catch((error) => setStatus(error.message, true)));
    el.loadAiStatus?.addEventListener("click", () => loadAiStatus().catch((error) => setStatus(error.message, true)));
    el.aiRefineQuestion?.addEventListener("click", () => refineQuestionWithAi().catch((error) => setStatus(error.message, true)));
    el.aiRubricSuggest?.addEventListener("click", () => suggestRubricWithAi().catch((error) => setStatus(error.message, true)));
    el.aiFibCluster?.addEventListener("click", () => clusterFibWithAi().catch((error) => setStatus(error.message, true)));
    el.aiSubjectiveSuggest?.addEventListener("click", () => suggestSubjectiveWithAi().catch((error) => setStatus(error.message, true)));
    el.aiSummarizeAnalytics?.addEventListener("click", () => summarizeAnalyticsWithAi().catch((error) => setStatus(error.message, true)));
    el.refreshResults?.addEventListener("click", () => refreshResults().catch((error) => setStatus(error.message, true)));
    el.publishResults?.addEventListener("click", () => publishResults().catch((error) => setStatus(error.message, true)));
    el.unpublishResults?.addEventListener("click", () => unpublishResults().catch((error) => setStatus(error.message, true)));
    el.downloadResultsCsv?.addEventListener("click", () => downloadResultsCsv().catch((error) => setStatus(error.message, true)));
    el.downloadPendingCsv?.addEventListener("click", () => downloadPendingReviewCsv().catch((error) => setStatus(error.message, true)));
    el.loadArtifacts?.addEventListener("click", () => loadArtifacts().catch((error) => setStatus(error.message, true)));
    el.createAdminAccount?.addEventListener("click", () => createAdminAccount().catch((error) => setStatus(error.message, true)));
    el.loadAdminAccounts?.addEventListener("click", () => loadAdminAccounts().catch((error) => setStatus(error.message, true)));
    bindQuestionTable();
    bindReviewTables();
    bindResultTable();
  }

  try {
    ensureSession();
    bindEvents();
    applyAdminDrawerState(loadAdminDrawerState());
    setAdminTab("dashboard");
    loadVersion();
    loadExams().catch((error) => setStatus(error.message, true));
    loadQuestions().catch((error) => setStatus(error.message, true));
    loadStudents().catch((error) => setStatus(error.message, true));
    if (st.role === "superadmin") {
      loadAdminAccounts().catch((error) => setStatus(error.message, true));
    }
    loadAccessProfile().catch(() => {});
    loadArtifacts().catch(() => {});
  } catch {
    // Redirect handled in ensureSession.
  }
})();
