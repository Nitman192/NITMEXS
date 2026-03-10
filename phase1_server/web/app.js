(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (v) =>
    String(v ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  const st = {
    s: { id: "", exam: "", aid: "", seq: 1, q: null },
    a: { exam: "", cursor: null, polling: false, timer: null, seen: new Set() },
    r: { exam: "", run: null },
  };
  const el = {
    version: $("version"),
    sid: $("sid"),
    sExam: $("s-exam"),
    sLoad: $("s-load"),
    sStart: $("s-start"),
    sStatus: $("s-status"),
    sMeta: $("s-meta"),
    sAid: $("s-aid"),
    sQ: $("s-q"),
    sPrev: $("s-prev"),
    sNext: $("s-next"),
    sSubmit: $("s-submit"),
    sFinal: $("s-final"),
    sResult: $("s-result"),
    sResultBox: $("s-result-box"),
    aLoad: $("a-load"),
    aExam: $("a-exam"),
    pLive: $("p-live"),
    pSync: $("p-sync"),
    pAlerts: $("p-alerts"),
    pPull: $("p-pull"),
    pAuto: $("p-auto"),
    pCursor: $("p-cursor"),
    pStatus: $("p-status"),
    pSummary: $("p-summary"),
    pActive: $("p-active"),
    pAlertBody: $("p-alert-body"),
    pEvents: $("p-events"),
    rExam: $("r-exam"),
    rMin: $("r-min"),
    rApply: $("r-apply"),
    rRun: $("r-run"),
    rHist: $("r-hist"),
    rReason: $("r-reason"),
    rStatus: $("r-status"),
    rLast: $("r-last"),
    rRuns: $("r-runs"),
    rItems: $("r-items"),
  };

  const setStatus = (node, msg) => {
    node.textContent = msg;
  };
  const t = (iso) => {
    if (!iso) return "-";
    const d = new Date(iso);
    return Number.isNaN(d.valueOf()) ? iso : d.toLocaleString();
  };
  const sec = (s) => {
    if (s == null) return "-";
    const v = Math.max(0, Number(s) || 0);
    return `${Math.floor(v / 60)}m ${v % 60}s`;
  };
  const studHeaders = () => {
    const id = el.sid.value.trim();
    if (!id) throw new Error("Student ID required");
    st.s.id = id;
    return { "x-student-id": id };
  };
  const adminHeaders = () => ({ "x-admin": "true", "x-admin-id": "web-admin" });

  async function api(path, opts = {}) {
    const o = { ...opts, headers: { ...(opts.headers || {}) } };
    if (o.body && typeof o.body !== "string") {
      o.headers["Content-Type"] = "application/json";
      o.body = JSON.stringify(o.body);
    }
    const r = await fetch(path, o);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.detail || j.error || `HTTP ${r.status}`);
    return j.data ?? j;
  }

  const fillExams = (select, items) => {
    const prev = select.value;
    select.innerHTML = '<option value="">Select exam...</option>';
    for (const ex of items) {
      select.insertAdjacentHTML(
        "beforeend",
        `<option value="${esc(ex.id)}">${esc(ex.name)} [${esc(ex.status)}]</option>`
      );
    }
    if (prev && items.some((x) => x.id === prev)) select.value = prev;
  };

  function renderStudentQ(payload) {
    st.s.q = payload.question;
    const opts = (payload.options || [])
      .map(
        (o) =>
          `<label class="row"><input type="radio" name="sopt" value="${esc(o.id)}"><span>${esc(
            o.option_text
          )}</span></label>`
      )
      .join("");
    el.sQ.innerHTML = `<div class="small">Sequence #${st.s.seq}</div><div style="font-weight:600">${esc(
      payload.question.text
    )}</div><div class="small">Topic: ${esc(payload.question.topic)} | Difficulty: ${esc(
      payload.question.difficulty
    )}</div>${opts}`;
  }

  async function loadVersion() {
    try {
      const d = await api("/system/version");
      el.version.textContent = d.version;
    } catch {
      el.version.textContent = "n/a";
    }
  }

  async function sLoadExams() {
    try {
      const data = await api("/student/exams", { headers: studHeaders() });
      fillExams(el.sExam, data);
      setStatus(el.sStatus, `Loaded ${data.length} exam(s).`);
    } catch (e) {
      setStatus(el.sStatus, e.message);
    }
  }

  async function sStart() {
    try {
      const exam = el.sExam.value;
      if (!exam) throw new Error("Select exam first");
      const d = await api(`/student/exams/${encodeURIComponent(exam)}/start`, {
        method: "POST",
        headers: studHeaders(),
      });
      st.s.exam = exam;
      st.s.aid = d.attempt_id;
      st.s.seq = 1;
      el.sAid.textContent = d.attempt_id;
      el.sMeta.innerHTML = `Exam: <span class="mono">${esc(
        exam
      )}</span><br>Started: ${esc(t(d.started_at))}<br>Expires: ${esc(t(d.expires_at))}<br>Status: ${esc(
        d.status
      )}`;
      renderStudentQ(d.first_question);
      setStatus(el.sStatus, "Attempt started.");
    } catch (e) {
      setStatus(el.sStatus, e.message);
    }
  }

  async function sFetch(seqNo) {
    try {
      if (!st.s.aid) throw new Error("Start attempt first");
      if (seqNo < 1) throw new Error("Invalid sequence");
      const d = await api(
        `/student/attempts/${encodeURIComponent(st.s.aid)}/questions/${seqNo}`,
        { headers: studHeaders() }
      );
      st.s.seq = seqNo;
      renderStudentQ(d);
      setStatus(el.sStatus, `Loaded question #${seqNo}.`);
    } catch (e) {
      setStatus(el.sStatus, e.message);
    }
  }

  async function sSubmit() {
    try {
      if (!st.s.aid || !st.s.q) throw new Error("No active question");
      const pick = document.querySelector('input[name="sopt"]:checked');
      if (!pick) throw new Error("Select option first");
      await api(`/student/attempts/${encodeURIComponent(st.s.aid)}/answers`, {
        method: "POST",
        headers: studHeaders(),
        body: { question_id: st.s.q.id, selected_option_id: pick.value },
      });
      setStatus(el.sStatus, "Answer submitted.");
    } catch (e) {
      setStatus(el.sStatus, e.message);
    }
  }

  async function sFinalize() {
    try {
      if (!st.s.aid) throw new Error("No active attempt");
      const d = await api(`/student/attempts/${encodeURIComponent(st.s.aid)}/finalize`, {
        method: "POST",
        headers: studHeaders(),
      });
      el.sResultBox.textContent = JSON.stringify(d.result, null, 2);
      setStatus(el.sStatus, "Finalized and graded.");
    } catch (e) {
      setStatus(el.sStatus, e.message);
    }
  }

  async function sResult() {
    try {
      if (!st.s.aid) throw new Error("No attempt");
      const d = await api(`/student/attempts/${encodeURIComponent(st.s.aid)}/result`, {
        headers: studHeaders(),
      });
      el.sResultBox.textContent = JSON.stringify(d, null, 2);
      setStatus(el.sStatus, "Result loaded.");
    } catch (e) {
      setStatus(el.sStatus, e.message);
    }
  }

  async function aLoadExams() {
    try {
      const data = await api("/admin/exams", { headers: adminHeaders() });
      fillExams(el.aExam, data);
      fillExams(el.rExam, data);
      setStatus(el.pStatus, `Loaded ${data.length} exam(s).`);
      setStatus(el.rStatus, `Loaded ${data.length} exam(s).`);
    } catch (e) {
      setStatus(el.pStatus, e.message);
      setStatus(el.rStatus, e.message);
    }
  }

  const curExam = () => {
    const exam = el.aExam.value;
    if (!exam) throw new Error("Select admin exam");
    st.a.exam = exam;
    return exam;
  };
  const curRecalExam = () => {
    const exam = el.rExam.value;
    if (!exam) throw new Error("Select recalibration exam");
    st.r.exam = exam;
    return exam;
  };

  function renderActive(rows) {
    if (!rows.length) {
      el.pActive.innerHTML = '<tr><td colspan="5" class="small">No active attempts.</td></tr>';
      return;
    }
    el.pActive.innerHTML = rows
      .map(
        (r) =>
          `<tr><td class="mono">${esc(r.attempt_id)}</td><td>${esc(r.student_id)}</td><td>${esc(
            sec(r.remaining_seconds)
          )}</td><td>${esc(String(r.answered_question_count || 0))}/${esc(
            String(r.total_question_count || 0)
          )}</td><td>${esc((Number(r.progress_percent || 0)).toFixed(1))}%</td></tr>`
      )
      .join("");
  }

  function renderAlerts(rows) {
    if (!rows.length) {
      el.pAlertBody.innerHTML = '<tr><td colspan="6" class="small">No alerts.</td></tr>';
      return;
    }
    el.pAlertBody.innerHTML = rows
      .map(
        (a) =>
          `<tr><td class="mono">${esc(a.id)}</td><td>${esc(a.status)}</td><td>${esc(
            a.indicator_code
          )}</td><td>${esc(a.student_id)}</td><td>${esc(
            t(a.last_detected_at || a.created_at)
          )}</td><td><button class="alt js-aa" data-id="${esc(
            a.id
          )}">Ack</button> <button class="warn js-ar" data-id="${esc(a.id)}">Resolve</button></td></tr>`
      )
      .join("");
  }

  function renderEvents(rows) {
    if (!rows.length && !el.pEvents.children.length) {
      el.pEvents.innerHTML = '<tr><td colspan="5" class="small">No events yet.</td></tr>';
      return;
    }
    if (!rows.length) return;
    if (el.pEvents.textContent.includes("No events yet")) el.pEvents.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (const ev of rows) {
      if (st.a.seen.has(ev.event_id)) continue;
      st.a.seen.add(ev.event_id);
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(t(ev.created_at))}</td><td>${esc(ev.event_type)}</td><td class="mono">${esc(
        ev.attempt_id
      )}</td><td>${esc(ev.student_id)}</td><td class="mono">${esc(ev.event_id)}</td>`;
      frag.appendChild(tr);
    }
    el.pEvents.appendChild(frag);
  }

  async function pLive() {
    try {
      const exam = curExam();
      const [live, active] = await Promise.all([
        api(`/admin/exams/${encodeURIComponent(exam)}/live-status`, { headers: adminHeaders() }),
        api(`/admin/exams/${encodeURIComponent(exam)}/active-attempts`, {
          headers: adminHeaders(),
        }),
      ]);
      renderActive(active);
      el.pSummary.textContent = JSON.stringify(
        {
          exam_id: live.exam_id,
          as_of: live.as_of,
          active_attempt_count: live.active_attempt_count,
          suspicious: (live.suspicious_indicators || []).length,
          finalize_events: (live.recent_finalize_events || []).length,
        },
        null,
        2
      );
      setStatus(el.pStatus, "Live status refreshed.");
    } catch (e) {
      setStatus(el.pStatus, e.message);
    }
  }

  async function pSync() {
    try {
      const exam = curExam();
      const d = await api(`/admin/proctor/alerts/sync?exam_id=${encodeURIComponent(exam)}`, {
        method: "POST",
        headers: adminHeaders(),
      });
      setStatus(
        el.pStatus,
        `Alerts synced: created=${d.created_count}, updated=${d.updated_count}, auto_resolved=${d.auto_resolved_count}`
      );
      await pAlerts();
    } catch (e) {
      setStatus(el.pStatus, e.message);
    }
  }

  async function pAlerts() {
    try {
      const exam = curExam();
      const d = await api(`/admin/proctor/alerts?exam_id=${encodeURIComponent(exam)}&limit=300`, {
        headers: adminHeaders(),
      });
      renderAlerts(d.alerts || []);
      setStatus(el.pStatus, `Loaded ${d.count} alert(s).`);
    } catch (e) {
      setStatus(el.pStatus, e.message);
    }
  }

  async function pAckResolve(alertId, resolve) {
    try {
      const path = resolve
        ? `/admin/proctor/alerts/${encodeURIComponent(alertId)}/resolve`
        : `/admin/proctor/alerts/${encodeURIComponent(alertId)}/acknowledge`;
      await api(path, {
        method: "POST",
        headers: adminHeaders(),
        body: resolve ? { note: "resolved_from_web_console" } : undefined,
      });
      await pAlerts();
    } catch (e) {
      setStatus(el.pStatus, e.message);
    }
  }

  async function pPull() {
    try {
      const exam = curExam();
      const q = new URLSearchParams({ exam_id: exam, limit: "100" });
      if (st.a.cursor) q.set("cursor", st.a.cursor);
      const d = await api(`/admin/proctor/events?${q.toString()}`, { headers: adminHeaders() });
      renderEvents(d.events || []);
      st.a.cursor = d.next_cursor || st.a.cursor;
      el.pCursor.textContent = st.a.cursor || "none";
      setStatus(el.pStatus, `Pulled ${(d.events || []).length} event(s).`);
    } catch (e) {
      setStatus(el.pStatus, e.message);
    }
  }

  function pToggleAuto() {
    if (st.a.polling) {
      st.a.polling = false;
      if (st.a.timer) clearInterval(st.a.timer);
      st.a.timer = null;
      el.pAuto.textContent = "Start Auto Poll";
      return;
    }
    st.a.polling = true;
    el.pAuto.textContent = "Stop Auto Poll";
    st.a.timer = window.setInterval(pPull, 3000);
  }

  function renderRuns(runs) {
    if (!runs.length) {
      el.rRuns.innerHTML = '<tr><td colspan="7" class="small">No runs.</td></tr>';
      return;
    }
    el.rRuns.innerHTML = runs
      .map(
        (r) =>
          `<tr><td>${esc(t(r.created_at))}</td><td class="mono">${esc(r.run_id)}</td><td>${esc(
            r.mode
          )}</td><td>${esc(String(r.updated_questions))}</td><td>${esc(
            String(r.eligible_questions)
          )}</td><td class="mono">${esc(r.source_run_id || "-")}</td><td><button class="alt js-rv" data-id="${esc(
            r.run_id
          )}">View</button> <button class="warn js-rr" data-id="${esc(r.run_id)}" ${
            r.mode === "apply" ? "" : "disabled"
          }>Rollback</button></td></tr>`
      )
      .join("");
  }

  function renderItems(items) {
    if (!items.length) {
      el.rItems.innerHTML = '<tr><td colspan="6" class="small">No items.</td></tr>';
      return;
    }
    el.rItems.innerHTML = items
      .map(
        (i) =>
          `<tr><td class="mono">${esc(i.question_id)}</td><td>${esc(
            String(i.total_attempts ?? 0)
          )}</td><td>${esc(Number(i.observed_difficulty_index ?? 0).toFixed(2))}</td><td>${esc(
            `${i.current?.difficulty ?? "-"} / L${i.current?.difficulty_level ?? "-"} / D${
              i.current?.discrimination_index ?? "-"
            }`
          )}</td><td>${esc(
            `${i.suggested?.difficulty ?? "-"} / L${i.suggested?.difficulty_level ?? "-"} / D${
              i.suggested?.discrimination_index ?? "-"
            }`
          )}</td><td>${esc(i.status)}</td></tr>`
      )
      .join("");
  }

  async function rRun() {
    try {
      const exam = curRecalExam();
      const d = await api(`/admin/exams/${encodeURIComponent(exam)}/questions/recalibrate`, {
        method: "POST",
        headers: adminHeaders(),
        body: { min_attempts: Number(el.rMin.value || "1"), apply: !!el.rApply.checked },
      });
      el.rLast.textContent = JSON.stringify(
        {
          run_id: d.run_id,
          mode: d.mode,
          total_questions: d.total_questions,
          eligible_questions: d.eligible_questions,
          updated_questions: d.updated_questions,
          skipped_questions: d.skipped_questions,
        },
        null,
        2
      );
      setStatus(el.rStatus, `Recalibration ${d.mode} run completed.`);
      await rHist();
    } catch (e) {
      setStatus(el.rStatus, e.message);
    }
  }

  async function rHist() {
    try {
      const exam = curRecalExam();
      const d = await api(
        `/admin/exams/${encodeURIComponent(exam)}/questions/recalibration-runs?limit=200`,
        { headers: adminHeaders() }
      );
      renderRuns(d.runs || []);
      setStatus(el.rStatus, `Loaded ${(d.runs || []).length} run(s).`);
    } catch (e) {
      setStatus(el.rStatus, e.message);
    }
  }

  async function rView(runId) {
    try {
      const exam = curRecalExam();
      const d = await api(
        `/admin/exams/${encodeURIComponent(exam)}/questions/recalibration-runs/${encodeURIComponent(
          runId
        )}`,
        { headers: adminHeaders() }
      );
      renderItems(d.items || []);
      setStatus(el.rStatus, `Loaded run ${runId}.`);
    } catch (e) {
      setStatus(el.rStatus, e.message);
    }
  }

  async function rRollback(runId) {
    try {
      const exam = curRecalExam();
      const note = el.rReason.value.trim();
      const d = await api(
        `/admin/exams/${encodeURIComponent(exam)}/questions/recalibration-runs/${encodeURIComponent(
          runId
        )}/rollback`,
        { method: "POST", headers: adminHeaders(), body: note ? { reason: note } : {} }
      );
      el.rLast.textContent = JSON.stringify(
        {
          run_id: d.run_id,
          source_run_id: d.source_run_id,
          updated_questions: d.updated_questions,
          reason: d.reason,
        },
        null,
        2
      );
      setStatus(el.rStatus, `Rollback completed for ${runId}.`);
      await rHist();
      await rView(d.run_id);
    } catch (e) {
      setStatus(el.rStatus, e.message);
    }
  }

  function bind() {
    el.sLoad.addEventListener("click", sLoadExams);
    el.sStart.addEventListener("click", sStart);
    el.sPrev.addEventListener("click", () => sFetch(st.s.seq - 1));
    el.sNext.addEventListener("click", () => sFetch(st.s.seq + 1));
    el.sSubmit.addEventListener("click", sSubmit);
    el.sFinal.addEventListener("click", sFinalize);
    el.sResult.addEventListener("click", sResult);
    el.aLoad.addEventListener("click", aLoadExams);
    el.pLive.addEventListener("click", pLive);
    el.pSync.addEventListener("click", pSync);
    el.pAlerts.addEventListener("click", pAlerts);
    el.pPull.addEventListener("click", pPull);
    el.pAuto.addEventListener("click", pToggleAuto);
    el.aExam.addEventListener("change", () => {
      st.a.cursor = null;
      st.a.seen.clear();
      el.pCursor.textContent = "none";
      el.pEvents.innerHTML = "";
    });
    el.pAlertBody.addEventListener("click", (ev) => {
      const t = ev.target;
      if (!(t instanceof HTMLElement)) return;
      if (t.classList.contains("js-aa")) pAckResolve(t.getAttribute("data-id"), false);
      if (t.classList.contains("js-ar")) pAckResolve(t.getAttribute("data-id"), true);
    });
    el.rRun.addEventListener("click", rRun);
    el.rHist.addEventListener("click", rHist);
    el.rRuns.addEventListener("click", (ev) => {
      const t = ev.target;
      if (!(t instanceof HTMLElement)) return;
      const id = t.getAttribute("data-id");
      if (!id) return;
      if (t.classList.contains("js-rv")) rView(id);
      if (t.classList.contains("js-rr")) rRollback(id);
    });
    window.addEventListener("beforeunload", () => {
      if (st.a.timer) clearInterval(st.a.timer);
    });
  }

  function seed() {
    el.pActive.innerHTML = '<tr><td colspan="5" class="small">No active attempts.</td></tr>';
    el.pAlertBody.innerHTML = '<tr><td colspan="6" class="small">No alerts.</td></tr>';
    el.pEvents.innerHTML = '<tr><td colspan="5" class="small">No events yet.</td></tr>';
    el.rRuns.innerHTML = '<tr><td colspan="7" class="small">No runs.</td></tr>';
    el.rItems.innerHTML = '<tr><td colspan="6" class="small">No items.</td></tr>';
  }

  bind();
  seed();
  loadVersion();
})();
