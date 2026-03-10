(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const st = {
    examId: "",
    cursor: null,
    polling: false,
    timerId: null,
    seenEventIds: new Set(),
  };

  const el = {
    version: $("version"),
    loadExams: $("load-exams"),
    examSelect: $("exam-select"),
    status: $("admin-status"),
    refreshLive: $("refresh-live"),
    syncAlerts: $("sync-alerts"),
    loadAlerts: $("load-alerts"),
    liveSummary: $("live-summary"),
    activeBody: $("active-body"),
    alertBody: $("alert-body"),
    pullEvents: $("pull-events"),
    toggleAuto: $("toggle-auto"),
    cursorLabel: $("cursor-label"),
    eventsBody: $("events-body"),
    minAttempts: $("min-attempts"),
    applyRun: $("apply-run"),
    runRecalibration: $("run-recalibration"),
    loadHistory: $("load-history"),
    rollbackReason: $("rollback-reason"),
    runSummary: $("run-summary"),
    runsBody: $("runs-body"),
    itemsBody: $("items-body"),
  };

  const adminHeaders = () => ({ "x-admin": "true", "x-admin-id": "web-admin" });
  const setStatus = (message) => {
    el.status.textContent = message;
  };

  async function api(path, options = {}) {
    const request = { ...options, headers: { ...(options.headers || {}) } };
    if (request.body && typeof request.body !== "string") {
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

  function currentExamId() {
    const examId = el.examSelect.value;
    if (!examId) {
      throw new Error("Select exam first");
    }
    st.examId = examId;
    return examId;
  }

  function renderActiveAttempts(rows) {
    if (!rows.length) {
      el.activeBody.innerHTML =
        '<tr><td colspan="5" class="small">No active attempts.</td></tr>';
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
      el.eventsBody.innerHTML =
        '<tr><td colspan="5" class="small">No events yet.</td></tr>';
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
      const data = await api("/admin/exams", { headers: adminHeaders() });
      renderExamOptions(data);
      setStatus(`Loaded ${data.length} exam(s).`);
    } catch (error) {
      setStatus(error.message);
    }
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
      setStatus(`Fetched ${(data.events || []).length} event(s) with cursor paging.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function toggleAutoPolling() {
    if (st.polling) {
      st.polling = false;
      if (st.timerId) {
        clearInterval(st.timerId);
      }
      st.timerId = null;
      el.toggleAuto.textContent = "Start Auto Poll";
      setStatus("Auto polling stopped.");
      return;
    }
    st.polling = true;
    st.timerId = window.setInterval(() => {
      pullEvents();
    }, 3000);
    el.toggleAuto.textContent = "Stop Auto Poll";
    setStatus("Auto polling started (3s interval).");
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

  function bindEvents() {
    el.loadExams.addEventListener("click", loadExams);
    el.refreshLive.addEventListener("click", refreshLive);
    el.syncAlerts.addEventListener("click", syncAlerts);
    el.loadAlerts.addEventListener("click", loadAlerts);
    el.pullEvents.addEventListener("click", pullEvents);
    el.toggleAuto.addEventListener("click", toggleAutoPolling);
    el.runRecalibration.addEventListener("click", runRecalibration);
    el.loadHistory.addEventListener("click", loadHistory);

    el.examSelect.addEventListener("change", () => {
      st.cursor = null;
      st.seenEventIds.clear();
      el.cursorLabel.textContent = "none";
      el.eventsBody.innerHTML = "";
    });

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

    window.addEventListener("beforeunload", () => {
      if (st.timerId) {
        clearInterval(st.timerId);
      }
    });
  }

  function seedTables() {
    el.activeBody.innerHTML = '<tr><td colspan="5" class="small">No active attempts.</td></tr>';
    el.alertBody.innerHTML = '<tr><td colspan="6" class="small">No alerts.</td></tr>';
    el.eventsBody.innerHTML = '<tr><td colspan="5" class="small">No events yet.</td></tr>';
    el.runsBody.innerHTML = '<tr><td colspan="7" class="small">No recalibration runs.</td></tr>';
    el.itemsBody.innerHTML = '<tr><td colspan="6" class="small">No run items.</td></tr>';
  }

  bindEvents();
  seedTables();
  loadVersion();
})();
