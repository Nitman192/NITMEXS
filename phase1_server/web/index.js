(() => {
  const STUDENT_SESSION_KEY = "nitmexs_student_session";
  const ADMIN_SESSION_KEY = "nitmexs_admin_session";
  const $ = (id) => document.getElementById(id);
  const friendlyFieldLabel = (field) => {
    const map = {
      student_id: "Student ID",
      admin_id: "Admin ID",
      access_key: "access key",
      password: "password",
      display_name: "display name",
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
      return "This admin login works only on the trusted host machine.";
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
  const el = {
    version: $("version-badge"),
    accessProfile: $("access-profile-label"),
    studentId: $("student-login-id"),
    studentPassword: $("student-login-password"),
    studentPasswordToggle: $("student-login-password-toggle"),
    studentCapsWarning: $("student-login-caps-warning"),
    studentLogin: $("student-login-btn"),
    adminCard: $("admin-card"),
    adminId: $("admin-login-id"),
    adminKey: $("admin-login-key"),
    adminKeyToggle: $("admin-login-key-toggle"),
    adminCapsWarning: $("admin-login-caps-warning"),
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
    if (el.status) {
      el.status.textContent = String(message ?? "");
      el.status.classList.toggle("error", isError);
    }
    if (isError && message) showErrorDialog(message);
  };

  const bindPasswordControls = (input, toggle, warning) => {
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
      setStatus("Please enter Student ID and password.", true);
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
      setStatus("Please enter Admin ID and access key.", true);
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
    setStatus("Please sign in first to open that page.", true);
  }
  if (params.get("reason") === "host_only") {
    setStatus("The admin panel is available only on the trusted host machine.", true);
  }

  bindPasswordControls(el.studentPassword, el.studentPasswordToggle, el.studentCapsWarning);
  bindPasswordControls(el.adminKey, el.adminKeyToggle, el.adminCapsWarning);

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
