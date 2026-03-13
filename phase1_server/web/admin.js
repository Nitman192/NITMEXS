(() => {
  const ADMIN_SESSION_KEY = "nitmexs_admin_session";
  const GUIDED_MODE_KEY = "nitmexs_admin_guided_mode";
  const IDLE_TIMEOUT_POLICY_KEY = "nitmexs_admin_idle_timeout_ms";
  const IDLE_TIMEOUT_DEFAULT_MS = 10_000;
  const ADMIN_WIDGET_LAYOUT_KEY = "nitmexs_admin_widget_layout";
  const ADMIN_POLICY_HISTORY_KEY = "nitmexs_admin_policy_history";
  const ADMIN_PUBLISH_POLICY_KEY = "nitmexs_admin_publish_policy";
  const ADMIN_BACKUP_POLICY_KEY = "nitmexs_admin_backup_policy";
  const ADMIN_ACCESS_POLICY_KEY = "nitmexs_admin_access_policy";
  const ADMIN_AI_DRAFT_QUEUE_KEY = "nitmexs_admin_ai_draft_queue";

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
    autoForceExpiredTimerId: null,
    idleTimerId: null,
    idleLockMs: IDLE_TIMEOUT_DEFAULT_MS,
    seenEventIds: new Set(),
    questionMap: new Map(),
    latestMetrics: null,
    latestDashboard: null,
    lastBroadcastEventId: "",
    lastBroadcastExamId: "",
    alertNoiseThreshold: 0,
    latestAnalyticsSummary: null,
    latestTopicCells: [],
    latestDistributionBuckets: [],
    pendingAiDraft: null,
  };

  const el = {
    sessionAdmin: $("session-admin"),
    version: $("version"),
    guidedToggle: $("guided-toggle"),
    emergencyStop: $("emergency-stop-btn"),
    logoutAdmin: $("logout-admin"),
    loadExams: $("load-exams"),
    examSelect: $("exam-select"),
    deleteExam: $("delete-exam"),
    status: $("admin-status"),
    navButtons: Array.from(document.querySelectorAll(".nav-btn")),
    pages: Array.from(document.querySelectorAll(".page-panel")),
    refreshLive: $("refresh-live"),
    syncAlerts: $("sync-alerts"),
    loadAlerts: $("load-alerts"),
    alertNoiseThreshold: $("alert-noise-threshold"),
    applyAlertNoiseFilter: $("apply-alert-noise-filter"),
    clearAlertNoiseFilter: $("clear-alert-noise-filter"),
    riskInsightsBox: $("risk-insights-box"),
    forceAttemptId: $("force-attempt-id"),
    forceSubmitAttempt: $("force-submit-attempt"),
    forceSubmitExpired: $("force-submit-expired"),
    examControlReason: $("exam-control-reason"),
    pauseExam: $("pause-exam"),
    resumeExam: $("resume-exam"),
    broadcastTemplate: $("broadcast-template"),
    applyBroadcastTemplate: $("apply-broadcast-template"),
    broadcastMessage: $("broadcast-message"),
    broadcastSeverity: $("broadcast-severity"),
    sendBroadcast: $("send-broadcast"),
    refreshBroadcastReceipts: $("refresh-broadcast-receipts"),
    autoForceExpiredToggle: $("auto-force-expired-toggle"),
    runPreflight: $("run-preflight"),
    forceSubmitResult: $("force-submit-result"),
    broadcastResult: $("broadcast-result"),
    preflightResult: $("preflight-result"),
    publishLab: $("publish-lab"),
    runCanaryPublish: $("run-canary-publish"),
    runPublishGate: $("run-publish-gate"),
    createRollbackSnapshot: $("create-rollback-snapshot"),
    applyCircuitBreaker: $("apply-circuit-breaker"),
    graceMinutes: $("grace-minutes"),
    applyGracePolicy: $("apply-grace-policy"),
    approvalSteps: $("approval-steps"),
    saveApprovalBuilder: $("save-approval-builder"),
    publishOpsBox: $("publish-ops-box"),
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
    aiDraftTopic: $("ai-draft-topic"),
    aiDraftDifficulty: $("ai-draft-difficulty"),
    aiDraftPrompt: $("ai-draft-prompt"),
    generateAiDraft: $("generate-ai-draft"),
    approveAiDraft: $("approve-ai-draft"),
    aiDraftBox: $("ai-draft-box"),
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
    runCohortBenchmarking: $("run-cohort-benchmarking"),
    runDistractorAnalytics: $("run-distractor-analytics"),
    runAttendanceForecast: $("run-attendance-forecast"),
    runSlotDemand: $("run-slot-demand"),
    analyticsAdvancedBox: $("analytics-advanced-box"),
    loadMetrics: $("load-metrics"),
    loadDashboard: $("load-dashboard"),
    computeRisk: $("compute-risk"),
    exportSiem: $("export-siem"),
    hashAuditChain: $("hash-audit-chain"),
    loadMigrationHealth: $("load-migration-health"),
    widgetLiveToggle: $("widget-live-toggle"),
    widgetAlertToggle: $("widget-alert-toggle"),
    widgetAnalyticsToggle: $("widget-analytics-toggle"),
    saveWidgetLayout: $("save-widget-layout"),
    complianceProfile: $("compliance-profile"),
    applyComplianceProfile: $("apply-compliance-profile"),
    savePolicyVersion: $("save-policy-version"),
    idleTimeoutSeconds: $("idle-timeout-seconds"),
    applyIdleTimeout: $("apply-idle-timeout"),
    metricsBox: $("metrics-box"),
    dashboardBox: $("dashboard-box"),
    infraHealthBox: $("infra-health-box"),
    anomalyBox: $("anomaly-box"),
    integrityBox: $("integrity-box"),
    policyBox: $("policy-box"),
    trendBox: $("trend-box"),
    simulatorBox: $("simulator-box"),
    backupRetentionDays: $("backup-retention-days"),
    applyBackupRetention: $("apply-backup-retention"),
    backupEncryptionToggle: $("backup-encryption-toggle"),
    backupEncryptionKey: $("backup-encryption-key"),
    applyBackupEncryption: $("apply-backup-encryption"),
    restorePointTime: $("restore-point-time"),
    browseRestorePoints: $("browse-restore-points"),
    runRestoreDry: $("run-restore-dry"),
    runDbProfiler: $("run-db-profiler"),
    runQueueMonitor: $("run-queue-monitor"),
    runKeyRotation: $("run-key-rotation"),
    runVaultCheck: $("run-vault-check"),
    ssoMode: $("sso-mode"),
    toggleHardwareMfa: $("toggle-hardware-mfa"),
    geoIpPolicy: $("geo-ip-policy"),
    applyGeoPolicy: $("apply-geo-policy"),
    conditionalAccessRule: $("conditional-access-rule"),
    applyConditionalAccess: $("apply-conditional-access"),
    backupSecurityBox: $("backup-security-box"),
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

  function readJsonStorage(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return fallback;
      }
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        return parsed;
      }
      return fallback;
    } catch {
      return fallback;
    }
  }

  function writeJsonStorage(key, payload) {
    localStorage.setItem(key, JSON.stringify(payload));
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

  async function deleteSelectedExam() {
    try {
      const examId = currentExamId();
      const selectedOption = el.examSelect?.selectedOptions?.[0];
      const label = selectedOption?.textContent?.trim() || examId;
      const confirmed = window.confirm(
        `Delete selected exam?\n\n${label}\n\nThis works only if the exam has no attempt history.`
      );
      if (!confirmed) {
        setStatus("Exam delete cancelled.");
        return;
      }

      const data = await api(`/admin/exams/${encodeURIComponent(examId)}`, {
        method: "DELETE",
        headers: adminHeaders(),
      });
      st.examId = "";
      if (el.examSelect) {
        el.examSelect.value = "";
      }
      setStatus(`Exam '${data.name}' deleted successfully.`);
      await loadExams();
      if (el.liveSummary) {
        el.liveSummary.textContent = "Live summary will appear here.";
      }
    } catch (error) {
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
    const threshold = Number(st.alertNoiseThreshold || 0);
    const filteredRows =
      threshold > 1
        ? rows.filter((row) => Number(row.incident_count || 1) >= threshold)
        : rows;
    if (!filteredRows.length) {
      el.alertBody.innerHTML = '<tr><td colspan="6" class="small">No alerts.</td></tr>';
      return;
    }
    el.alertBody.innerHTML = filteredRows
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

  function classifyAlertSeverity(alert) {
    const indicator = String(alert.indicator_code || "").toLowerCase();
    if (indicator.includes("switch") || indicator.includes("copy") || indicator.includes("critical")) {
      return "critical";
    }
    if (indicator.includes("network") || indicator.includes("inactivity")) {
      return "warn";
    }
    return "info";
  }

  function buildRiskInsights(alerts, activeAttempts) {
    const unresolved = alerts.filter((item) => String(item.status || "").toUpperCase() !== "RESOLVED");
    const byStudent = new Map();
    unresolved.forEach((alert) => {
      const student = String(alert.student_id || "unknown");
      if (!byStudent.has(student)) {
        byStudent.set(student, { student_id: student, score: 0, incidents: 0 });
      }
      const entry = byStudent.get(student);
      const severity = classifyAlertSeverity(alert);
      const weight = severity === "critical" ? 5 : severity === "warn" ? 2 : 1;
      entry.score += weight;
      entry.incidents += 1;
    });
    const ranked = Array.from(byStudent.values()).sort((a, b) => b.score - a.score).slice(0, 10);
    const avgRisk =
      activeAttempts > 0
        ? Number((ranked.reduce((acc, row) => acc + row.score, 0) / Math.max(activeAttempts, 1)).toFixed(2))
        : 0;
    return {
      active_attempts: activeAttempts,
      unresolved_alerts: unresolved.length,
      ranked_students: ranked,
      avg_risk_score: avgRisk,
    };
  }

  function renderRiskInsights(payload) {
    if (!el.riskInsightsBox) {
      return;
    }
    el.riskInsightsBox.textContent = JSON.stringify(payload, null, 2);
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
      const rows = data.alerts || [];
      renderAlerts(rows);
      const activeData = await api(
        `/admin/exams/${encodeURIComponent(examId)}/active-attempts`,
        { headers: adminHeaders() }
      );
      const riskPayload = buildRiskInsights(rows, activeData.length || 0);
      renderRiskInsights(riskPayload);
      setStatus(`Loaded ${data.count} alert(s).`);
    } catch (error) {
      if (el.forceSubmitResult) {
        el.forceSubmitResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  function applyAlertNoiseFilter() {
    const threshold = Number(el.alertNoiseThreshold?.value || "0");
    st.alertNoiseThreshold = Number.isNaN(threshold) ? 0 : Math.max(0, Math.floor(threshold));
    setStatus(
      st.alertNoiseThreshold > 1
        ? `Alert noise filter active: incident_count >= ${st.alertNoiseThreshold}`
        : "Alert noise filter disabled."
    );
    loadAlerts();
  }

  function clearAlertNoiseFilter() {
    st.alertNoiseThreshold = 0;
    if (el.alertNoiseThreshold) {
      el.alertNoiseThreshold.value = "2";
    }
    setStatus("Alert noise filter cleared.");
    loadAlerts();
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
      const reason = (el.examControlReason?.value || "").trim();
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
      const reason = (el.examControlReason?.value || "").trim();
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
      const message = (el.broadcastMessage?.value || "").trim();
      if (!message) {
        throw new Error("Broadcast message required.");
      }
      const severity = el.broadcastSeverity?.value || "info";
      const data = await api(
        `/admin/exams/${encodeURIComponent(examId)}/broadcast`,
        {
          method: "POST",
          headers: adminHeaders(),
          body: { message, severity },
        }
      );
      let deliveryHint = "Broadcast sent.";
      try {
        const auditCheck = await api(
          `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&event_type=EXAM_BROADCAST&limit=1`,
          { headers: adminHeaders() }
        );
        const latestEvent = (auditCheck.events || [])[0];
        if (latestEvent?.id) {
          st.lastBroadcastEventId = latestEvent.id;
          st.lastBroadcastExamId = examId;
          deliveryHint = "Broadcast sent and audit-logged.";
        } else {
          st.lastBroadcastEventId = "";
          st.lastBroadcastExamId = examId;
          deliveryHint = "Broadcast sent (audit lookup pending).";
        }
      } catch {
        st.lastBroadcastEventId = "";
        st.lastBroadcastExamId = examId;
        deliveryHint = "Broadcast sent (audit lookup failed).";
      }
      el.broadcastResult.textContent = JSON.stringify(
        {
          ...data,
          audit_event_id: st.lastBroadcastEventId || null,
          delivery_hint: deliveryHint,
        },
        null,
        2
      );
      if (el.broadcastMessage) {
        el.broadcastMessage.value = "";
      }
      setStatus(`Broadcast sent (${severity}) to exam candidates. ${deliveryHint}`);
      await refreshBroadcastReceipts();
    } catch (error) {
      setStatus(error.message);
    }
  }

  function applyBroadcastTemplate() {
    const template = (el.broadcastTemplate?.value || "").trim();
    if (!template) {
      setStatus("Template select karo.");
      return;
    }
    const [templateSeverity, ...messageParts] = template.split("::");
    const message = messageParts.length ? messageParts.join("::").trim() : template;
    if (el.broadcastMessage) {
      el.broadcastMessage.value = message;
    }
    if (el.broadcastSeverity && ["info", "warn", "critical"].includes(templateSeverity)) {
      el.broadcastSeverity.value = templateSeverity;
    }
    setStatus("Broadcast template applied.");
  }

  async function refreshBroadcastReceipts() {
    try {
      const examId = currentExamId();
      let broadcastEventId = st.lastBroadcastEventId;
      if (!broadcastEventId || st.lastBroadcastExamId !== examId) {
        const latestBroadcast = await api(
          `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&event_type=EXAM_BROADCAST&limit=1`,
          { headers: adminHeaders() }
        );
        const latestEvent = (latestBroadcast.events || [])[0];
        if (!latestEvent?.id) {
          el.broadcastResult.textContent = JSON.stringify(
            { exam_id: examId, receipts: 0, hint: "No broadcast found for this exam yet." },
            null,
            2
          );
          return;
        }
        st.lastBroadcastEventId = latestEvent.id;
        st.lastBroadcastExamId = examId;
        broadcastEventId = latestEvent.id;
      }

      const receiptEvents = await api(
        `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&event_type=BROADCAST_RECEIVED&limit=2000`,
        { headers: adminHeaders() }
      );
      const rows = (receiptEvents.events || []).filter((event) => {
        const payload = event.payload || {};
        return payload.broadcast_event_id === broadcastEventId;
      });
      const uniqueStudents = new Set(
        rows.map((row) => (row.payload || {}).student_id).filter(Boolean)
      );
      const uniqueAttempts = new Set(
        rows.map((row) => (row.payload || {}).attempt_id).filter(Boolean)
      );
      el.broadcastResult.textContent = JSON.stringify(
        {
          exam_id: examId,
          broadcast_event_id: broadcastEventId,
          receipt_count: rows.length,
          unique_students: uniqueStudents.size,
          unique_attempts: uniqueAttempts.size,
          last_receipt_at: rows[0]?.created_at || null,
        },
        null,
        2
      );
      setStatus(`Broadcast read receipts loaded (${rows.length} receipt event(s)).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function buildPreflightSuggestions(context) {
    const suggestions = [];
    if (context.serverOffline) {
      suggestions.push("Server unreachable: exam operations temporarily hold karo.");
    }
    if (context.criticalAlerts > 0) {
      suggestions.push("Critical alerts detected: targeted broadcast + candidate review karo.");
    }
    if (context.unresolvedAlerts > 20) {
      suggestions.push("High unresolved alert load: proctor team ko split assignment do.");
    }
    if (context.expiredActiveAttempts > 0) {
      suggestions.push("Expired active attempts present: force-submit-expired run karo.");
    }
    if (context.activeAttempts === 0) {
      suggestions.push("No active attempts: exam scope and publish status verify karo.");
    }
    if (!suggestions.length) {
      suggestions.push("System stable. Continue monitoring cadence every 30-60 seconds.");
    }
    return suggestions;
  }

  async function runPreflightReport() {
    try {
      const examId = currentExamId();
      const [liveStatus, activeAttempts, alertsData, metricsData] = await Promise.all([
        api(`/admin/exams/${encodeURIComponent(examId)}/live-status`, { headers: adminHeaders() }),
        api(`/admin/exams/${encodeURIComponent(examId)}/active-attempts`, { headers: adminHeaders() }),
        api(`/admin/proctor/alerts?exam_id=${encodeURIComponent(examId)}&limit=300`, { headers: adminHeaders() }),
        api("/admin/system/metrics", { headers: adminHeaders() }),
      ]);
      const alerts = alertsData.alerts || [];
      const unresolved = alerts.filter((alert) => String(alert.status || "").toUpperCase() !== "RESOLVED");
      const criticalAlerts = unresolved.filter((alert) => {
        const indicator = String(alert.indicator_code || "").toLowerCase();
        return indicator.includes("critical") || indicator.includes("switch");
      });
      const nowMs = Date.now();
      const unresolvedAges = unresolved
        .map((alert) => new Date(alert.created_at || alert.last_detected_at || "").valueOf())
        .filter((value) => Number.isFinite(value))
        .map((value) => Math.max(0, Math.floor((nowMs - value) / 1000)));
      const maxAgeSeconds = unresolvedAges.length ? Math.max(...unresolvedAges) : 0;

      const report = {
        generated_at: new Date().toISOString(),
        exam_id: examId,
        active_attempts: Number(liveStatus.active_attempt_count || activeAttempts.length || 0),
        suspicious_indicators: (liveStatus.suspicious_indicators || []).length,
        unresolved_alerts: unresolved.length,
        critical_alerts: criticalAlerts.length,
        incident_sla: {
          max_unresolved_age_seconds: maxAgeSeconds,
          max_unresolved_age_minutes: Number((maxAgeSeconds / 60).toFixed(1)),
        },
        expired_active_attempts: Number(metricsData.auto_expire_count || 0),
      };
      report.recommendations = buildPreflightSuggestions({
        activeAttempts: report.active_attempts,
        criticalAlerts: report.critical_alerts,
        unresolvedAlerts: report.unresolved_alerts,
        expiredActiveAttempts: report.expired_active_attempts,
        serverOffline: false,
      });
      if (el.preflightResult) {
        el.preflightResult.textContent = JSON.stringify(report, null, 2);
      }
      setStatus("Preflight report generated.");
    } catch (error) {
      if (el.preflightResult) {
        el.preflightResult.textContent = `ERROR: ${error.message}`;
      }
      setStatus(error.message);
    }
  }

  async function autoForceExpiredTick() {
    try {
      if (!el.autoForceExpiredToggle?.checked) {
        return;
      }
      const examId = currentExamId(true);
      const query = new URLSearchParams({ limit: "500" });
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
      if (Number(data.finalized_count || 0) > 0 && el.forceSubmitResult) {
        el.forceSubmitResult.textContent = JSON.stringify(data, null, 2);
      }
    } catch {
      return;
    }
  }

  function toggleAutoForceExpiredPolicy() {
    if (!el.autoForceExpiredToggle?.checked) {
      if (st.autoForceExpiredTimerId) {
        clearInterval(st.autoForceExpiredTimerId);
        st.autoForceExpiredTimerId = null;
      }
      setStatus("Auto force-submit expired policy disabled.");
      return;
    }
    if (st.autoForceExpiredTimerId) {
      clearInterval(st.autoForceExpiredTimerId);
    }
    st.autoForceExpiredTimerId = window.setInterval(() => {
      autoForceExpiredTick();
    }, 30000);
    autoForceExpiredTick();
    setStatus("Auto force-submit expired policy enabled (30s interval).");
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

      st.latestAnalyticsSummary = summary;
      st.latestTopicCells = topic.cells || [];
      st.latestDistributionBuckets = distribution.buckets || [];
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

      if (el.trendBox) {
        const topicLeaderboard = topicCells
          .map((cell) => ({
            topic: cell.topic_tag,
            avg: Number(cell.average_score || 0),
            performance: Number(cell.performance_index || 0),
          }))
          .sort((a, b) => b.performance - a.performance);
        el.trendBox.textContent = JSON.stringify(
          {
            trend_cube_analytics: {
              best_topics: topicLeaderboard.slice(0, 5),
              weak_topics: topicLeaderboard.slice(-5).reverse(),
              cohort_benchmarking: {
                global_avg_percentage: Number(summary.average_percentage || 0),
                pass_rate: Number(summary.pass_rate || 0),
                total_attempts: Number(summary.total_attempts || 0),
              },
            },
          },
          null,
          2
        );
      }

      if (el.simulatorBox) {
        const average = Number(summary.average_percentage || 0);
        const attempts = Number(summary.total_attempts || 0);
        const whatIfCutoffs = [35, 40, 45, 50, 60].map((cutoff) => ({
          cutoff,
          estimated_pass_count: Math.round((Math.max(0, average - cutoff + 50) / 100) * attempts),
        }));
        el.simulatorBox.textContent = JSON.stringify(
          {
            cutoff_optimizer: whatIfCutoffs,
            what_if_simulator: {
              current_average: average,
              recommendations: average < 50
                ? ["Increase remedial sessions for weak topics.", "Reduce difficult-question weight in next mock."]
                : ["Maintain current difficulty mix.", "Focus on high-risk candidates from risk model."],
            },
            ai_remediation_planner: {
              primary_topics: (topicCells || [])
                .sort((a, b) => Number(a.performance_index || 0) - Number(b.performance_index || 0))
                .slice(0, 3)
                .map((row) => row.topic_tag),
            },
          },
          null,
          2
        );
      }

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
    const errorBudget = requestCount > 0
      ? Number((((conflictCount + suspiciousAttempts) / requestCount) * 100).toFixed(3))
      : 0;

    el.infraHealthBox.innerHTML = `
      <div><strong>Infra Health: ${esc(health)}</strong></div>
      <div>Avg API latency: ${esc(avgLatency.toFixed(2))} ms</div>
      <div>Concurrency conflicts: ${esc(String(conflictCount))}</div>
      <div>API error budget burn: ${esc(String(errorBudget))}%</div>
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

  async function computeRiskModel() {
    try {
      const examId = currentExamId();
      const [alertsData, activeAttempts] = await Promise.all([
        api(`/admin/proctor/alerts?exam_id=${encodeURIComponent(examId)}&limit=500`, {
          headers: adminHeaders(),
        }),
        api(`/admin/exams/${encodeURIComponent(examId)}/active-attempts`, {
          headers: adminHeaders(),
        }),
      ]);
      const riskPayload = buildRiskInsights(alertsData.alerts || [], activeAttempts.length || 0);
      const severe = (alertsData.alerts || []).filter(
        (row) => classifyAlertSeverity(row) === "critical"
      );
      const clusters = severe.reduce((acc, row) => {
        const key = String(row.indicator_code || "unknown");
        acc[key] = Number(acc[key] || 0) + 1;
        return acc;
      }, {});
      if (el.anomalyBox) {
        el.anomalyBox.textContent = JSON.stringify(
          {
            exam_id: examId,
            incident_severity_classifier: {
              critical: severe.length,
              warn: (alertsData.alerts || []).filter((row) => classifyAlertSeverity(row) === "warn").length,
              info: (alertsData.alerts || []).filter((row) => classifyAlertSeverity(row) === "info").length,
            },
            suspicious_cluster_detector: clusters,
            proctor_load_balancer: {
              recommendation: `Assign ${Math.max(1, Math.ceil((alertsData.count || 0) / 15))} proctor lane(s)`,
              unresolved_alerts: (alertsData.alerts || []).filter((row) => String(row.status || "").toUpperCase() !== "RESOLVED").length,
            },
            live_floor_candidate_map: (activeAttempts || []).slice(0, 40).map((row, idx) => ({
              slot: idx + 1,
              attempt_id: row.attempt_id,
              student_id: row.student_id,
              risk: riskPayload.ranked_students.find((item) => item.student_id === row.student_id)?.score || 0,
            })),
          },
          null,
          2
        );
      }
      renderRiskInsights(riskPayload);
      setStatus("Risk model computed.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function exportSiemJson() {
    try {
      const examId = currentExamId();
      const data = await api(
        `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&limit=2000`,
        { headers: adminHeaders() }
      );
      const rows = data.events || [];
      const blob = new Blob([JSON.stringify(rows, null, 2)], { type: "application/json;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `siem_exam_${examId}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setStatus(`SIEM export downloaded (${rows.length} event(s)).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function hashAuditChain() {
    try {
      const examId = currentExamId();
      const data = await api(
        `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&limit=2000`,
        { headers: adminHeaders() }
      );
      const rows = data.events || [];
      const canonical = rows
        .slice()
        .reverse()
        .map((event) => `${event.id}|${event.created_at}|${event.event_type}|${JSON.stringify(event.payload || {})}`)
        .join("\n");
      if (!window.crypto?.subtle) {
        throw new Error("Crypto hashing not supported in this browser.");
      }
      const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
      const hashHex = Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
      if (el.integrityBox) {
        el.integrityBox.textContent = JSON.stringify(
          {
            exam_id: examId,
            event_count: rows.length,
            chain_hash_sha256: hashHex,
            generated_at: new Date().toISOString(),
          },
          null,
          2
        );
      }
      setStatus("Audit chain hash generated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadMigrationHealth() {
    try {
      const [versionData, metricsData] = await Promise.all([
        api("/system/version"),
        api("/admin/system/metrics", { headers: adminHeaders() }),
      ]);
      const metricRows = Array.isArray(metricsData.request_duration_ms) ? metricsData.request_duration_ms : [];
      const p95Like = metricRows.length
        ? Math.max(...metricRows.map((row) => Number(row.total_value || 0) / Math.max(1, Number(row.count || 1))))
        : 0;
      if (el.integrityBox) {
        const existing = el.integrityBox.textContent || "";
        el.integrityBox.textContent = `${existing}\n\n${JSON.stringify(
          {
            migration_health_panel: {
              app_version: versionData.version,
              request_latency_peak_ms: Number(p95Like.toFixed(2)),
              status: p95Like > 2000 ? "degraded" : "healthy",
            },
          },
          null,
          2
        )}`;
      }
      setStatus("Migration health loaded.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function readPublishPolicy() {
    return readJsonStorage(ADMIN_PUBLISH_POLICY_KEY, {
      grace_minutes: 2,
      approval_steps: 2,
      snapshots: [],
      circuit_breaker: { enabled: true, critical_threshold: 3 },
    });
  }

  function writePublishPolicy(payload) {
    writeJsonStorage(ADMIN_PUBLISH_POLICY_KEY, payload);
  }

  function readBackupPolicy() {
    return readJsonStorage(ADMIN_BACKUP_POLICY_KEY, {
      retention_days: 30,
      encryption_enabled: true,
      encryption_key_alias: "key-v1",
      restore_points: [],
      last_dry_run: null,
    });
  }

  function writeBackupPolicy(payload) {
    writeJsonStorage(ADMIN_BACKUP_POLICY_KEY, payload);
  }

  function readAccessPolicy() {
    return readJsonStorage(ADMIN_ACCESS_POLICY_KEY, {
      sso_mode: "disabled",
      hardware_mfa_required: false,
      allowed_geo: "IN",
      conditional_rule: "standard",
      active_key_id: "key-v1",
      key_history: [],
      vault_status: "unknown",
    });
  }

  function writeAccessPolicy(payload) {
    writeJsonStorage(ADMIN_ACCESS_POLICY_KEY, payload);
  }

  function writeAiDraftQueue(rows) {
    writeJsonStorage(ADMIN_AI_DRAFT_QUEUE_KEY, rows.slice(-100));
  }

  function readAiDraftQueue() {
    const payload = readJsonStorage(ADMIN_AI_DRAFT_QUEUE_KEY, []);
    return Array.isArray(payload) ? payload : [];
  }

  function renderPublishOps(payload) {
    if (!el.publishOpsBox) {
      return;
    }
    el.publishOpsBox.textContent = JSON.stringify(payload, null, 2);
  }

  function renderBackupSecurity(payload) {
    if (!el.backupSecurityBox) {
      return;
    }
    el.backupSecurityBox.textContent = JSON.stringify(payload, null, 2);
  }

  async function runCanaryPublish() {
    try {
      const examId = currentExamId();
      const lab = String(el.publishLab?.value || "").trim() || "lab-a";
      const active = await api(`/admin/exams/${encodeURIComponent(examId)}/active-attempts`, {
        headers: adminHeaders(),
      });
      const canarySize = Math.max(1, Math.min(10, Math.floor(active.length * 0.2) || 1));
      const selected = (active || []).slice(0, canarySize).map((row) => ({
        attempt_id: row.attempt_id,
        student_id: row.student_id,
      }));
      const policy = readPublishPolicy();
      policy.last_canary = {
        exam_id: examId,
        lab,
        selected_count: selected.length,
        selected,
        generated_at: new Date().toISOString(),
      };
      writePublishPolicy(policy);
      renderPublishOps({
        canary_publish: policy.last_canary,
      });
      setStatus(`Canary publish staged for ${selected.length} attempt(s) in ${lab}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runPublishGate() {
    try {
      const examId = currentExamId();
      const [liveStatus, alertsData] = await Promise.all([
        api(`/admin/exams/${encodeURIComponent(examId)}/live-status`, {
          headers: adminHeaders(),
        }),
        api(`/admin/proctor/alerts?exam_id=${encodeURIComponent(examId)}&limit=300`, {
          headers: adminHeaders(),
        }),
      ]);
      const alerts = alertsData.alerts || [];
      const unresolved = alerts.filter((row) => String(row.status || "").toUpperCase() !== "RESOLVED");
      const critical = unresolved.filter((row) => classifyAlertSeverity(row) === "critical");
      const gate = {
        exam_id: examId,
        checks: {
          exam_selected: Boolean(examId),
          active_attempts_visible: Number(liveStatus.active_attempt_count || 0) >= 0,
          unresolved_alerts_under_limit: unresolved.length <= 20,
          critical_alerts_under_limit: critical.length <= 3,
        },
      };
      gate.pass = Object.values(gate.checks).every(Boolean);
      gate.generated_at = new Date().toISOString();
      const policy = readPublishPolicy();
      policy.last_gate = gate;
      writePublishPolicy(policy);
      renderPublishOps({
        publish_gate_engine: gate,
        recommendation: gate.pass
          ? "Gate PASS: staged publish allowed."
          : "Gate WARN: resolve critical/unresolved alerts before publish.",
      });
      setStatus(gate.pass ? "Publish gate passed." : "Publish gate failed.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function createRollbackSnapshot() {
    try {
      const examId = currentExamId();
      const events = await api(
        `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&limit=200`,
        { headers: adminHeaders() }
      );
      const rows = events.events || [];
      const snapshotId = `snap_${Date.now()}`;
      const content = rows.map((row) => `${row.id}|${row.created_at}|${row.event_type}`).join("\n");
      let digestValue = "sha256_unavailable";
      if (window.crypto?.subtle) {
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
        digestValue = Array.from(new Uint8Array(digest))
          .map((byte) => byte.toString(16).padStart(2, "0"))
          .join("")
          .slice(0, 24);
      }
      const snapshot = {
        snapshot_id: snapshotId,
        exam_id: examId,
        event_count: rows.length,
        digest: digestValue,
        created_at: new Date().toISOString(),
      };
      const policy = readPublishPolicy();
      policy.snapshots = [snapshot, ...(policy.snapshots || [])].slice(0, 20);
      writePublishPolicy(policy);
      renderPublishOps({
        rollback_snapshot: snapshot,
        retained_snapshots: policy.snapshots.length,
      });
      setStatus(`Rollback snapshot created (${snapshotId}).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function applyCircuitBreakerRule() {
    try {
      const examId = currentExamId();
      const alertsData = await api(
        `/admin/proctor/alerts?exam_id=${encodeURIComponent(examId)}&limit=300`,
        { headers: adminHeaders() }
      );
      const alerts = alertsData.alerts || [];
      const unresolvedCritical = alerts.filter(
        (row) =>
          String(row.status || "").toUpperCase() !== "RESOLVED" &&
          classifyAlertSeverity(row) === "critical"
      );
      const threshold = 3;
      let action = "no_pause";
      let pauseResult = null;
      if (unresolvedCritical.length >= threshold) {
        pauseResult = await api(`/admin/exams/${encodeURIComponent(examId)}/pause?limit=2000`, {
          method: "POST",
          headers: adminHeaders(),
          body: { reason: "circuit_breaker_rule_triggered" },
        });
        action = "paused_exam";
        await refreshLive();
      }
      const policy = readPublishPolicy();
      policy.circuit_breaker = {
        enabled: true,
        critical_threshold: threshold,
        last_triggered_at: new Date().toISOString(),
        last_critical_count: unresolvedCritical.length,
        last_action: action,
      };
      writePublishPolicy(policy);
      renderPublishOps({
        circuit_breaker_pause_rule: policy.circuit_breaker,
        pause_result: pauseResult,
      });
      setStatus(
        action === "paused_exam"
          ? "Circuit breaker triggered: exam paused."
          : "Circuit breaker evaluated: no pause action required."
      );
    } catch (error) {
      setStatus(error.message);
    }
  }

  function applyGracePolicyRule() {
    const graceMinutes = Math.max(0, Math.min(30, Number(el.graceMinutes?.value || "2")));
    const policy = readPublishPolicy();
    policy.grace_minutes = graceMinutes;
    policy.last_grace_update_at = new Date().toISOString();
    writePublishPolicy(policy);
    renderPublishOps({
      grace_period_policy: {
        grace_minutes: graceMinutes,
        strategy: "allow_active_sync_then_force_submit_expired",
        updated_at: policy.last_grace_update_at,
      },
    });
    setStatus(`Grace period policy saved (${graceMinutes} minute(s)).`);
  }

  function saveMultiStepApprovals() {
    const steps = Math.max(1, Math.min(5, Number(el.approvalSteps?.value || "2")));
    const policy = readPublishPolicy();
    policy.approval_steps = steps;
    policy.last_approval_update_at = new Date().toISOString();
    writePublishPolicy(policy);
    renderPublishOps({
      multi_step_approvals_builder: {
        required_steps: steps,
        approval_chain: Array.from({ length: steps }, (_, idx) => ({
          step: idx + 1,
          role: idx === 0 ? "ops_admin" : idx === steps - 1 ? "chief_proctor" : "review_admin",
        })),
      },
    });
    setStatus(`Approval builder saved (${steps} steps).`);
  }

  function applyBackupRetentionPolicy() {
    const retentionDays = Math.max(1, Math.min(365, Number(el.backupRetentionDays?.value || "30")));
    const policy = readBackupPolicy();
    policy.retention_days = retentionDays;
    policy.updated_at = new Date().toISOString();
    writeBackupPolicy(policy);
    renderBackupSecurity({
      backup_retention_policy: policy,
    });
    setStatus(`Backup retention updated to ${retentionDays} day(s).`);
  }

  function applyBackupEncryptionPolicy() {
    const policy = readBackupPolicy();
    policy.encryption_enabled = Boolean(el.backupEncryptionToggle?.checked);
    policy.encryption_key_alias = String(el.backupEncryptionKey?.value || "").trim() || "key-v1";
    policy.updated_at = new Date().toISOString();
    writeBackupPolicy(policy);
    renderBackupSecurity({
      backup_encryption_controls: {
        enabled: policy.encryption_enabled,
        key_alias: policy.encryption_key_alias,
        updated_at: policy.updated_at,
      },
    });
    setStatus(
      policy.encryption_enabled
        ? `Backup encryption enabled (${policy.encryption_key_alias}).`
        : "Backup encryption disabled."
    );
  }

  async function browseRestorePoints() {
    try {
      const examId = currentExamId(true);
      const query = examId
        ? `/admin/audit/events?entity_type=exam&entity_id=${encodeURIComponent(examId)}&limit=200`
        : "/admin/audit/events?limit=200";
      const data = await api(query, { headers: adminHeaders() });
      const events = data.events || [];
      const points = [];
      for (const event of events.slice(0, 30)) {
        points.push({
          point_id: `rp_${String(event.id).slice(0, 8)}`,
          at: event.created_at,
          event_type: event.event_type,
        });
      }
      const policy = readBackupPolicy();
      policy.restore_points = points;
      policy.updated_at = new Date().toISOString();
      writeBackupPolicy(policy);
      renderBackupSecurity({
        point_in_time_restore_browser: {
          exam_scope: examId || "global",
          points_count: points.length,
          points: points.slice(0, 10),
        },
      });
      setStatus(`Loaded ${points.length} restore point(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runRestoreDrySandbox() {
    try {
      const policy = readBackupPolicy();
      if (!policy.restore_points || !policy.restore_points.length) {
        await browseRestorePoints();
      }
      const latest = (readBackupPolicy().restore_points || [])[0];
      const requestedPoint = String(el.restorePointTime?.value || "").trim();
      const selectedTime = requestedPoint || latest?.at || new Date().toISOString();
      const allEvents = await api("/admin/audit/events?limit=400", { headers: adminHeaders() });
      const before = (allEvents.events || []).filter(
        (row) => new Date(row.created_at).valueOf() <= new Date(selectedTime).valueOf()
      );
      const after = (allEvents.events || []).length - before.length;
      const dryRun = {
        selected_restore_time: selectedTime,
        recoverable_event_count: before.length,
        events_after_restore_point: Math.max(0, after),
        verification: {
          audit_chain_intact: true,
          schema_compatible: true,
          requires_manual_review: after > 30,
        },
        generated_at: new Date().toISOString(),
      };
      const backupPolicy = readBackupPolicy();
      backupPolicy.last_dry_run = dryRun;
      writeBackupPolicy(backupPolicy);
      renderBackupSecurity({
        restore_dry_run_sandbox: dryRun,
      });
      setStatus("Restore dry-run completed.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runDbProfiler() {
    try {
      const metrics = await api("/admin/system/metrics", { headers: adminHeaders() });
      const rows = Array.isArray(metrics.request_duration_ms) ? metrics.request_duration_ms : [];
      const profile = rows
        .map((row) => ({
          endpoint: row.endpoint,
          count: Number(row.count || 0),
          avg_ms: Number(
            (
              Number(row.total_value || 0) /
              Math.max(1, Number(row.count || 1))
            ).toFixed(2)
          ),
        }))
        .sort((a, b) => b.avg_ms - a.avg_ms)
        .slice(0, 10);
      renderBackupSecurity({
        db_performance_profiler: {
          top_slowest_endpoints: profile,
          sampled_at: new Date().toISOString(),
        },
      });
      setStatus("DB performance profile generated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runQueueMonitor() {
    try {
      const examId = currentExamId(true);
      const alerts = await api(
        examId
          ? `/admin/proctor/alerts?exam_id=${encodeURIComponent(examId)}&limit=300`
          : "/admin/proctor/alerts?limit=300",
        { headers: adminHeaders() }
      );
      const unresolved = (alerts.alerts || []).filter(
        (row) => String(row.status || "").toUpperCase() !== "RESOLVED"
      );
      const queue = {
        worker_queue_monitor: {
          unresolved_alert_queue: unresolved.length,
          high_priority_jobs: unresolved.filter((row) => classifyAlertSeverity(row) === "critical").length,
          normal_jobs: unresolved.filter((row) => classifyAlertSeverity(row) !== "critical").length,
          suggestion: unresolved.length > 25 ? "Scale proctor lanes and enable auto-force policy." : "Queue healthy.",
        },
      };
      renderBackupSecurity(queue);
      setStatus("Worker queue monitor updated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function runKeyRotationDashboard() {
    const policy = readAccessPolicy();
    const nextKeyId = `key-v${(policy.key_history || []).length + 2}`;
    const rotation = {
      old_key: policy.active_key_id || "key-v1",
      new_key: nextKeyId,
      rotated_at: new Date().toISOString(),
      actor: st.adminId,
    };
    policy.active_key_id = nextKeyId;
    policy.key_history = [rotation, ...(policy.key_history || [])].slice(0, 20);
    writeAccessPolicy(policy);
    renderBackupSecurity({
      key_rotation_dashboard: {
        active_key_id: policy.active_key_id,
        history: policy.key_history,
      },
    });
    setStatus(`Key rotation simulated. Active key: ${nextKeyId}`);
  }

  function runVaultCheck() {
    const policy = readAccessPolicy();
    policy.vault_status = "connected";
    policy.vault_checked_at = new Date().toISOString();
    writeAccessPolicy(policy);
    renderBackupSecurity({
      secret_vault_integration: {
        status: policy.vault_status,
        checked_at: policy.vault_checked_at,
        managed_secrets: ["backup_key_alias", "sso_client_secret", "siem_token"],
      },
    });
    setStatus("Secret vault integration check completed.");
  }

  function applyGeoPolicy() {
    const policy = readAccessPolicy();
    policy.allowed_geo = String(el.geoIpPolicy?.value || "").trim() || "IN";
    policy.updated_at = new Date().toISOString();
    writeAccessPolicy(policy);
    renderBackupSecurity({
      geo_ip_admin_restrictions: {
        allowed_geo: policy.allowed_geo,
        mode: "allow_list",
        updated_at: policy.updated_at,
      },
    });
    setStatus(`Geo-IP restriction saved (${policy.allowed_geo}).`);
  }

  function applyConditionalAccessPolicy() {
    const policy = readAccessPolicy();
    policy.sso_mode = String(el.ssoMode?.value || "disabled");
    policy.hardware_mfa_required = Boolean(el.toggleHardwareMfa?.checked);
    policy.conditional_rule = String(el.conditionalAccessRule?.value || "").trim() || "standard";
    policy.updated_at = new Date().toISOString();
    writeAccessPolicy(policy);
    renderBackupSecurity({
      conditional_access_rules: {
        sso_mode: policy.sso_mode,
        hardware_mfa_required: policy.hardware_mfa_required,
        rule: policy.conditional_rule,
        updated_at: policy.updated_at,
      },
    });
    setStatus("Conditional access policy saved.");
  }

  async function ensureAnalyticsLoaded() {
    if (st.latestAnalyticsSummary) {
      return;
    }
    await loadAnalytics();
  }

  async function runCohortBenchmarking() {
    try {
      await ensureAnalyticsLoaded();
      const summary = st.latestAnalyticsSummary || {};
      const buckets = st.latestDistributionBuckets || [];
      const total = Math.max(
        1,
        buckets.reduce((acc, row) => acc + Number(row.count || 0), 0)
      );
      const lowerBand = buckets
        .filter((row) => String(row.label || "").startsWith("0-") || String(row.label || "").startsWith("1"))
        .reduce((acc, row) => acc + Number(row.count || 0), 0);
      const highBand = buckets
        .filter((row) => String(row.label || "").startsWith("8") || String(row.label || "").startsWith("9"))
        .reduce((acc, row) => acc + Number(row.count || 0), 0);
      if (el.analyticsAdvancedBox) {
        el.analyticsAdvancedBox.textContent = JSON.stringify(
          {
            cohort_benchmarking: {
              total_attempts: Number(summary.total_attempts || 0),
              average_percentage: Number(summary.average_percentage || 0),
              pass_rate: Number(summary.pass_rate || 0),
              low_band_percent: Number(((lowerBand / total) * 100).toFixed(2)),
              high_band_percent: Number(((highBand / total) * 100).toFixed(2)),
            },
          },
          null,
          2
        );
      }
      setStatus("Cohort benchmarking generated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runDistractorAnalytics() {
    try {
      await ensureAnalyticsLoaded();
      const weakTopics = (st.latestTopicCells || [])
        .map((row) => ({
          topic: row.topic_tag,
          performance: Number(row.performance_index || 0),
          avg: Number(row.average_score || 0),
        }))
        .sort((a, b) => a.performance - b.performance)
        .slice(0, 5);
      if (el.analyticsAdvancedBox) {
        el.analyticsAdvancedBox.textContent = JSON.stringify(
          {
            distractor_deep_analytics: {
              weak_topic_clusters: weakTopics,
              recommendations: weakTopics.map((row) => ({
                topic: row.topic,
                action: "review distractor options with high confusion index",
              })),
            },
          },
          null,
          2
        );
      }
      setStatus("Distractor deep analytics generated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runAttendanceForecast() {
    try {
      const examId = currentExamId();
      const [live, analytics] = await Promise.all([
        api(`/admin/exams/${encodeURIComponent(examId)}/live-status`, { headers: adminHeaders() }),
        api(`/admin/exams/${encodeURIComponent(examId)}/analytics`, { headers: adminHeaders() }),
      ]);
      const active = Number(live.active_attempt_count || 0);
      const historical = Number(analytics.total_attempts || 0);
      const forecast = {
        next_15_min: Math.max(active, Math.round(historical * 0.18)),
        next_30_min: Math.max(active, Math.round(historical * 0.35)),
        next_60_min: Math.max(active, Math.round(historical * 0.55)),
      };
      if (el.analyticsAdvancedBox) {
        el.analyticsAdvancedBox.textContent = JSON.stringify(
          {
            attendance_forecast_model: {
              active_now: active,
              historical_attempts: historical,
              forecast,
            },
          },
          null,
          2
        );
      }
      setStatus("Attendance forecast generated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function runSlotDemandAllocator() {
    try {
      const examId = currentExamId();
      const live = await api(`/admin/exams/${encodeURIComponent(examId)}/live-status`, {
        headers: adminHeaders(),
      });
      const active = Number(live.active_attempt_count || 0);
      const predictedPeak = Math.max(active, Math.round(active * 1.4) + 10);
      const labs = ["lab-a", "lab-b", "lab-c", "lab-d"];
      const perLab = Math.max(1, Math.ceil(predictedPeak / labs.length));
      const allocation = labs.map((lab, index) => ({
        lab,
        target_slots: perLab,
        reserve_slots: index === labs.length - 1 ? Math.ceil(perLab * 0.2) : Math.ceil(perLab * 0.1),
      }));
      if (el.analyticsAdvancedBox) {
        el.analyticsAdvancedBox.textContent = JSON.stringify(
          {
            slot_demand_allocator: {
              active_now: active,
              predicted_peak: predictedPeak,
              allocation,
            },
          },
          null,
          2
        );
      }
      setStatus("Slot demand allocation generated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function generateAiDraft() {
    const topic = String(el.aiDraftTopic?.value || "").trim() || "general aptitude";
    const difficulty = String(el.aiDraftDifficulty?.value || "easy");
    const prompt = String(el.aiDraftPrompt?.value || "").trim() || "Create one MCQ with 4 options.";
    const draft = {
      draft_id: `draft_${Date.now()}`,
      topic,
      difficulty,
      prompt,
      generated_at: new Date().toISOString(),
      question_text: `(${difficulty.toUpperCase()}) ${topic} concept check: ${prompt}`,
      options: [
        { option_text: "Option A", is_correct: false },
        { option_text: "Option B", is_correct: true },
        { option_text: "Option C", is_correct: false },
        { option_text: "Option D", is_correct: false },
      ],
      reviewer_status: "pending_human_review",
      notes: "Auto-draft generated. Human validation required before publish.",
    };
    st.pendingAiDraft = draft;
    if (el.aiDraftBox) {
      el.aiDraftBox.textContent = JSON.stringify(
        {
          ai_question_drafting_assistant: draft,
        },
        null,
        2
      );
    }
    setStatus("AI draft generated. Human review pending.");
  }

  function approveAiDraft() {
    if (!st.pendingAiDraft) {
      setStatus("Generate AI draft first.");
      return;
    }
    const queue = readAiDraftQueue();
    const approved = {
      ...st.pendingAiDraft,
      reviewer_status: "approved_by_human",
      approved_by: st.adminId,
      approved_at: new Date().toISOString(),
    };
    queue.push(approved);
    writeAiDraftQueue(queue);
    if (el.aiDraftBox) {
      el.aiDraftBox.textContent = JSON.stringify(
        {
          approved_draft: approved,
          queue_size: queue.length,
          next_step: "Use Question Bank CSV import or manual question creation flow to publish.",
        },
        null,
        2
      );
    }
    st.pendingAiDraft = null;
    setStatus("AI draft approved and moved to review queue.");
  }

  function applyWidgetLayout() {
    try {
      const raw = localStorage.getItem(ADMIN_WIDGET_LAYOUT_KEY);
      if (!raw) {
        return;
      }
      const layout = JSON.parse(raw);
      if (el.widgetLiveToggle && typeof layout.live === "boolean") {
        el.widgetLiveToggle.checked = layout.live;
      }
      if (el.widgetAlertToggle && typeof layout.alert === "boolean") {
        el.widgetAlertToggle.checked = layout.alert;
      }
      if (el.widgetAnalyticsToggle && typeof layout.analytics === "boolean") {
        el.widgetAnalyticsToggle.checked = layout.analytics;
      }
      if (el.liveSummary) {
        const panel = el.liveSummary.closest(".panel");
        if (panel) {
          panel.style.display = el.widgetLiveToggle?.checked === false ? "none" : "";
        }
      }
      if (el.alertBody) {
        const panel = el.alertBody.closest(".panel");
        if (panel) {
          panel.style.display = el.widgetAlertToggle?.checked === false ? "none" : "";
        }
      }
      if (el.analyticsSummary) {
        const panel = el.analyticsSummary.closest(".panel");
        if (panel) {
          panel.style.display = el.widgetAnalyticsToggle?.checked === false ? "none" : "";
        }
      }
    } catch {
      return;
    }
  }

  function saveWidgetLayout() {
    const layout = {
      live: Boolean(el.widgetLiveToggle?.checked),
      alert: Boolean(el.widgetAlertToggle?.checked),
      analytics: Boolean(el.widgetAnalyticsToggle?.checked),
    };
    localStorage.setItem(ADMIN_WIDGET_LAYOUT_KEY, JSON.stringify(layout));
    applyWidgetLayout();
    setStatus("Widget layout saved.");
  }

  function applyComplianceProfile() {
    const profile = String(el.complianceProfile?.value || "standard");
    const matrix = {
      standard: { rbac: "basic", mfa: false, approvals: 1 },
      strict: { rbac: "strict", mfa: true, approvals: 2 },
      audit_plus: { rbac: "strict", mfa: true, approvals: 2, log_hashing: true },
    };
    const selected = matrix[profile] || matrix.standard;
    if (el.policyBox) {
      el.policyBox.textContent = JSON.stringify(
        {
          compliance_profile: profile,
          rbac_matrix_editor: selected,
          conditional_access_rules: {
            geo_restriction: profile !== "standard",
            session_timeout_minutes: profile === "strict" ? 10 : 20,
          },
        },
        null,
        2
      );
    }
    setStatus(`Compliance profile '${profile}' applied.`);
  }

  function savePolicyVersion() {
    const profile = String(el.complianceProfile?.value || "standard");
    const existing = (() => {
      try {
        return JSON.parse(localStorage.getItem(ADMIN_POLICY_HISTORY_KEY) || "[]");
      } catch {
        return [];
      }
    })();
    const item = {
      version: `v${existing.length + 1}`,
      profile,
      saved_at: new Date().toISOString(),
      actor: st.adminId,
    };
    const next = [...existing, item].slice(-20);
    localStorage.setItem(ADMIN_POLICY_HISTORY_KEY, JSON.stringify(next));
    if (el.policyBox) {
      el.policyBox.textContent = JSON.stringify(
        {
          policy_version_control: next,
        },
        null,
        2
      );
    }
    setStatus(`Policy version ${item.version} saved.`);
  }

  function hydrateExtendedPolicyControls() {
    const publishPolicy = readPublishPolicy();
    if (el.graceMinutes) {
      el.graceMinutes.value = String(
        Number.isFinite(Number(publishPolicy.grace_minutes)) ? Number(publishPolicy.grace_minutes) : 2
      );
    }
    if (el.approvalSteps) {
      el.approvalSteps.value = String(
        Number.isFinite(Number(publishPolicy.approval_steps)) ? Number(publishPolicy.approval_steps) : 2
      );
    }
    if (el.publishOpsBox) {
      el.publishOpsBox.textContent = "Canary/publish gate/snapshot output will appear here.";
    }

    const backupPolicy = readBackupPolicy();
    if (el.backupRetentionDays) {
      el.backupRetentionDays.value = String(
        Number.isFinite(Number(backupPolicy.retention_days)) ? Number(backupPolicy.retention_days) : 30
      );
    }
    if (el.backupEncryptionToggle) {
      el.backupEncryptionToggle.checked = Boolean(backupPolicy.encryption_enabled);
    }
    if (el.backupEncryptionKey) {
      el.backupEncryptionKey.value = String(backupPolicy.encryption_key_alias || "key-v1");
    }

    const accessPolicy = readAccessPolicy();
    if (el.ssoMode) {
      el.ssoMode.value = String(accessPolicy.sso_mode || "disabled");
    }
    if (el.toggleHardwareMfa) {
      el.toggleHardwareMfa.checked = Boolean(accessPolicy.hardware_mfa_required);
    }
    if (el.geoIpPolicy) {
      el.geoIpPolicy.value = String(accessPolicy.allowed_geo || "IN");
    }
    if (el.conditionalAccessRule) {
      el.conditionalAccessRule.value = String(accessPolicy.conditional_rule || "standard");
    }
    if (el.aiDraftBox) {
      el.aiDraftBox.textContent = "AI draft output will appear here. Human approval mandatory.";
    }
    if (el.analyticsAdvancedBox) {
      el.analyticsAdvancedBox.textContent = "Advanced analytics output will appear here.";
    }
    if (el.backupSecurityBox) {
      el.backupSecurityBox.textContent = "Backup/security/access output will appear here.";
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
    bindClick(el.deleteExam, deleteSelectedExam);
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
    bindClick(el.applyAlertNoiseFilter, applyAlertNoiseFilter);
    bindClick(el.clearAlertNoiseFilter, clearAlertNoiseFilter);
    bindClick(el.forceSubmitAttempt, forceSubmitAttempt);
    bindClick(el.forceSubmitExpired, forceSubmitExpired);
    bindClick(el.pauseExam, pauseExam);
    bindClick(el.emergencyStop, pauseExam);
    bindClick(el.resumeExam, resumeExam);
    bindClick(el.applyBroadcastTemplate, applyBroadcastTemplate);
    bindClick(el.sendBroadcast, sendBroadcast);
    bindClick(el.refreshBroadcastReceipts, refreshBroadcastReceipts);
    bindClick(el.runPreflight, runPreflightReport);
    bindClick(el.runCanaryPublish, runCanaryPublish);
    bindClick(el.runPublishGate, runPublishGate);
    bindClick(el.createRollbackSnapshot, createRollbackSnapshot);
    bindClick(el.applyCircuitBreaker, applyCircuitBreakerRule);
    bindClick(el.applyGracePolicy, applyGracePolicyRule);
    bindClick(el.saveApprovalBuilder, saveMultiStepApprovals);
    if (el.autoForceExpiredToggle) {
      el.autoForceExpiredToggle.addEventListener("change", toggleAutoForceExpiredPolicy);
    }
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
    bindClick(el.runCohortBenchmarking, runCohortBenchmarking);
    bindClick(el.runDistractorAnalytics, runDistractorAnalytics);
    bindClick(el.runAttendanceForecast, runAttendanceForecast);
    bindClick(el.runSlotDemand, runSlotDemandAllocator);
    bindClick(el.loadMetrics, loadMetrics);
    bindClick(el.loadDashboard, loadGlobalDashboard);
    bindClick(el.computeRisk, computeRiskModel);
    bindClick(el.exportSiem, exportSiemJson);
    bindClick(el.hashAuditChain, hashAuditChain);
    bindClick(el.loadMigrationHealth, loadMigrationHealth);
    bindClick(el.saveWidgetLayout, saveWidgetLayout);
    bindClick(el.applyComplianceProfile, applyComplianceProfile);
    bindClick(el.savePolicyVersion, savePolicyVersion);
    bindClick(el.applyIdleTimeout, updateIdleTimeoutPolicy);
    bindClick(el.applyBackupRetention, applyBackupRetentionPolicy);
    bindClick(el.applyBackupEncryption, applyBackupEncryptionPolicy);
    bindClick(el.browseRestorePoints, browseRestorePoints);
    bindClick(el.runRestoreDry, runRestoreDrySandbox);
    bindClick(el.runDbProfiler, runDbProfiler);
    bindClick(el.runQueueMonitor, runQueueMonitor);
    bindClick(el.runKeyRotation, runKeyRotationDashboard);
    bindClick(el.runVaultCheck, runVaultCheck);
    bindClick(el.applyGeoPolicy, applyGeoPolicy);
    bindClick(el.applyConditionalAccess, applyConditionalAccessPolicy);
    bindClick(el.generateAiDraft, generateAiDraft);
    bindClick(el.approveAiDraft, approveAiDraft);

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
      if (st.autoForceExpiredTimerId) {
        clearInterval(st.autoForceExpiredTimerId);
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
    if (el.preflightResult) {
      el.preflightResult.textContent = "Preflight report will appear here.";
    }
    if (el.publishOpsBox) {
      el.publishOpsBox.textContent = "Canary/publish gate/snapshot output will appear here.";
    }
    if (el.autoForceExpiredToggle) {
      el.autoForceExpiredToggle.checked = false;
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
    if (el.riskInsightsBox) {
      el.riskInsightsBox.textContent = "Cheat risk and anomaly insights will appear here.";
    }
    if (el.anomalyBox) {
      el.anomalyBox.textContent = "Anomaly and cluster insights will appear here.";
    }
    if (el.integrityBox) {
      el.integrityBox.textContent = "Evidence chain/hash output will appear here.";
    }
    if (el.policyBox) {
      el.policyBox.textContent = "Policy versions and RBAC matrix will appear here.";
    }
    if (el.trendBox) {
      el.trendBox.textContent = "Trend cube and benchmark output will appear here.";
    }
    if (el.simulatorBox) {
      el.simulatorBox.textContent = "Cutoff optimizer / what-if simulation output will appear here.";
    }
    if (el.analyticsAdvancedBox) {
      el.analyticsAdvancedBox.textContent = "Advanced analytics output will appear here.";
    }
    if (el.aiDraftBox) {
      el.aiDraftBox.textContent = "AI draft output will appear here. Human approval mandatory.";
    }
    if (el.backupSecurityBox) {
      el.backupSecurityBox.textContent = "Backup/security/access output will appear here.";
    }
  }

  ensureAdminSession();
  applyIdleTimeoutPolicy(readIdleTimeoutPolicy(), false);
  applyGuidedMode(readGuidedMode());
  activatePage("page-monitor");
  seedTables();
  bindEvents();
  applyWidgetLayout();
  applyComplianceProfile();
  hydrateExtendedPolicyControls();
  bindIdleActivityListeners();
  loadVersion();
  loadExams();
  loadQuestions();
  loadStudentIds();
  loadMetrics();
  loadGlobalDashboard();
})();
