(() => {
  const THEME_MODE_KEY = "nitmexs_theme_mode";

  function isValidTheme(value) {
    return value === "dark" || value === "light";
  }

  function preferredTheme() {
    const stored = localStorage.getItem(THEME_MODE_KEY);
    if (isValidTheme(stored)) {
      return stored;
    }

    const defaultTheme = document.body?.dataset?.defaultTheme;
    if (isValidTheme(defaultTheme)) {
      return defaultTheme;
    }

    return "dark";
  }

  function updateToggleLabels(mode) {
    const labelText =
      mode === "dark"
        ? window.NITMEXSUILabels?.get("common.theme_dark", "Dark") || "Dark"
        : window.NITMEXSUILabels?.get("common.theme_light", "Light") || "Light";
    const labels = document.querySelectorAll("[data-theme-label]");
    labels.forEach((label) => {
      label.textContent = labelText;
    });
  }

  function syncToggleChecked(mode) {
    const toggles = document.querySelectorAll("[data-theme-toggle]");
    toggles.forEach((toggle) => {
      if (toggle instanceof HTMLInputElement) {
        toggle.checked = mode === "dark";
      }
    });
  }

  function applyTheme(mode) {
    const resolved = isValidTheme(mode) ? mode : preferredTheme();
    document.body.classList.remove("theme-dark", "theme-light");
    document.body.classList.add(`theme-${resolved}`);
    updateToggleLabels(resolved);
    syncToggleChecked(resolved);
  }

  function saveTheme(mode) {
    if (!isValidTheme(mode)) {
      return;
    }
    localStorage.setItem(THEME_MODE_KEY, mode);
  }

  function bindThemeToggles() {
    const toggles = document.querySelectorAll("[data-theme-toggle]");
    toggles.forEach((toggle) => {
      if (!(toggle instanceof HTMLInputElement)) {
        return;
      }
      toggle.addEventListener("change", () => {
        const nextMode = toggle.checked ? "dark" : "light";
        saveTheme(nextMode);
        applyTheme(nextMode);
      });
    });
  }

  function initTheme() {
    applyTheme(preferredTheme());
    bindThemeToggles();
  }

  window.NITMEXSTheme = {
    applyTheme,
    initTheme,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTheme, { once: true });
  } else {
    initTheme();
  }
})();
