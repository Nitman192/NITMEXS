(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const st = {
    studentId: "",
    examId: "",
    attemptId: "",
    sequence: 1,
    currentQuestion: null,
    expiresAt: null,
    timerId: null,
  };

  const el = {
    version: $("version"),
    studentId: $("student-id"),
    loadExams: $("load-exams"),
    examSelect: $("exam-select"),
    startAttempt: $("start-attempt"),
    status: $("student-status"),
    meta: $("attempt-meta"),
    attemptId: $("attempt-id"),
    sequence: $("sequence-number"),
    remaining: $("remaining-time"),
    prev: $("prev-question"),
    next: $("next-question"),
    questionBox: $("question-box"),
    submit: $("submit-answer"),
    finalize: $("finalize-attempt"),
    result: $("view-result"),
    resultBox: $("result-box"),
  };

  const setStatus = (message) => {
    el.status.textContent = message;
  };

  function studentHeaders() {
    const id = el.studentId.value.trim();
    if (!id) {
      throw new Error("Student ID required");
    }
    st.studentId = id;
    return { "x-student-id": id };
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

  function formatRemaining(expiresAt) {
    if (!expiresAt) {
      return "-";
    }
    const expires = new Date(expiresAt).valueOf();
    const diff = Math.max(0, Math.floor((expires - Date.now()) / 1000));
    const mins = Math.floor(diff / 60);
    const secs = diff % 60;
    return `${mins}m ${secs}s`;
  }

  function startTimer() {
    if (st.timerId) {
      clearInterval(st.timerId);
      st.timerId = null;
    }
    el.remaining.textContent = formatRemaining(st.expiresAt);
    st.timerId = window.setInterval(() => {
      el.remaining.textContent = formatRemaining(st.expiresAt);
    }, 1000);
  }

  function renderExamOptions(exams) {
    const previous = el.examSelect.value;
    el.examSelect.innerHTML = '<option value="">Select available exam...</option>';
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

  function renderQuestion(payload) {
    st.currentQuestion = payload.question;
    el.sequence.textContent = String(st.sequence);
    const options = (payload.options || [])
      .map(
        (option) => `
          <label class="option">
            <input type="radio" name="selected-option" value="${esc(option.id)}">
            <span>${esc(option.option_text)}</span>
          </label>
        `
      )
      .join("");
    el.questionBox.innerHTML = `
      <p class="small">Question #${esc(st.sequence)}</p>
      <p class="question">${esc(payload.question.text)}</p>
      <p class="small">Topic: ${esc(payload.question.topic)} | Difficulty: ${esc(payload.question.difficulty)} | Marks: ${esc(payload.question.marks)}</p>
      <div class="stack">${options}</div>
    `;
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
      const exams = await api("/student/exams", { headers: studentHeaders() });
      renderExamOptions(exams);
      setStatus(`Loaded ${exams.length} available exam(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function startAttempt() {
    try {
      const examId = el.examSelect.value;
      if (!examId) {
        throw new Error("Select exam first");
      }
      const data = await api(`/student/exams/${encodeURIComponent(examId)}/start`, {
        method: "POST",
        headers: studentHeaders(),
      });
      st.examId = examId;
      st.attemptId = data.attempt_id;
      st.sequence = 1;
      st.expiresAt = data.expires_at;
      el.attemptId.textContent = data.attempt_id;
      el.meta.innerHTML = `
        Exam: <span class="mono">${esc(examId)}</span><br>
        Started: ${esc(formatDate(data.started_at))}<br>
        Expires: ${esc(formatDate(data.expires_at))}<br>
        Status: ${esc(data.status)}
      `;
      startTimer();
      renderQuestion(data.first_question);
      setStatus("Attempt started. Best of luck.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function fetchQuestion(sequence) {
    try {
      if (!st.attemptId) {
        throw new Error("Start an attempt first");
      }
      if (sequence < 1) {
        throw new Error("Invalid sequence");
      }
      const data = await api(
        `/student/attempts/${encodeURIComponent(st.attemptId)}/questions/${sequence}`,
        { headers: studentHeaders() }
      );
      st.sequence = sequence;
      renderQuestion(data);
      setStatus(`Question #${sequence} loaded.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function submitAnswer() {
    try {
      if (!st.attemptId || !st.currentQuestion) {
        throw new Error("No active question context");
      }
      const selected = document.querySelector('input[name="selected-option"]:checked');
      if (!selected) {
        throw new Error("Select an option first");
      }
      await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/answers`, {
        method: "POST",
        headers: studentHeaders(),
        body: {
          question_id: st.currentQuestion.id,
          selected_option_id: selected.value,
        },
      });
      setStatus(`Answer submitted for question #${st.sequence}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function finalizeAttempt() {
    try {
      if (!st.attemptId) {
        throw new Error("No active attempt");
      }
      const data = await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/finalize`, {
        method: "POST",
        headers: studentHeaders(),
      });
      el.resultBox.textContent = JSON.stringify(data.result, null, 2);
      setStatus("Attempt finalized. Grading completed.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function viewResult() {
    try {
      if (!st.attemptId) {
        throw new Error("No active attempt");
      }
      const data = await api(`/student/attempts/${encodeURIComponent(st.attemptId)}/result`, {
        headers: studentHeaders(),
      });
      el.resultBox.textContent = JSON.stringify(data, null, 2);
      setStatus("Result fetched.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function bindEvents() {
    el.loadExams.addEventListener("click", loadExams);
    el.startAttempt.addEventListener("click", startAttempt);
    el.prev.addEventListener("click", () => fetchQuestion(st.sequence - 1));
    el.next.addEventListener("click", () => fetchQuestion(st.sequence + 1));
    el.submit.addEventListener("click", submitAnswer);
    el.finalize.addEventListener("click", finalizeAttempt);
    el.result.addEventListener("click", viewResult);
    window.addEventListener("beforeunload", () => {
      if (st.timerId) {
        clearInterval(st.timerId);
      }
    });
  }

  bindEvents();
  loadVersion();
})();
