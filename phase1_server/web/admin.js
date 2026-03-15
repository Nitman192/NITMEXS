(() => {
  const SESSION_KEY = "nitmexs_admin_session";
  const $ = (id) => document.getElementById(id);
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const st = {
    adminId: "",
    role: "superadmin",
    exams: [],
    questions: [],
    selectedExamId: "",
    selectedQuestion: null,
  };

  const el = {
    sessionAdmin: $("session-admin"),
    version: $("version"),
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
    loadExamAnalytics: $("load-exam-analytics"),
    analyticsBox: $("analytics-box"),
    adminAccountsPanel: $("admin-accounts-panel"),
    newAdminId: $("new-admin-id"),
    newAdminName: $("new-admin-name"),
    newAdminRole: $("new-admin-role"),
    newAdminKey: $("new-admin-key"),
    createAdminAccount: $("create-admin-account"),
    loadAdminAccounts: $("load-admin-accounts"),
    adminAccountResult: $("admin-account-result"),
    adminAccountsBody: $("admin-accounts-body"),
  };

  function setStatus(message, isError = false) {
    if (!el.status) return;
    el.status.textContent = message;
    el.status.classList.toggle("error", isError);
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
    if (!res.ok) throw new Error(payload.detail || payload.error || `HTTP ${res.status}`);
    return payload.data ?? payload;
  }

  async function download(path) {
    const res = await fetch(path, { headers: headers() });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload.detail || payload.error || `HTTP ${res.status}`);
    }
    return res.text();
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

  function renderQuestionMetrics(rows) {
    if (!rows.length) {
      return '<p class="small">Per-question metrics abhi ready nahi hain.</p>';
    }
    return `
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
                    <td><span class="mono">${esc(compactId(row.question_id))}</span></td>
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

  function renderDifficultyHeatmap(cells) {
    if (!cells.length) {
      return '<p class="small">Difficulty heatmap abhi empty hai.</p>';
    }
    return `
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
                    <td><span class="mono">${esc(compactId(cell.question_id))}</span></td>
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

    return `
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
              <p class="small">Each question ki correctness aur average score.</p>
            </div>
          </div>
          ${renderQuestionMetrics(questionMetrics)}
        </article>
        <article class="analytics-panel">
          <div class="analytics-panel-head">
            <div>
              <h3>Difficulty Heatmap</h3>
              <p class="small">Difficulty index aur discrimination values friendly table me.</p>
            </div>
          </div>
          ${renderDifficultyHeatmap(difficultyCells)}
        </article>
      </section>
    `;
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
    }
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
    el.metricsBox.textContent = prettyJson(data);
  }

  async function loadAnalytics() {
    const examId = requireExam();
    const [summary, difficultyHeatmap, topicHeatmap, scoreDistribution] = await Promise.all([
      api(`/admin/exams/${examId}/analytics`),
      api(`/admin/exams/${examId}/analytics/difficulty-heatmap`),
      api(`/admin/exams/${examId}/analytics/topic-heatmap`),
      api(`/admin/exams/${examId}/analytics/score-distribution`),
    ]);
    el.analyticsBox.innerHTML = renderAnalyticsDashboard(
      summary,
      difficultyHeatmap,
      topicHeatmap,
      scoreDistribution,
    );
    setStatus("Analytics dashboard loaded.");
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

  function bindEvents() {
    el.logoutAdmin.addEventListener("click", () => {
      localStorage.removeItem(SESSION_KEY);
      window.location.href = "/web";
    });
    el.loadExams.addEventListener("click", () => loadExams().catch((error) => setStatus(error.message, true)));
    el.createExam.addEventListener("click", () => createExam().catch((error) => setStatus(error.message, true)));
    el.examSelect.addEventListener("change", () => {
      st.selectedExamId = el.examSelect.value;
      const exam = st.exams.find((item) => item.id === st.selectedExamId);
      el.referenceExamSelect.value = exam?.reference_exam_id || "";
      el.customRulesText.value = (exam?.custom_rules || []).join("\n");
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
    el.loadExamAnalytics.addEventListener("click", () => loadAnalytics().catch((error) => setStatus(error.message, true)));
    el.createAdminAccount?.addEventListener("click", () => createAdminAccount().catch((error) => setStatus(error.message, true)));
    el.loadAdminAccounts?.addEventListener("click", () => loadAdminAccounts().catch((error) => setStatus(error.message, true)));
    bindQuestionTable();
    bindReviewTables();
  }

  try {
    ensureSession();
    bindEvents();
    loadVersion();
    loadExams().catch((error) => setStatus(error.message, true));
    loadQuestions().catch((error) => setStatus(error.message, true));
    loadStudents().catch((error) => setStatus(error.message, true));
    if (st.role === "superadmin") {
      loadAdminAccounts().catch((error) => setStatus(error.message, true));
    }
    loadAccessProfile().catch(() => {});
  } catch {
    // Redirect handled in ensureSession.
  }
})();
