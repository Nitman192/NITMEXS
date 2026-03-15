(() => {
  const catalog = {
    strings: {
      "common.brand_short": "NITMEXS",
      "common.brand_full": "Networked Integrated Training, Monitoring, Evaluation and eXamination Suite",
      "common.theme_dark": "Dark",
      "common.theme_light": "Light",
      "common.logout": "Logout",
      "common.downloads": "Downloads",
      "common.close": "Close",
      "common.ok": "OK",

      "gateway.badge": "NITMEXS EXAM SYSTEM",
      "gateway.title": "Examination Gateway",
      "gateway.subtitle_small": "Web Control Gateway",
      "gateway.subtitle_main": "Trusted host machine par Exam Controller aur Cadet login dono dikhenge. Network clients par sirf Cadet login available hoga.",
      "gateway.student_zone": "CADET ZONE",
      "gateway.student_login_title": "Student Login",
      "gateway.student_login_text": "Student ID aur password enter karke NITMEXS exam console open karo.",
      "gateway.student_id_placeholder": "Student ID (example: cadet-01)",
      "gateway.student_password_placeholder": "Password",
      "gateway.student_login_button": "Login As Cadet",
      "gateway.admin_zone": "EXAM CONTROLLER",
      "gateway.admin_login_title": "Admin Login",
      "gateway.admin_login_text": "Yeh panel sirf trusted host machine par available hai.",
      "gateway.admin_id_placeholder": "Admin ID (example: superadmin)",
      "gateway.admin_key_placeholder": "Access Key",
      "gateway.admin_login_button": "Login As Exam Controller",
      "gateway.session_control": "SESSION CONTROL",
      "gateway.quick_access": "Quick Access",
      "gateway.continue_student": "Continue Cadet Session",
      "gateway.continue_admin": "Continue Admin Session",
      "gateway.logout_all": "Logout All",

      "student.mode_kicker": "NITMEXS EXAM MODE",
      "student.console_title": "Cadet Examination Console",
      "student.console_subtitle": "Controlled three-stage examination workflow.",
      "student.tools": "Tools",
      "student.shortcuts": "Shortcuts",
      "student.stage_lobby": "1. Pre-Exam Lobby",
      "student.stage_exam": "2. Active Exam",
      "student.stage_submission": "3. Exam Submission",
      "student.select_exam_title": "Select Exam",
      "student.refresh_exams": "Refresh Exams",
      "student.exam_select_label": "Choose an Available Exam",
      "student.exam_select_placeholder": "Choose an available exam...",
      "student.reference_exam": "Reference Exam",
      "student.start_exam": "Start Exam",
      "student.exam_status": "Exam Status",
      "student.font_size": "Font Size",
      "student.device_diagnostics": "Device Diagnostics",
      "student.run_diagnostics": "Run Diagnostics",
      "student.exam_rules": "Exam Rules",
      "student.active_exam_title": "Exam",
      "student.support_toggle": "Exam Support Panel",
      "student.diagram_toggle": "Diagram Canvas",
      "student.input_tools_toggle": "Input Tools",
      "student.question_viewer": "Question Viewer",
      "student.answer_label": "Answer",
      "student.mark_review": "Mark Current Question",
      "student.unmark_review": "Unmark Current Question",
      "student.previous": "Previous",
      "student.save_next": "Save & Next",
      "student.jump_unanswered": "Jump to First Unanswered",
      "student.report_question_issue": "Report Question Issue",
      "student.report_technical_issue": "Report Technical Issue",
      "student.submit_exam": "Submit Exam",
      "student.time_left": "Time Left",
      "student.live_status": "Live Status Tracker",
      "student.attempted": "Attempted",
      "student.remaining": "Remaining",
      "student.marked_review_prefix": "Marked for review",
      "student.submission_title": "Exam Submission",
      "student.reference_modal_title": "Reference Exam",
      "student.shortcuts_modal_title": "Keyboard Shortcuts",
      "student.submission_modal_title": "Exam Submitted",
      "student.broadcast_modal_title": "Broadcast Message",
      "student.virtual_keyboard_note": "Virtual keyboard is available only for text-entry questions.",
      "student.support_help_text": "Need help? Use technical issue reporting if input or screen behavior is affected.",
      "student.support_broadcast_text": "Broadcasts from Exam Controller will appear below when available.",
      "student.answer_prompt_mcq": "Choose One Option",
      "student.answer_prompt_tf": "Select True or False",
      "student.answer_prompt_fib": "Type the missing word or phrase",
      "student.answer_prompt_subjective": "Write your answer",
      "student.option_selected": "Selected",
      "student.word_counter_prefix": "Words",
      "student.clear_canvas": "Clear",

      "admin.drawer_title": "Control Drawer",
      "admin.drawer_nav": "Navigation",
      "admin.drawer_collapse": "Collapse",
      "admin.drawer_expand": "Expand",
      "admin.dashboard_tab": "Dashboard",
      "admin.exams_tab": "Exams",
      "admin.questions_tab": "Questions",
      "admin.cadets_tab": "Cadets",
      "admin.live_tab": "Live Control",
      "admin.review_tab": "Review",
      "admin.results_tab": "Results",
      "admin.downloads_tab": "Downloads",
      "admin.audit_tab": "Audit",
      "admin.security_tab": "Security",
      "admin.exam_context": "Exam Context",
      "admin.load_exams": "Load Exams",
      "admin.reference_exam_placeholder": "Reference exam (optional)",
      "admin.new_exam_name_placeholder": "New exam name",
      "admin.exam_duration_placeholder": "Duration in minutes (example: 60)",
      "admin.negative_marking_placeholder": "Negative marking (example: 0.25)",
      "admin.save_reference_exam": "Save Reference Exam",
      "admin.quick_dashboard": "Quick Dashboard",
      "admin.exam_scope": "Exam Scope",
      "admin.custom_exam_rules": "Custom Exam Rules",
      "admin.difficulty_easy": "Easy",
      "admin.difficulty_medium": "Medium",
      "admin.difficulty_hard": "Hard",
      "admin.question_setup": "Question and Reference Setup",
      "admin.question_authoring": "Question Authoring",
      "admin.question_bank": "Question Bank",
      "admin.cadet_registry": "Cadet Registry",
      "admin.exam_control": "Exam Control",
      "admin.fib_review": "FIB Review Queue",
      "admin.subjective_review": "Subjective Review Queue",
      "admin.results_export": "Result Publication & Export",
      "admin.exam_summary": "Exam Summary",
      "admin.detailed_analytics": "Detailed Analytics",
      "admin.access_health_audit": "Access and Health Audit",
      "admin.deep_audit": "Deep Audit Explorer",
      "admin.system_security": "System Security",
      "admin.admin_accounts": "Admin Accounts",
      "admin.generated_artifacts": "Generated Artifacts",
    },
    pages: {
      gateway: {
        title: "NITMEXS Examination Gateway | Web Control Gateway",
        text: {
          ".chip": "gateway.badge",
          ".portal-header h1": "gateway.title",
          ".portal-header > .small": "gateway.subtitle_small",
          ".portal-header .subtitle": "gateway.subtitle_main",
          ".portal-grid .portal-card:first-child .card-kicker": "gateway.student_zone",
          ".portal-grid .portal-card:first-child h2": "gateway.student_login_title",
          ".portal-grid .portal-card:first-child > p:not(.card-kicker)": "gateway.student_login_text",
          "#student-login-btn": "gateway.student_login_button",
          "#admin-card .card-kicker": "gateway.admin_zone",
          "#admin-card h2": "gateway.admin_login_title",
          "#admin-card > p:not(.card-kicker):not(.small)": "gateway.admin_login_text",
          "#admin-login-btn": "gateway.admin_login_button",
          "section.portal-card .card-kicker": "gateway.session_control",
          "section.portal-card h2": "gateway.quick_access",
          "#continue-student": "gateway.continue_student",
          "#continue-admin": "gateway.continue_admin",
          "#logout-all": "gateway.logout_all",
        },
        attrs: {
          "#student-login-id": { placeholder: "gateway.student_id_placeholder" },
          "#student-login-password": { placeholder: "gateway.student_password_placeholder" },
          "#admin-login-id": { placeholder: "gateway.admin_id_placeholder" },
          "#admin-login-key": { placeholder: "gateway.admin_key_placeholder" },
        },
      },
      student: {
        title: "NITMEXS Examination",
        text: {
          ".student-kicker": "student.mode_kicker",
          ".student-header h1": "student.console_title",
          ".student-subtitle": "student.console_subtitle",
          ".army-tools-menu summary": "student.tools",
          "#open-shortcuts": "student.shortcuts",
          "#logout-student": "common.logout",
          "#stage-pill-lobby": "student.stage_lobby",
          "#stage-pill-exam": "student.stage_exam",
          "#stage-pill-submission": "student.stage_submission",
          "#student-stage-lobby .army-panel-block:first-child h2": "student.select_exam_title",
          "#load-exams": "student.refresh_exams",
          "#student-stage-lobby .army-panel-block:first-child label[for='exam-select']": "student.exam_select_label",
          "#preview-reference": "student.reference_exam",
          "#start-attempt": "student.start_exam",
          ".status-strip .status-label": "student.exam_status",
          ".utility-field[for='font-size-select']": "student.font_size",
          "#student-stage-lobby .army-panel-block:last-child h2": "student.device_diagnostics",
          "#run-diagnostics": "student.run_diagnostics",
          "#student-stage-lobby .army-panel-block:last-child h3": "student.exam_rules",
          "#toggle-support": "student.support_toggle",
          "#toggle-diagram": "student.diagram_toggle",
          "#toggle-input-tools": "student.input_tools_toggle",
          ".question-viewer h3": "student.question_viewer",
          "#answer-label": "student.answer_label",
          "#mark-review": "student.mark_review",
          "#prev-question": "student.previous",
          "#save-next": "student.save_next",
          "#jump-unanswered": "student.jump_unanswered",
          "#report-question-issue": "student.report_question_issue",
          "#report-technical-issue": "student.report_technical_issue",
          "#submit-exam": "student.submit_exam",
          ".compact-timer .section-label": "student.time_left",
          ".army-status-card .section-label": "student.live_status",
          ".army-counter-row > div:first-child .army-counter-label": "student.attempted",
          ".army-counter-row > div:last-child .army-counter-label": "student.remaining",
          ".army-submission-stage h2": "student.submission_title",
          "#reference-modal h3": "student.reference_modal_title",
          "#close-reference": "common.close",
          "#shortcuts-modal h3": "student.shortcuts_modal_title",
          "#close-shortcuts": "common.close",
          "#submission-modal-ok": "common.ok",
          "#broadcast-modal-ok": "common.ok",
          "#broadcast-modal h3": "student.broadcast_modal_title",
          "#input-tools-panel .box.small p": "student.virtual_keyboard_note",
          "#support-panel .box.small p:first-child": "student.support_help_text",
          "#support-panel .box.small p:nth-child(2)": "student.support_broadcast_text",
          "#clear-diagram": "student.clear_canvas",
          "#final-logout": "common.logout",
        },
        attrs: {
          "#exam-select option[value='']": { text: "student.exam_select_placeholder" },
        },
      },
      admin: {
        title: "NITMEXS Exam Controller Console",
        text: {
          ".admin-brand-mark": "common.brand_short",
          ".admin-brand-subline": "common.brand_full",
          "#open-downloads-top": "common.downloads",
          "#logout-admin": "common.logout",
          ".admin-context-bar h2": "admin.exam_context",
          "#load-exams": "admin.load_exams",
          "#save-reference-exam": "admin.save_reference_exam",
          ".admin-drawer-head .small": "admin.drawer_nav",
          ".admin-drawer-head strong": "admin.drawer_title",
          "[data-admin-tab='dashboard']": "admin.dashboard_tab",
          "[data-admin-tab='exams']": "admin.exams_tab",
          "[data-admin-tab='questions']": "admin.questions_tab",
          "[data-admin-tab='cadets']": "admin.cadets_tab",
          "[data-admin-tab='live']": "admin.live_tab",
          "[data-admin-tab='review']": "admin.review_tab",
          "[data-admin-tab='results']": "admin.results_tab",
          "[data-admin-tab='downloads']": "admin.downloads_tab",
          "[data-admin-tab='audit']": "admin.audit_tab",
          "[data-admin-tab='security']": "admin.security_tab",
          "[data-admin-panel='dashboard'] h2": "admin.quick_dashboard",
          "[data-admin-panel='exams'] h2": "admin.exam_scope",
          "label[for='custom-rules-text'] strong": "admin.custom_exam_rules",
          "[data-admin-panel='questions'] .panel:first-child h2": "admin.question_setup",
          "[data-admin-panel='questions'] .panel:nth-child(2) h2": "admin.question_authoring",
          "[data-admin-panel='questions'] .panel:nth-child(3) h2": "admin.question_bank",
          "#question-difficulty option[value='easy']": "admin.difficulty_easy",
          "#question-difficulty option[value='medium']": "admin.difficulty_medium",
          "#question-difficulty option[value='hard']": "admin.difficulty_hard",
          "[data-admin-panel='cadets'] h2": "admin.cadet_registry",
          "[data-admin-panel='live'] .panel:first-child h2": "admin.exam_control",
          "[data-admin-panel='review'] .panel:first-child h2": "admin.fib_review",
          "[data-admin-panel='review'] .panel:nth-child(2) h2": "admin.subjective_review",
          "[data-admin-panel='results'] .panel:first-child h2": "admin.results_export",
          "[data-admin-panel='results'] .panel:nth-child(2) h2": "admin.exam_summary",
          "[data-admin-panel='results'] .panel:nth-child(3) h2": "admin.detailed_analytics",
          "[data-admin-panel='downloads'] .panel:last-child h2": "admin.generated_artifacts",
          "[data-admin-panel='audit'] .panel:first-child h2": "admin.access_health_audit",
          "[data-admin-panel='audit'] .panel:nth-child(2) h2": "admin.deep_audit",
          "[data-admin-panel='security'] .panel:first-child h2": "admin.system_security",
          "#admin-accounts-panel h2": "admin.admin_accounts",
        },
        attrs: {
          "#new-exam-name": { placeholder: "admin.new_exam_name_placeholder" },
          "#new-exam-duration": { placeholder: "admin.exam_duration_placeholder" },
          "#new-exam-negative-marking": { placeholder: "admin.negative_marking_placeholder" },
        },
      },
    },
  };

  function get(path, fallback = "") {
    return catalog.strings[path] ?? fallback;
  }

  function inferPage() {
    if (document.body?.classList.contains("student-body")) return "student";
    if (document.body?.classList.contains("admin-shell")) return "admin";
    if (document.body?.classList.contains("portal-body")) return "gateway";
    return "";
  }

  function applyText(selector, value, root = document) {
    root.querySelectorAll(selector).forEach((node) => {
      node.textContent = value;
    });
  }

  function applyAttributes(selector, attrMap, root = document) {
    root.querySelectorAll(selector).forEach((node) => {
      Object.entries(attrMap).forEach(([attrName, labelKey]) => {
        const value = get(labelKey, "");
        if (value) {
          if (attrName === "text") node.textContent = value;
          else node.setAttribute(attrName, value);
        }
      });
    });
  }

  function apply(pageName = inferPage(), root = document) {
    const page = catalog.pages[pageName];
    if (!page) return;
    if (page.title) {
      document.title = page.title;
    }
    Object.entries(page.text || {}).forEach(([selector, labelKey]) => {
      applyText(selector, get(labelKey, ""), root);
    });
    Object.entries(page.attrs || {}).forEach(([selector, attrMap]) => {
      applyAttributes(selector, attrMap, root);
    });
  }

  window.NITMEXSUILabels = {
    catalog,
    get,
    apply,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => apply(), { once: true });
  } else {
    apply();
  }
})();
