(() => {
  const ADMIN_DEMO_KEY = "nitmexs-admin";
  const STUDENT_SESSION_KEY = "nitmexs_student_session";
  const ADMIN_SESSION_KEY = "nitmexs_admin_session";

  const el = {
    version: document.getElementById("version-badge"),
    studentId: document.getElementById("student-login-id"),
    studentLogin: document.getElementById("student-login-btn"),
    adminId: document.getElementById("admin-login-id"),
    adminKey: document.getElementById("admin-login-key"),
    adminLogin: document.getElementById("admin-login-btn"),
    continueStudent: document.getElementById("continue-student"),
    continueAdmin: document.getElementById("continue-admin"),
    logoutAll: document.getElementById("logout-all"),
    status: document.getElementById("portal-status"),
  };

  const setStatus = (message) => {
    if (el.status) {
      el.status.textContent = message;
    }
  };

  const readSession = (key) => {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return null;
      }
      return JSON.parse(raw);
    } catch {
      return null;
    }
  };

  const writeSession = (key, payload) => {
    localStorage.setItem(key, JSON.stringify(payload));
  };

  async function loadVersion() {
    if (!el.version) {
      return;
    }
    try {
      const response = await fetch("/system/version");
      const payload = await response.json();
      el.version.textContent = payload?.data?.version ?? "n/a";
    } catch {
      el.version.textContent = "unreachable";
    }
  }

  function loginStudent() {
    const studentId = (el.studentId?.value || "").trim();
    if (!studentId) {
      setStatus("Student login ke liye Student ID required hai.");
      return;
    }
    writeSession(STUDENT_SESSION_KEY, {
      student_id: studentId,
      logged_in_at: new Date().toISOString(),
    });
    setStatus(`Student session created for ${studentId}. Redirecting...`);
    window.location.href = "/web/student.html";
  }

  function loginAdmin() {
    const adminId = (el.adminId?.value || "").trim();
    const adminKey = (el.adminKey?.value || "").trim();
    if (!adminId) {
      setStatus("Admin login ke liye Admin ID required hai.");
      return;
    }
    if (!adminKey) {
      setStatus("Admin login ke liye Access Key required hai.");
      return;
    }
    if (adminKey !== ADMIN_DEMO_KEY) {
      setStatus("Access Key invalid hai. Demo key use karo: nitmexs-admin");
      return;
    }
    writeSession(ADMIN_SESSION_KEY, {
      admin_id: adminId,
      logged_in_at: new Date().toISOString(),
    });
    setStatus(`Admin session created for ${adminId}. Redirecting...`);
    window.location.href = "/web/admin.html";
  }

  function continueStudentSession() {
    const session = readSession(STUDENT_SESSION_KEY);
    if (!session?.student_id) {
      setStatus("No active student session found.");
      return;
    }
    window.location.href = "/web/student.html";
  }

  function continueAdminSession() {
    const session = readSession(ADMIN_SESSION_KEY);
    if (!session?.admin_id) {
      setStatus("No active admin session found.");
      return;
    }
    window.location.href = "/web/admin.html";
  }

  function logoutAllSessions() {
    localStorage.removeItem(STUDENT_SESSION_KEY);
    localStorage.removeItem(ADMIN_SESSION_KEY);
    setStatus("All sessions cleared. Fresh login required.");
  }

  function hydrateFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const target = params.get("target");
    const reason = params.get("reason");
    if (target === "student" && reason === "login_required") {
      setStatus("Student page open karne ke liye pehle student login karo.");
    } else if (target === "admin" && reason === "login_required") {
      setStatus("Admin console open karne ke liye pehle admin login karo.");
    }
  }

  function bindEvents() {
    el.studentLogin?.addEventListener("click", loginStudent);
    el.adminLogin?.addEventListener("click", loginAdmin);
    el.continueStudent?.addEventListener("click", continueStudentSession);
    el.continueAdmin?.addEventListener("click", continueAdminSession);
    el.logoutAll?.addEventListener("click", logoutAllSessions);
  }

  loadVersion();
  hydrateFromQuery();
  bindEvents();
})();
