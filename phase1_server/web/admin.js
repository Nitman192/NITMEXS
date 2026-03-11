(() => {
  const ADMIN_SESSION_KEY = "nitmexs_admin_session";
  const GUIDED_MODE_KEY = "nitmexs_admin_guided_mode";
  const IDLE_TIMEOUT_POLICY_KEY = "nitmexs_admin_idle_timeout_ms";
  const IDLE_TIMEOUT_DEFAULT_MS = 10_000;

  const $ = (id) => document.getElementById(id);
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const st = {
    adminId: "",
    examId: "",
    cursor: null,
    polling: false,
    pollTimerId: null,
    idleTimerId: null,
    idleLockMs: IDLE_TIMEOUT_DEFAULT_MS,
    seenEventIds: new Set(),
    questionMap: new Map(),
    latestMetrics: null,
    latestDashboard: null,
  };

  const el = {
    sessionAdmin: $("session-admin"),
    version: $("version"),
    guidedToggle: $("guided-toggle"),
    emergencyStop: $("emergency-stop-btn"),
    logoutAdmin: $("logout-admin"),
    loadExams: $("load-exams"),
    examSelect: $("exam-select"),
    status: $("admin-status"),
    navButtons: Array.from(document.querySelectorAll(".nav-btn")),
    pages: Array.from(document.querySelectorAll(".page-panel")),
    refreshLive: $("refresh-live"),
    syncAlerts: $("sync-alerts"),
    loadAlerts: $("load-alerts"),
    forceAttemptId: $("force-attempt-id"),
    forceSubmitAttempt: $("force-submit-attempt"),
    forceSubmitExpired: $("force-submit-expired"),
    examControlReason: $("exam-control-reason"),
    pauseExam: $("pause-exam"),
    resumeExam: $("resume-exam"),
    broadcastMessage: $("broadcast-message"),
    broadcastSeverity: $("broadcast-severity"),
    sendBroadcast: $("send-broadcast"),
    forceSubmitResult: $("force-submit-result"),
    broadcastResult: $("broadcast-result"),
    liveSummary: $("live-summary"),
    activeBody: $("active-body"),
    alertBody: $("alert-body"),
    pullEvents: $("pull-events"),
    toggleAuto: $("toggle-auto"),
    cursorLabel: $("cursor-label"),
    eventsBody: $("events-body"),
    auditEntityType: $("audit-entity-type"),
    auditEntityId: $("audit-entity-id"),
    auditEventType: $("audit-event-type"),
    auditActorId: $("audit-actor-id"),
    loadAuditEvents: $("load-audit-events"),
    auditEventsBody: $("audit-events-body"),
    questionCsvFile: $("question-csv-file"),
    uploadQuestionCsv: $("upload-question-csv"),
    questionUploadResult: $("question-upload-result"),
    examPackFile: $("exam-pack-file"),
    uploadExamPack: $("upload-exam-pack"),
    examPackResult: $("exam-pack-result"),
    loadQuestions: $("load-questions"),
    questionCount: $("question-count"),
    questionsBody: $("questions-body"),
    studentPreviewBox: $("student-preview-box"),
    studentIdInput: $("student-id-input"),
    studentNameInput: $("student-name-input"),
    createStudentId: $("create-student-id"),
    studentPrefix: $("student-prefix"),
    studentCount: $("student-count"),
    generateStudentIds: $("generate-student-ids"),
    refreshStudentIds: $("refresh-student-ids"),
    studentCsvFile: $("student-csv-file"),
    uploadStudentCsv: $("upload-student-csv"),
    exportStudentCsv: $("export-student-csv"),
    studentIdResult: $("student-id-result"),
    studentCsvResult: $("student-csv-result"),
    studentsBody: $("students-body"),
    minAttempts: $("min-attempts"),
    applyRun: $("apply-run"),
    runRecalibration: $("run-recalibration"),
    loadHistory: $("load-history"),
    rollbackReason: $("rollback-reason"),
    runSummary: $("run-summary"),
    runsBody: $("runs-body"),
    itemsBody: $("items-body"),
    loadAnalytics: $("load-analytics"),
    analyticsSummary: $("analytics-summary"),
    difficultyBody: $("difficulty-body"),
    topicBody: $("topic-body"),
    distributionBody: $("distribution-body"),
    loadMetrics: $("load-metrics"),
    loadDashboard: $("load-dashboard"),
    idleTimeoutSeconds: $("idle-timeout-seconds"),
    applyIdleTimeout: $("apply-idle-timeout"),
    metricsBox: $("metrics-box"),
    dashboardBox: $("dashboard-box"),
    infraHealthBox: $("infra-health-box"),
  };

  const setStatus = (message) => {
    el.status.textContent = message;
  };

  function parseAdminSession() {
    try {
      const raw = localStorage.getItem(ADMIN_SESSION_KEY);
      if (!raw) {
        return null;
      }
      const payload = JSON.parse(raw);
      if (!payload?.admin_id) {
        return null;
      }
      return payload;
    } catch {
      return null;
    }
  }

  function ensureAdminSession() {
    const session = parseAdminSession();
    if (!session) {
      window.location.href = "/web?target=admin&reason=login_required";
      throw new Error("Admin login required");
    }
    st.adminId = session.admin_id;
    el.sessionAdmin.textContent = session.admin_id;
    return session;
  }

  function adminHeaders() {
    return { "x-admin": "true", "x-admin-id": st.adminId };
  }

  async function api(path, options = {}) {
    const request = { ...options, headers: { ...(options.headers || {}) } };
    if (
      request.body &&
      typeof request.body !== "string" &&
      !(request.body instanceof FormData)
    ) {
      request.headers["Content-Type"] = "application/json";
      request.body = JSON.stringify(request.body);
    }
    const response = await fetch(path, request);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
    }
    return payload.data ?? payload;
  }

  function formatDate(iso) {
    if (!iso) {
      return "-";
    }
    const date = new Date(iso);
    if (Number.isNaN(date.valueOf())) {
      return iso;
    }
    return date.toLocaleString();
  }

  function formatRemaining(seconds) {
    if (seconds == null) {
      return "-";
    }
    const value = Math.max(0, Number(seconds) || 0);
    const mins = Math.floor(value / 60);
    const secs = value % 60;
    return `${mins}m ${secs}s`;
  }

  function readGuidedMode() {
    return localStorage.getItem(GUIDED_MODE_KEY) === "on";
  }

  function normalizeIdleTimeoutMs(secondsInput) {
    const parsedSeconds = Number(secondsInput);
    if (Number.isNaN(parsedSeconds)) {
      return IDLE_TIMEOUT_DEFAULT_MS;
    }
    const clampedSeconds = Math.min(3600, Math.max(10, Math.round(parsedSeconds)));
    return clampedSeconds * 1000;
  }

  function readIdleTimeoutPolicy() {
    const stored = localStorage.getItem(IDLE_TIMEOUT_POLICY_KEY);
    if (!stored) {
      return IDLE_TIMEOUT_DEFAULT_MS;
    }
    const storedMs = Number(stored);
    if (Number.isNaN(storedMs)) {
      return IDLE_TIMEOUT_DEFAULT_MS;
    }
    return normalizeIdleTimeoutMs(storedMs / 1000);
  }

  function applyIdleTimeoutPolicy(nextTimeoutMs, persist) {
    st.idleLockMs = normalizeIdleTimeoutMs(nextTimeoutMs / 1000);
    if (el.idleTimeoutSeconds) {
      el.idleTimeoutSeconds.value = String(Math.round(st.idleLockMs / 1000));
    }
    if (persist) {
      localStorage.setItem(IDLE_TIMEOUT_POLICY_KEY, String(st.idleLockMs));
    }
    resetIdleTimer();
  }

  function applyGuidedMode(enabled) {
    document.body.classList.toggle("guided-on", enabled);
    el.guidedToggle.checked = enabled;
    localStorage.setItem(GUIDED_MODE_KEY, enabled ? "on" : "off");
  }

  function activatePage(pageId) {
    el.navButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.page === pageId);
    });
    el.pages.forEach((page) => {
      page.classList.toggle("active", page.id === pageId);
    });
  }

  function lockIdleShield() {
    document.body.classList.add("idle-lock");
  }

  function unlockIdleShield() {
    document.body.classList.remove("idle-lock");
  }

  function resetIdleTimer() {
    unlockIdleShield();
    if (st.idleTimerId) {
      clearTimeout(st.idleTimerId);
    }
    st.idleTimerId = window.setTimeout(lockIdleShield, st.idleLockMs);
  }

  function bindIdleActivityListeners() {
    const events = ["mousemove", "keydown", "mousedown", "wheel", "touchstart"];
    events.forEach((eventName) => {
      document.addEventListener(eventName, resetIdleTimer, { passive: true });
    });
    resetIdleTimer();
  }

  function logoutAdmin() {
    localStorage.removeItem(ADMIN_SESSION_KEY);
    window.location.href = "/web?target=admin&reason=login_required";
  }

  function renderExamOptions(exams) {
    const previous = el.examSelect.value;
    el.examSelect.innerHTML = '<option value="">Select exam...</option>';
    for (const exam of exams) {
      el.examSelect.insertAdjacentHTML(
        "beforeend",
        `<option value="${esc(exam.id)}">${esc(exam.name)} [${esc(exam.status)}]</option>`
      );
    }
    if (previous && exams.some((exam) => exam.id === previous)) {
      el.examSelect.value = previous;
    }
  }

  function currentExamId(optional = false) {
    const selected = (el.examSelect?.value || "").trim();
    if (selected) {
      st.examId = selected;
      return selected;
    }
    if (st.examId) {
      return st.examId;
    }
    const firstExamOption = Array.from(el.examSelect?.options || []).find(
      (option) => option.value
    );
    if (firstExamOption) {
      el.examSelect.value = firstExamOption.value;
      st.examId = firstExamOption.value;
      return firstExamOption.value;
    }
    if (optional) {
      return "";
    }
    throw new Error("Exam select nahi hai. Pehle Load Exams karo, phir exam choose karo.");
  }

  async function loadVersion() {
    try {
      const data = await api("/system/version");
      el.version.textContent = data.version;
    } catch {
      el.version.textContent = "n/a";
    }
  }

  async function loadExams() {
    try {
      const exams = await api("/admin/exams", { headers: adminHeaders() });
      renderExamOptions(exams);
      setStatus(`Loaded ${exams.length} exam(s).`);
    } catch (error) {
      if (el.forceSubmitResult) {
        el.forceSubmitResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  function renderActiveAttempts(rows) {
    if (!rows.length) {
      el.activeBody.innerHTML = '<tr><td colspan="5" class="small">No active attempts.</td></tr>';
      return;
    }
    el.activeBody.innerHTML = rows
      .map(
        (row) => `
          <tr>
            <td class="mono">${esc(row.attempt_id)}</td>
            <td>${esc(row.student_id)}</td>
            <td>${esc(formatRemaining(row.remaining_seconds))}</td>
            <td>${esc(String(row.answered_question_count || 0))}/${esc(String(row.total_question_count || 0))}</td>
            <td>${esc((Number(row.progress_percent || 0)).toFixed(1))}%</td>
          </tr>
        `
      )
      .join("");
  }

  function renderAlerts(rows) {
    if (!rows.length) {
      el.alertBody.innerHTML = '<tr><td colspan="6" class="small">No alerts.</td></tr>';
      return;
    }
    el.alertBody.innerHTML = rows
      .map(
        (alert) => `
          <tr>
            <td class="mono">${esc(alert.id)}</td>
            <td>${esc(alert.status)}</td>
            <td>${esc(alert.indicator_code)}</td>
            <td>${esc(alert.student_id)}</td>
            <td>${esc(formatDate(alert.last_detected_at || alert.created_at))}</td>
            <td>
              <button class="alt js-ack" data-alert-id="${esc(alert.id)}">Ack</button>
              <button class="warn js-resolve" data-alert-id="${esc(alert.id)}">Resolve</button>
            </td>
          </tr>
        `
      )
      .join("");
  }

  function renderEvents(events) {
    if (!events.length && !el.eventsBody.children.length) {
      el.eventsBody.innerHTML = '<tr><td colspan="5" class="small">No events yet.</td></tr>';
      return;
    }
    if (!events.length) {
      return;
    }
    if (el.eventsBody.textContent.includes("No events yet")) {
      el.eventsBody.innerHTML = "";
    }
    const fragment = document.createDocumentFragment();
    for (const event of events) {
      if (st.seenEventIds.has(event.event_id)) {
        continue;
      }
      st.seenEventIds.add(event.event_id);
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${esc(formatDate(event.created_at))}</td>
        <td>${esc(event.event_type)}</td>
        <td class="mono">${esc(event.attempt_id)}</td>
        <td>${esc(event.student_id)}</td>
        <td class="mono">${esc(event.event_id)}</td>
      `;
      fragment.appendChild(row);
    }
    el.eventsBody.appendChild(fragment);
  }

  function renderAuditEvents(events) {
    if (!events.length) {
      el.auditEventsBody.innerHTML = '<tr><td colspan="5" class="small">No audit events for current filter.</td></tr>';
      return;
    }
    el.auditEventsBody.innerHTML = events
      .map(
        (event) => `
          <tr>
            <td>${esc(formatDate(event.created_at))}</td>
            <td class="mono">${esc(event.entity_type)}:${esc(event.entity_id)}</td>
            <td>${esc(event.event_type)}</td>
            <td>${esc(event.actor_type)}:${esc(event.actor_id)}</td>
            <td class="mono">${esc(JSON.stringify(event.payload || {}))}</td>
          </tr>
        `
      )
      .join("");
  }

  async function refreshLive() {
    try {
      const examId = currentExamId();
      const [liveStatus, activeAttempts] = await Promise.all([
        api(`/admin/exams/${encodeURIComponent(examId)}/live-status`, {
          headers: adminHeaders(),
        }),
        api(`/admin/exams/${encodeURIComponent(examId)}/active-attempts`, {
          headers: adminHeaders(),
        }),
      ]);
      renderActiveAttempts(activeAttempts);
      el.liveSummary.textContent = JSON.stringify(
        {
          exam_id: liveStatus.exam_id,
          as_of: liveStatus.as_of,
          active_attempt_count: liveStatus.active_attempt_count,
          suspicious_indicator_count: (liveStatus.suspicious_indicators || []).length,
          finalize_events: (liveStatus.recent_finalize_events || []).length,
        },
        null,
        2
      );
      setStatus("Live status refreshed.");
    } catch (error) {
      if (el.forceSubmitResult) {
        el.forceSubmitResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  async function syncAlerts() {
    try {
      const examId = currentExamId();
      const data = await api(
        `/admin/proctor/alerts/sync?exam_id=${encodeURIComponent(examId)}`,
        {
          method: "POST",
          headers: adminHeaders(),
        }
      );
      setStatus(
        `Alerts synced: created=${data.created_count}, updated=${data.updated_count}, auto_resolved=${data.auto_resolved_count}`
      );
      await loadAlerts();
    } catch (error) {
      if (el.forceSubmitResult) {
        el.forceSubmitResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  async function loadAlerts() {
    try {
      const examId = currentExamId();
      const data = await api(
        `/admin/proctor/alerts?exam_id=${encodeURIComponent(examId)}&limit=300`,
        { headers: adminHeaders() }
      );
      renderAlerts(data.alerts || []);
      setStatus(`Loaded ${data.count} alert(s).`);
    } catch (error) {
      if (el.forceSubmitResult) {
        el.forceSubmitResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  async function alertAction(alertId, resolve) {
    try {
      const path = resolve
        ? `/admin/proctor/alerts/${encodeURIComponent(alertId)}/resolve`
        : `/admin/proctor/alerts/${encodeURIComponent(alertId)}/acknowledge`;
      await api(path, {
        method: "POST",
        headers: adminHeaders(),
        body: resolve ? { note: "resolved_from_admin_ui" } : undefined,
      });
      await loadAlerts();
    } catch (error) {
      if (el.broadcastResult) {
        el.broadcastResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  async function forceSubmitAttempt() {
    try {
      const attemptId = (el.forceAttemptId.value || "").trim();
      if (!attemptId) {
        throw new Error("Attempt ID required for force submit.");
      }
      const data = await api(
        `/admin/attempts/${encodeURIComponent(attemptId)}/force-submit`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: { reason: "emergency_manual_force_submit" },
        }
      );
      el.forceSubmitResult.textContent = JSON.stringify(data, null, 2);
      setStatus(`Attempt ${attemptId} force submitted.`);
      await refreshLive();
      await loadAlerts();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function forceSubmitExpired() {
    try {
      const examId = currentExamId(true);
      const query = new URLSearchParams({ limit: "1000" });
      if (examId) {
        query.set("exam_id", examId);
      }
      const data = await api(
        `/admin/attempts/force-submit-expired?${query.toString()}`,
        {
          method: "POST",
          headers: adminHeaders(),
        }
      );
      el.forceSubmitResult.textContent = JSON.stringify(data, null, 2);
      setStatus(
        `Expired force-submit complete: processed=${data.processed_count}, finalized=${data.finalized_count}, failed=${data.failed_count}.`
      );
      await refreshLive();
      await loadAlerts();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function pauseExam() {
    try {
      const examId = currentExamId();
      const reason = (el.examControlReason.value || "").trim();
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/pause?limit=2000`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: reason ? { reason } : {},
        }
      );
      el.forceSubmitResult.textContent = JSON.stringify(data, null, 2);
      setStatus(`Exam paused. paused=${data.paused_count}, failed=${data.failed_count}.`);
      await refreshLive();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function resumeExam() {
    try {
      const examId = currentExamId();
      const reason = (el.examControlReason.value || "").trim();
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/resume?limit=2000`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: reason ? { reason } : {},
        }
      );
      el.forceSubmitResult.textContent = JSON.stringify(data, null, 2);
      setStatus(`Exam resumed. resumed=${data.resumed_count}, failed=${data.failed_count}.`);
      await refreshLive();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function sendBroadcast() {
    try {
      const examId = currentExamId();
      const message = (el.broadcastMessage.value || "").trim();
      if (!message) {
        throw new Error("Broadcast message required.");
      }
      const severity = el.broadcastSeverity.value || "info";
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/broadcast`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: { message, severity },
        }
      );
      const auditCheck = await api(
        `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&event_type=EXAM_BROADCAST&limit=1`,
        { headers: adminHeaders() }
      );
      if (!auditCheck.count) {
        throw new Error("Broadcast was sent but audit verification failed.");
      }
      el.broadcastResult.textContent = JSON.stringify(data, null, 2);
      el.broadcastMessage.value = "";
      setStatus(`Broadcast sent (${severity}) to exam candidates.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadAuditEvents() {
    try {
      const query = new URLSearchParams({
        limit: "300",
      });
      const entityType = (el.auditEntityType.value || "").trim();
      const entityId = (el.auditEntityId.value || "").trim();
      const eventType = (el.auditEventType.value || "").trim();
      const actorId = (el.auditActorId.value || "").trim();
      if (entityType) {
        query.set("entity_type", entityType);
      }
      if (entityId) {
        query.set("entity_id", entityId);
      }
      if (eventType) {
        query.set("event_type", eventType);
      }
      if (actorId) {
        query.set("actor_id", actorId);
      }
      const data = await api(`/admin/audit/events?${query.toString()}`, {
        headers: adminHeaders(),
      });
      renderAuditEvents(data.events || []);
      setStatus(`Loaded ${Number(data.count || 0)} audit event(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function pullEvents() {
    try {
      const examId = currentExamId();
      const query = new URLSearchParams({
        exam_id: examId,
        limit: "100",
      });
      if (st.cursor) {
        query.set("cursor", st.cursor);
      }
      const data = await api(`/admin/proctor/events?${query.toString()}`, {
        headers: adminHeaders(),
      });
      renderEvents(data.events || []);
      st.cursor = data.next_cursor || st.cursor;
      el.cursorLabel.textContent = st.cursor || "none";
      setStatus(`Fetched ${(data.events || []).length} event(s) with cursor pagination.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function toggleAutoPolling() {
    if (st.polling) {
      st.polling = false;
      if (st.pollTimerId) {
        clearInterval(st.pollTimerId);
      }
      st.pollTimerId = null;
      el.toggleAuto.textContent = "Start Auto Poll";
      setStatus("Auto polling stopped.");
      return;
    }
    st.polling = true;
    st.pollTimerId = window.setInterval(() => {
      pullEvents();
    }, 3000);
    el.toggleAuto.textContent = "Stop Auto Poll";
    setStatus("Auto polling started (3s interval).");
  }

  function getSelectedFile(input) {
    const file = input.files?.[0];
    if (!file) {
      throw new Error("Select CSV file first");
    }
    return file;
  }

  async function uploadQuestionCsv() {
    try {
      const file = getSelectedFile(el.questionCsvFile);
      const formData = new FormData();
      formData.append("file", file);
      const data = await api("/admin/questions/import-csv", {
        method: "POST",
        headers: adminHeaders(),
        body: formData,
      });
      el.questionUploadResult.textContent = JSON.stringify(data, null, 2);
      setStatus("Question bank CSV imported.");
      await loadQuestions();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function uploadExamPack() {
    try {
      const file = getSelectedFile(el.examPackFile);
      const formData = new FormData();
      formData.append("file", file);
      const data = await api("/admin/exams/import-question-pack-csv", {
        method: "POST",
        headers: adminHeaders(),
        body: formData,
      });
      el.examPackResult.textContent = JSON.stringify(data, null, 2);
      setStatus("Exam package CSV imported.");
      await loadExams();
      el.examSelect.value = data.exam_id;
      await loadQuestions();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadQuestions() {
    try {
      const data = await api("/admin/questions", { headers: adminHeaders() });
      st.questionMap = new Map(data.map((question) => [question.id, question]));
      el.questionCount.textContent = String(data.length);
      if (!data.length) {
        el.questionsBody.innerHTML = '<tr><td colspan="6" class="small">No questions available.</td></tr>';
        el.studentPreviewBox.innerHTML = '<p class="small">No preview selected.</p>';
        return;
      }
      el.questionsBody.innerHTML = data
        .map(
          (question) => `
            <tr>
              <td class="mono">${esc(question.id)}</td>
              <td>${esc(question.text)}</td>
              <td>${esc(question.topic)}</td>
              <td>${esc(question.difficulty)}</td>
              <td>${esc(question.marks)}</td>
              <td><button class="alt js-preview-question" data-question-id="${esc(question.id)}">Preview</button></td>
            </tr>
          `
        )
        .join("");
      setStatus(`Loaded ${data.length} question(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function renderStudentPreview(questionId) {
    const question = st.questionMap.get(questionId);
    if (!question) {
      setStatus("Question not found for preview.");
      return;
    }
    const options = Array.isArray(question.options) ? question.options : [];
    el.studentPreviewBox.innerHTML = `
      <div class="small">Student View Preview</div>
      <h3>${esc(question.text)}</h3>
      <p class="small">Topic: ${esc(question.topic)} | Difficulty: ${esc(question.difficulty)} | Marks: ${esc(question.marks)}</p>
      <div class="stack">
        ${options
          .map(
            (option, index) => `
              <label class="row option">
                <input type="radio" disabled>
                <span>${esc(String.fromCharCode(65 + index))}. ${esc(option.option_text)}</span>
              </label>
            `
          )
          .join("")}
      </div>
    `;
    setStatus(`Preview loaded for question ${questionId}.`);
  }

  function renderStudentIds(rows) {
    if (!rows.length) {
      el.studentsBody.innerHTML = '<tr><td colspan="5" class="small">No student IDs created yet.</td></tr>';
      return;
    }
    el.studentsBody.innerHTML = rows
      .map(
        (student) => `
          <tr>
            <td class="mono">${esc(student.student_id)}</td>
            <td>${esc(student.display_name || "-")}</td>
            <td>${esc(student.created_by || "-")}</td>
            <td>${esc(formatDate(student.created_at))}</td>
            <td>${esc(student.status || "-")}</td>
          </tr>
        `
      )
      .join("");
  }

  async function loadStudentIds() {
    try {
      const data = await api("/admin/students?limit=500", { headers: adminHeaders() });
      renderStudentIds(data.students || []);
      setStatus(`Loaded ${Number(data.count || 0)} student ID(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function createStudentId() {
    try {
      const studentId = el.studentIdInput.value.trim();
      const displayName = el.studentNameInput.value.trim();
      if (!studentId) {
        throw new Error("Student ID required");
      }
      const data = await api("/admin/students/register", {
        method: "POST",
        headers: adminHeaders(),
        body: {
          student_id: studentId,
          display_name: displayName || null,
        },
      });
      el.studentIdResult.textContent = JSON.stringify(data, null, 2);
      el.studentIdInput.value = "";
      el.studentNameInput.value = "";
      await loadStudentIds();
      setStatus(`Student ID '${data.student_id}' created.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function generateStudentIds() {
    try {
      const prefix = el.studentPrefix.value.trim() || "cadet";
      const count = Number(el.studentCount.value || "10");
      const data = await api("/admin/students/generate", {
        method: "POST",
        headers: adminHeaders(),
        body: { prefix, count },
      });
      el.studentIdResult.textContent = JSON.stringify(data, null, 2);
      await loadStudentIds();
      setStatus(`Generated ${data.generated_count} student ID(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function uploadStudentCsv() {
    try {
      const file = getSelectedFile(el.studentCsvFile);
      const formData = new FormData();
      formData.append("file", file);
      const data = await api("/admin/students/import-csv", {
        method: "POST",
        headers: adminHeaders(),
        body: formData,
      });
      el.studentCsvResult.textContent = JSON.stringify(data, null, 2);
      await loadStudentIds();
      setStatus(
        `Student CSV processed. Inserted ${data.inserted}, failed ${data.failed}.`
      );
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function exportStudentCsv() {
    try {
      const response = await fetch("/admin/students/export-csv?limit=2000", {
        headers: adminHeaders(),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
      }

      const content = await response.text();
      const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "student_accounts.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);

      el.studentCsvResult.textContent =
        "Student export ready: downloaded student_accounts.csv";
      setStatus("Student CSV export downloaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function renderRuns(runs) {
    if (!runs.length) {
      el.runsBody.innerHTML = '<tr><td colspan="7" class="small">No recalibration runs.</td></tr>';
      return;
    }
    el.runsBody.innerHTML = runs
      .map(
        (run) => `
          <tr>
            <td>${esc(formatDate(run.created_at))}</td>
            <td class="mono">${esc(run.run_id)}</td>
            <td>${esc(run.mode)}</td>
            <td>${esc(String(run.updated_questions))}</td>
            <td>${esc(String(run.eligible_questions))}</td>
            <td class="mono">${esc(run.source_run_id || "-")}</td>
            <td>
              <button class="alt js-view-run" data-run-id="${esc(run.run_id)}">View</button>
              <button class="warn js-rollback-run" data-run-id="${esc(run.run_id)}" ${run.mode === "apply" ? "" : "disabled"}>Rollback</button>
            </td>
          </tr>
        `
      )
      .join("");
  }

  function renderRunItems(items) {
    if (!items.length) {
      el.itemsBody.innerHTML = '<tr><td colspan="6" class="small">No run items.</td></tr>';
      return;
    }
    el.itemsBody.innerHTML = items
      .map(
        (item) => `
          <tr>
            <td class="mono">${esc(item.question_id)}</td>
            <td>${esc(String(item.total_attempts ?? 0))}</td>
            <td>${esc(Number(item.observed_difficulty_index ?? 0).toFixed(2))}</td>
            <td>${esc(`${item.current?.difficulty ?? "-"} / L${item.current?.difficulty_level ?? "-"} / D${item.current?.discrimination_index ?? "-"}`)}</td>
            <td>${esc(`${item.suggested?.difficulty ?? "-"} / L${item.suggested?.difficulty_level ?? "-"} / D${item.suggested?.discrimination_index ?? "-"}`)}</td>
            <td>${esc(item.status)}</td>
          </tr>
        `
      )
      .join("");
  }

  async function runRecalibration() {
    try {
      const examId = currentExamId();
      const minAttempts = Number(el.minAttempts.value || "1");
      if (Number.isNaN(minAttempts) || minAttempts < 1) {
        throw new Error("min_attempts must be >= 1");
      }
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/questions/recalibrate`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: {
            min_attempts: minAttempts,
            apply: Boolean(el.applyRun.checked),
          },
        }
      );
      el.runSummary.textContent = JSON.stringify(
        {
          run_id: data.run_id,
          mode: data.mode,
          total_questions: data.total_questions,
          eligible_questions: data.eligible_questions,
          updated_questions: data.updated_questions,
          skipped_questions: data.skipped_questions,
        },
        null,
        2
      );
      setStatus(`Recalibration ${data.mode} run completed.`);
      await loadHistory();
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadHistory() {
    try {
      const examId = currentExamId();
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/questions/recalibration-runs?limit=200`,
        {
          headers: adminHeaders(),
        }
      );
      renderRuns(data.runs || []);
      setStatus(`Loaded ${(data.runs || []).length} recalibration run(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function viewRun(runId) {
    try {
      const examId = currentExamId();
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/questions/recalibration-runs/${encodeURIComponent(runId)}`,
        {
          headers: adminHeaders(),
        }
      );
      renderRunItems(data.items || []);
      setStatus(`Loaded run ${runId}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function rollbackRun(runId) {
    try {
      const examId = currentExamId();
      const reason = el.rollbackReason.value.trim();
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/questions/recalibration-runs/${encodeURIComponent(runId)}/rollback`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: reason ? { reason } : {},
        }
      );
      el.runSummary.textContent = JSON.stringify(
        {
          run_id: data.run_id,
          source_run_id: data.source_run_id,
          updated_questions: data.updated_questions,
          reason: data.reason,
        },
        null,
        2
      );
      setStatus(`Rollback completed for source run ${runId}.`);
      await loadHistory();
      await viewRun(data.run_id);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadAnalytics() {
    try {
      const examId = currentExamId();
      const [summary, difficulty, topic, distribution] = await Promise.all([
        api(`/admin/exams/${encodeURIComponent(examId)}/analytics`, {
          headers: adminHeaders(),
        }),
        api(`/admin/exams/${encodeURIComponent(examId)}/analytics/difficulty-heatmap`, {
          headers: adminHeaders(),
        }),
        api(`/admin/exams/${encodeURIComponent(examId)}/analytics/topic-heatmap`, {
          headers: adminHeaders(),
        }),
        api(`/admin/exams/${encodeURIComponent(examId)}/analytics/score-distribution`, {
          headers: adminHeaders(),
        }),
      ]);

      el.analyticsSummary.textContent = JSON.stringify(summary, null, 2);

      const difficultyCells = difficulty.cells || [];
      el.difficultyBody.innerHTML = difficultyCells.length
        ? difficultyCells
            .map(
              (cell) => {
                const totalAttempts = Number(cell.total_attempts || 0);
                const difficultyIndex = Number(cell.difficulty_index || 0);
                const correctCount = Math.round((totalAttempts * difficultyIndex) / 100);
                return `
                <tr>
                  <td class="mono">${esc(cell.question_id)}</td>
                  <td>${esc(difficultyIndex.toFixed(2))}</td>
                  <td>${esc(String(totalAttempts))}</td>
                  <td>${esc(String(correctCount))}</td>
                </tr>
              `;
              }
            )
            .join("")
        : '<tr><td colspan="4" class="small">No difficulty heatmap data.</td></tr>';

      const topicCells = topic.cells || [];
      el.topicBody.innerHTML = topicCells.length
        ? topicCells
            .map(
              (cell) => `
                <tr>
                  <td>${esc(cell.topic_tag)}</td>
                  <td>${esc(String(cell.total_attempts || 0))}</td>
                  <td>${esc(Number(cell.average_score || 0).toFixed(2))}</td>
                  <td>${esc(Number(cell.performance_index || 0).toFixed(2))}</td>
                </tr>
              `
            )
            .join("")
        : '<tr><td colspan="4" class="small">No topic heatmap data.</td></tr>';

      const buckets = distribution.buckets || [];
      const maxCount = Math.max(1, ...buckets.map((bucket) => Number(bucket.count || 0)));
      el.distributionBody.innerHTML = buckets.length
        ? buckets
            .map((bucket) => {
              const count = Number(bucket.count || 0);
              const width = Math.round((count / maxCount) * 100);
              return `
                <div class="dist-row">
                  <span class="mono">${esc(bucket.label)}</span>
                  <div class="dist-bar"><div style="width:${width}%"></div></div>
                  <span class="mono">${esc(count)}</span>
                </div>
              `;
            })
            .join("")
        : '<p class="small">No distribution data.</p>';

      setStatus("Analytics loaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function updateInfraHealthSummary() {
    const metrics = st.latestMetrics || {};
    const dashboard = st.latestDashboard || {};
    const requestRows = Array.isArray(metrics.request_duration_ms)
      ? metrics.request_duration_ms
      : [];
    const requestCount = requestRows.reduce(
      (acc, row) => acc + Number(row.count || 0),
      0
    );
    const requestTotal = requestRows.reduce(
      (acc, row) => acc + Number(row.total_value || 0),
      0
    );
    const avgLatency = requestCount > 0 ? requestTotal / requestCount : 0;

    const conflictRows = Array.isArray(metrics.concurrency_conflict_count)
      ? metrics.concurrency_conflict_count
      : [];
    const conflictCount = conflictRows.reduce(
      (acc, row) => acc + Number(row.count || 0),
      0
    );

    const activeAttempts = Number(dashboard.active_attempt_count || 0);
    const suspiciousAttempts = Number(dashboard.suspicious_attempt_count || 0);
    const health =
      activeAttempts > 0 && suspiciousAttempts / activeAttempts > 0.3
        ? "Watch"
        : avgLatency > 1500 || conflictCount > 0
          ? "Degraded"
          : "Healthy";

    el.infraHealthBox.innerHTML = `
      <div><strong>Infra Health: ${esc(health)}</strong></div>
      <div>Avg API latency: ${esc(avgLatency.toFixed(2))} ms</div>
      <div>Concurrency conflicts: ${esc(String(conflictCount))}</div>
      <div>Active attempts: ${esc(String(activeAttempts))}</div>
      <div>Suspicious attempts: ${esc(String(suspiciousAttempts))}</div>
      <div>Snapshot time: ${esc(formatDate(dashboard.as_of))}</div>
    `;
  }

  async function loadMetrics() {
    try {
      const metrics = await api("/admin/system/metrics", { headers: adminHeaders() });
      st.latestMetrics = metrics;
      el.metricsBox.textContent = JSON.stringify(metrics, null, 2);
      updateInfraHealthSummary();
      setStatus("System metrics loaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadGlobalDashboard() {
    try {
      const dashboard = await api("/admin/proctor/dashboard?active_limit=200&finalize_limit=50", {
        headers: adminHeaders(),
      });
      st.latestDashboard = dashboard;
      el.dashboardBox.textContent = JSON.stringify(dashboard, null, 2);
      updateInfraHealthSummary();
      setStatus("Global proctor snapshot loaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function updateIdleTimeoutPolicy() {
    const secondsInput = el.idleTimeoutSeconds?.value || "10";
    const timeoutMs = normalizeIdleTimeoutMs(secondsInput);
    applyIdleTimeoutPolicy(timeoutMs, true);
    setStatus(`Idle timeout policy updated to ${Math.round(timeoutMs / 1000)} seconds.`);
  }

  function bindClick(element, handler) {
    if (!element) {
      return;
    }
    element.addEventListener("click", handler);
  }

  function bindEvents() {
    bindClick(el.logoutAdmin, logoutAdmin);
    if (el.guidedToggle) {
      el.guidedToggle.addEventListener("change", () => {
        applyGuidedMode(el.guidedToggle.checked);
      });
    }
    el.navButtons.forEach((button) => {
      button.addEventListener("click", () => {
        activatePage(button.dataset.page);
      });
    });
    bindClick(el.loadExams, loadExams);
    if (el.examSelect) {
      el.examSelect.addEventListener("change", () => {
        st.cursor = null;
        st.seenEventIds.clear();
        el.cursorLabel.textContent = "none";
        el.eventsBody.innerHTML = "";
      });
    }

    bindClick(el.refreshLive, refreshLive);
    bindClick(el.syncAlerts, syncAlerts);
    bindClick(el.loadAlerts, loadAlerts);
    bindClick(el.forceSubmitAttempt, forceSubmitAttempt);
    bindClick(el.forceSubmitExpired, forceSubmitExpired);
    bindClick(el.pauseExam, pauseExam);
    bindClick(el.emergencyStop, pauseExam);
    bindClick(el.resumeExam, resumeExam);
    bindClick(el.sendBroadcast, sendBroadcast);
    bindClick(el.pullEvents, pullEvents);
    bindClick(el.toggleAuto, toggleAutoPolling);
    bindClick(el.loadAuditEvents, loadAuditEvents);

    el.alertBody.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const alertId = target.getAttribute("data-alert-id");
      if (!alertId) {
        return;
      }
      if (target.classList.contains("js-ack")) {
        alertAction(alertId, false);
      }
      if (target.classList.contains("js-resolve")) {
        alertAction(alertId, true);
      }
    });

    bindClick(el.uploadQuestionCsv, uploadQuestionCsv);
    bindClick(el.uploadExamPack, uploadExamPack);
    bindClick(el.loadQuestions, loadQuestions);
    bindClick(el.createStudentId, createStudentId);
    bindClick(el.generateStudentIds, generateStudentIds);
    bindClick(el.refreshStudentIds, loadStudentIds);
    bindClick(el.uploadStudentCsv, uploadStudentCsv);
    bindClick(el.exportStudentCsv, exportStudentCsv);

    bindClick(el.runRecalibration, runRecalibration);
    bindClick(el.loadHistory, loadHistory);
    el.runsBody.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const runId = target.getAttribute("data-run-id");
      if (!runId) {
        return;
      }
      if (target.classList.contains("js-view-run")) {
        viewRun(runId);
      }
      if (target.classList.contains("js-rollback-run")) {
        rollbackRun(runId);
      }
    });

    bindClick(el.loadAnalytics, loadAnalytics);
    bindClick(el.loadMetrics, loadMetrics);
    bindClick(el.loadDashboard, loadGlobalDashboard);
    bindClick(el.applyIdleTimeout, updateIdleTimeoutPolicy);

    el.questionsBody.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const questionId = target.getAttribute("data-question-id");
      if (!questionId) {
        return;
      }
      if (target.classList.contains("js-preview-question")) {
        renderStudentPreview(questionId);
      }
    });

    window.addEventListener("beforeunload", () => {
      if (st.pollTimerId) {
        clearInterval(st.pollTimerId);
      }
      if (st.idleTimerId) {
        clearTimeout(st.idleTimerId);
      }
    });
  }

  function seedTables() {
    el.activeBody.innerHTML = '<tr><td colspan="5" class="small">No active attempts.</td></tr>';
    el.alertBody.innerHTML = '<tr><td colspan="6" class="small">No alerts.</td></tr>';
    el.eventsBody.innerHTML = '<tr><td colspan="5" class="small">No events yet.</td></tr>';
    el.auditEventsBody.innerHTML = '<tr><td colspan="5" class="small">No audit events for current filter.</td></tr>';
    el.questionsBody.innerHTML = '<tr><td colspan="6" class="small">No questions available.</td></tr>';
    el.studentsBody.innerHTML = '<tr><td colspan="5" class="small">No student IDs created yet.</td></tr>';
    el.runsBody.innerHTML = '<tr><td colspan="7" class="small">No recalibration runs.</td></tr>';
    el.itemsBody.innerHTML = '<tr><td colspan="6" class="small">No run items.</td></tr>';
    el.difficultyBody.innerHTML = '<tr><td colspan="4" class="small">No difficulty heatmap data.</td></tr>';
    el.topicBody.innerHTML = '<tr><td colspan="4" class="small">No topic heatmap data.</td></tr>';
    el.distributionBody.innerHTML = '<p class="small">No distribution data.</p>';
    if (el.forceSubmitResult) {
      el.forceSubmitResult.textContent = "Force-submit output will appear here.";
    }
    if (el.broadcastResult) {
      el.broadcastResult.textContent = "Broadcast output will appear here.";
    }
    if (el.studentPreviewBox) {
      el.studentPreviewBox.innerHTML = '<p class="small">No preview selected.</p>';
    }
    if (el.studentCsvResult) {
      el.studentCsvResult.textContent = "Student CSV import/export result will appear here.";
    }
    if (el.infraHealthBox) {
      el.infraHealthBox.textContent = "Infra health summary will appear here.";
    }
  }

  ensureAdminSession();
  applyIdleTimeoutPolicy(readIdleTimeoutPolicy(), false);
  applyGuidedMode(readGuidedMode());
  activatePage("page-monitor");
  seedTables();
  bindEvents();
  bindIdleActivityListeners();
  loadVersion();
  loadExams();
  loadQuestions();
  loadStudentIds();
  loadMetrics();
  loadGlobalDashboard();
})();
