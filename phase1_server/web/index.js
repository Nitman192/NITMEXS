(() => {
  const STUDENT_SESSION_KEY = "nitmexs_student_session";
  const ADMIN_SESSION_KEY = "nitmexs_admin_session";
  const $ = (id) => document.getElementById(id);
  const explainApiError = (detail) => {
    if (detail == null || detail === "") return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => explainApiError(item)).filter(Boolean).join("; ");
    }
    if (typeof detail === "object") {
      if (typeof detail.msg === "string") {
        const where = Array.isArray(detail.loc) ? detail.loc.join(" > ") : "";
        return where ? `${where}: ${detail.msg}` : detail.msg;
      }
      if (typeof detail.detail === "string") return detail.detail;
      return Object.entries(detail)
        .map(([key, value]) => `${key}: ${explainApiError(value)}`)
        .filter((item) => item && !item.endsWith(": "))
        .join(", ");
    }
    return String(detail);
  };
  const el = {
    version: $("version-badge"),
    accessProfile: $("access-profile-label"),
    studentId: $("student-login-id"),
    studentPassword: $("student-login-password"),
    studentLogin: $("student-login-btn"),
    adminCard: $("admin-card"),
    adminId: $("admin-login-id"),
    adminKey: $("admin-login-key"),
    adminLogin: $("admin-login-btn"),
    continueStudent: $("continue-student"),
    continueAdmin: $("continue-admin"),
    logoutAll: $("logout-all"),
    status: $("portal-status"),
    errorDialog: $("gateway-error-dialog"),
    errorText: $("gateway-error-text"),
    errorClose: $("gateway-error-close"),
  };

  const openDialog = (dialog) => {
    if (!dialog) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "open");
  };

  const closeDialog = (dialog) => {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };

  const showErrorDialog = (message) => {
    if (!el.errorDialog || !el.errorText) return;
    el.errorText.textContent = String(message ?? "Something went wrong.");
    openDialog(el.errorDialog);
  };

  const setStatus = (message, isError = false) => {
    if (el.status) el.status.textContent = String(message ?? "");
    if (isError && message) showErrorDialog(message);
  };

  const readSession = (key) => {
    try {
      return JSON.parse(localStorage.getItem(key) || "null");
    } catch {
      return null;
    }
  };

  const writeSession = (key, payload) => {
    localStorage.setItem(key, JSON.stringify(payload));
  };

  async function api(path, options = {}) {
    const req = { ...options, headers: { ...(options.headers || {}) } };
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

  async function loadPortalContext() {
    try {
      const version = await api("/system/version");
      el.version.textContent = version.version || "n/a";
    } catch {
      el.version.textContent = "offline";
    }
    try {
      const profile = await api("/system/access-profile");
      el.accessProfile.textContent = `${profile.request_machine_type} / ${profile.deployment_profile}`;
      const adminVisible = Boolean(profile.admin_visible);
      el.adminCard.hidden = !adminVisible;
      el.continueAdmin.hidden = !adminVisible;
      if (!adminVisible) {
        setStatus("Client machine detected. Only Cadet login is available.");
      }
    } catch {
      el.accessProfile.textContent = "unavailable";
    }
  }

  async function loginStudent() {
    const studentId = (el.studentId.value || "").trim();
    const password = (el.studentPassword.value || "").trim();
    if (!studentId || !password) {
      setStatus("Student login ke liye Student ID aur password dono required hain.", true);
      return;
    }
    const session = await api("/student/login", {
      method: "POST",
      body: { student_id: studentId, password },
    });
    writeSession(STUDENT_SESSION_KEY, {
      student_id: session.student_id,
      display_name: session.display_name,
      logged_in_at: new Date().toISOString(),
    });
    window.location.href = "/web/student.html";
  }

  async function loginAdmin() {
    const adminId = (el.adminId.value || "").trim();
    const accessKey = (el.adminKey.value || "").trim();
    if (!adminId || !accessKey) {
      setStatus("Admin login ke liye Admin ID aur access key required hai.", true);
      return;
    }
    const session = await api("/system/admin-login", {
      method: "POST",
      body: { admin_id: adminId, access_key: accessKey },
    });
    writeSession(ADMIN_SESSION_KEY, {
      admin_id: session.admin_id,
      role: session.role,
      display_name: session.display_name,
      logged_in_at: new Date().toISOString(),
    });
    window.location.href = "/web/admin.html";
  }

  function continueSession(key, path, label) {
    const session = readSession(key);
    if (!session) {
      setStatus(`No active ${label} session found.`);
      return;
    }
    window.location.href = path;
  }

  function logoutAll() {
    localStorage.removeItem(STUDENT_SESSION_KEY);
    localStorage.removeItem(ADMIN_SESSION_KEY);
    setStatus("All sessions cleared. Fresh login required.");
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get("reason") === "login_required") {
    setStatus("Requested page open karne ke liye pehle login karo.", true);
  }
  if (params.get("reason") === "host_only") {
    setStatus("Admin panel sirf trusted host machine par available hai.", true);
  }

  el.studentLogin.addEventListener("click", () =>
    loginStudent().catch((error) => setStatus(error.message, true)),
  );
  el.adminLogin?.addEventListener("click", () =>
    loginAdmin().catch((error) => setStatus(error.message, true)),
  );
  el.continueStudent.addEventListener("click", () => continueSession(STUDENT_SESSION_KEY, "/web/student.html", "student"));
  el.continueAdmin.addEventListener("click", () => continueSession(ADMIN_SESSION_KEY, "/web/admin.html", "admin"));
  el.logoutAll.addEventListener("click", logoutAll);
  el.errorClose?.addEventListener("click", () => closeDialog(el.errorDialog));
  el.errorDialog?.addEventListener("click", (event) => {
    if (event.target === el.errorDialog) closeDialog(el.errorDialog);
  });
  loadPortalContext();
})();
