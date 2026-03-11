# NITMEXS Feature Roadmap

Last updated: 2026-03-11

## Legend
- `Already Done`: End-to-end working in current repo.
- `Partial`: Some primitives/UI/backend exist, but not full backlog behavior.
- `Missing`: Not implemented yet.

## Current Completion Snapshot (Post-Batch-3)
- Student: `30 / 50` fully done
- Admin: `11 / 50` fully done
- Overall full completion: `41 / 100 = 41%`

## Phase Plan
- `P0` (highest value + low risk): accessibility, exam-session resilience UX, admin operational controls, student/admin CSV friendliness, safe monitoring enrichments.
- `P1` (core UX/operations): scheduling, section-wise authoring, policy controls, candidate operations tooling, publishing hardening.
- `P2` (advanced analytics/AI assist): predictive analytics, distractor/cutoff simulators, AI drafting/remediation with human-in-loop controls.

## Student Backlog Audit (50)
| # | Feature | Status | Phase | Notes |
|---|---|---|---|---|
| 1 | First-time guided onboarding overlay | Already Done | P0 | First-run onboarding modal implemented with persistent seen-state. |
| 2 | Multi-language UI switch | Missing | P1 | Mixed static language text only. |
| 3 | Font size controls | Already Done | P0 | Added font-size selector with persisted preferences. |
| 4 | Dyslexia-friendly font mode | Missing | P1 | Not available in CSS/UI preferences. |
| 5 | High-contrast accessibility mode | Already Done | P0 | Added high-contrast toggle and student theme overrides. |
| 6 | Full keyboard-only navigation | Partial | P1 | Native browser tabbing exists; no explicit keyboard UX model. |
| 7 | Better screen-reader labels (ARIA) | Partial | P1 | Some labels exist, but no comprehensive ARIA pass. |
| 8 | Question text zoom | Already Done | P0 | Added question zoom controls and live zoom label. |
| 9 | Image zoom/pan in questions | Missing | P1 | No media viewer/zoom-pan controls. |
| 10 | Math equation renderer support | Missing | P1 | No KaTeX/MathJax or math parser integration. |
| 11 | Built-in rough work notepad | Missing | P0 | Not present in student workspace. |
| 12 | Configurable calculator (if allowed) | Missing | P1 | No policy-aware calculator module. |
| 13 | Formula sheet drawer (if allowed) | Missing | P1 | No exam-policy controlled formula drawer. |
| 14 | Hotkeys for mark/review/next | Already Done | P0 | Added keyboard shortcuts (`M`, `N`) plus `J` jump helper. |
| 15 | Live autosave indicator | Already Done | P0 | Dedicated autosave status indicator added (local/pending/synced). |
| 16 | LAN sync health indicator | Already Done | P0 | Dedicated LAN health indicator added (healthy/syncing/offline). |
| 17 | Auto retry on reconnect | Already Done | P0 | `online` event + periodic queue flush present. |
| 18 | Local encrypted answer cache | Missing | P1 | LocalStorage cache exists but not encrypted. |
| 19 | Crash recovery attempt restore | Already Done | P0 | Latest cached attempt restore implemented. |
| 20 | Accidental refresh/close guard | Already Done | P0 | `beforeunload` confirmation guard active during live attempt. |
| 21 | Optional confirm before leaving unanswered | Already Done | P0 | Configurable confirm toggle added with submit-time guard. |
| 22 | Section-wise progress bars | Missing | P1 | No section-level tracking UI/backend model. |
| 23 | Section-wise remaining time view | Missing | P1 | Global timer only. |
| 24 | Palette filters (answered/unanswered/review) | Already Done | P0 | Palette filter buttons added with active-state highlighting. |
| 25 | Jump-to-first-unanswered button | Already Done | P0 | Added direct jump action in palette controls and hotkey support. |
| 26 | Report question issue button | Already Done | P0 | Student can report question issue via API-backed quick action. |
| 27 | Technical issue quick report | Already Done | P0 | Student technical issue quick report API + UI added. |
| 28 | Low-time smart alerts | Already Done | P0 | Added staged low-time alerts at 5m/2m/1m thresholds. |
| 29 | Server heartbeat monitor | Already Done | P0 | Periodic heartbeat latency indicator added in student shell. |
| 30 | Inactivity warning prompt | Already Done | P0 | Added inactivity detector and resume modal prompt. |
| 31 | Fullscreen enforcement mode | Missing | P1 | Not implemented. |
| 32 | Copy-paste block during exam | Missing | P1 | No clipboard-block behavior in UI. |
| 33 | Right-click + context menu lock | Already Done | P0 | Context menu is disabled during attempt. |
| 34 | Tab-switch warning counter | Already Done | P0 | Visibility warning counter implemented and shown in submit summary. |
| 35 | Exam rules quick drawer | Already Done | P0 | Rules drawer with exam policy summary and checklist added. |
| 36 | AI morale coach cards (smart and contextual) | Partial | P2 | Basic morale endpoint/card exists; limited context depth. |
| 37 | Breathing/stress reset micro prompt | Already Done | P1 | 30-second guided breathing reset micro-prompt added. |
| 38 | Optional supervised break request | Missing | P1 | No break request workflow. |
| 39 | Read-aloud accessibility mode (policy based) | Missing | P2 | No TTS mode. |
| 40 | Quick FAQ/help panel | Already Done | P0 | In-context FAQ/help card available in exam sidebar. |
| 41 | Answer confidence tag (sure/maybe/guess) | Already Done | P1 | Confidence tag captured in payload and synced with answers. |
| 42 | Pre-submit revision mode | Already Done | P1 | Dedicated revision mode entry and guided navigation added. |
| 43 | Submit readiness checklist | Already Done | P0 | Checklist-style submit readiness with pass/warn signals added. |
| 44 | Visual result scorecard (non-JSON) | Already Done | P0 | Styled result summary card rendered in student UI. |
| 45 | Policy-based post-exam answer review | Missing | P1 | No policy gates or review endpoint. |
| 46 | Personal performance trend chart | Missing | P2 | No student-side trend visualization. |
| 47 | Digital acknowledgement receipt | Already Done | P0 | Receipt artifact generated after submission and persisted in UI state. |
| 48 | Printable result slip | Already Done | P0 | Printable slip action opens formatted print-ready receipt view. |
| 49 | OTP based re-entry after interruption | Missing | P2 | No OTP issuance/verification flow. |
| 50 | Pre-exam device diagnostics (keyboard/mouse/network) | Already Done | P0 | Device diagnostics panel checks keyboard/mouse/network/storage readiness. |

## Admin Backlog Audit (50)
| # | Feature | Status | Phase | Notes |
|---|---|---|---|---|
| 1 | Role-based admin accounts | Missing | P1 | Header-flag admin check only. |
| 2 | Admin PIN/MFA lock | Partial | P1 | Static demo access key only, no MFA/PIN flow. |
| 3 | Session timeout policy controls | Already Done | P0 | Idle lock timeout is now configurable and persisted in admin UI. |
| 4 | Two-step approval for critical actions | Missing | P1 | Not implemented. |
| 5 | Admin user management panel | Missing | P1 | Not implemented. |
| 6 | Student ID bulk import/export | Already Done | P0 | Added admin CSV import/export endpoints + UI controls + template. |
| 7 | Student batch/group management | Missing | P1 | No grouping model/UI. |
| 8 | Seat allotment planner | Missing | P1 | Not implemented. |
| 9 | Lab/room assignment map | Missing | P1 | Not implemented. |
| 10 | Exam scheduling calendar | Missing | P1 | Not implemented. |
| 11 | Time-window and blackout controls | Missing | P1 | Not implemented. |
| 12 | Reusable exam templates | Partial | P1 | Exam-package CSV helps bootstrap but no template lifecycle. |
| 13 | Section-wise exam builder | Missing | P1 | No section model/builder UI. |
| 14 | Drag-drop question ordering | Missing | P1 | Not implemented. |
| 15 | Randomization rule engine | Partial | P1 | Random shuffle exists; no configurable rule engine. |
| 16 | Unique paper generation per student | Already Done | P0 | Per-attempt randomized snapshots already generated. |
| 17 | Negative marking presets | Partial | P1 | Numeric field exists, no managed presets library. |
| 18 | Difficulty mix presets | Missing | P1 | Not implemented. |
| 19 | Topic quota enforcement | Missing | P1 | Not implemented. |
| 20 | Tag taxonomy manager | Partial | P1 | Topic tags exist at question level, no manager UI. |
| 21 | Duplicate question detector | Missing | P1 | Not implemented. |
| 22 | Media-rich question upload | Missing | P1 | Not implemented. |
| 23 | Equation editor for question creation | Missing | P1 | Not implemented. |
| 24 | Student-view preview mode | Already Done | P0 | Admin question table now supports student-view preview rendering. |
| 25 | Question quality validator | Missing | P1 | No validator tooling. |
| 26 | Bulk metadata edit tools | Partial | P1 | Recalibration updates metadata in bulk but not general bulk editor. |
| 27 | Archive/restore question sets | Missing | P1 | Not implemented. |
| 28 | Question version history | Missing | P1 | Not implemented. |
| 29 | Exam draft diff viewer | Missing | P2 | Not implemented. |
| 30 | Publish checklist with hard validation | Partial | P1 | Basic publish validation only (has questions + draft state). |
| 31 | Staged publishing per lab/batch | Missing | P1 | Not implemented. |
| 32 | Live lab-wise candidate map | Missing | P2 | No lab topology model or map. |
| 33 | Real-time incident stream | Already Done | P0 | Cursor-based proctor event stream endpoints/UI exists. |
| 34 | Cheat-risk scoring dashboard | Partial | P2 | Suspicious indicators/alerts exist, no richer scoring dashboard. |
| 35 | Proctor notes with evidence attachment | Missing | P1 | Not implemented. |
| 36 | One-way admin broadcast to candidates | Already Done | P0 | Admin exam broadcast endpoint + UI, student broadcast feed polling added. |
| 37 | Emergency pause/resume exam | Already Done | P0 | Exam-wide active attempt pause/resume controls added with audit trail. |
| 38 | Force-submit individual attempt | Already Done | P0 | Admin force-submit endpoint/UI available for single attempt. |
| 39 | Force-submit all expired attempts | Already Done | P0 | Admin bulk expired-attempt force-submit endpoint/UI available. |
| 40 | Deep audit explorer with filters | Already Done | P1 | Filterable audit explorer endpoint + admin table UI added. |
| 41 | DB integrity tamper alert panel | Missing | P2 | Not implemented. |
| 42 | Backup scheduler UI | Missing | P1 | Backup exists in CLI/service mode, no web scheduler UI. |
| 43 | Restore dry-run verification tool | Missing | P1 | Not implemented. |
| 44 | Infra health dashboard | Already Done | P0 | Consolidated infra health summary derived from metrics + proctor snapshot. |
| 45 | Rule-based alerts engine | Partial | P2 | Hardcoded suspicious rules exist, no configurable rule engine. |
| 46 | Trend analytics by exam/topic/batch | Partial | P2 | Exam/topic analytics present; no batch-trend slicing. |
| 47 | Distractor analysis per option | Missing | P2 | Not implemented. |
| 48 | Pass cutoff simulation tool | Missing | P2 | Not implemented. |
| 49 | AI question drafting assistant (human review mandatory) | Missing | P2 | Not implemented. |
| 50 | AI remediation planner for weak-topic improvement | Missing | P2 | Not implemented. |

## Batch Plan Log
| Batch | Scope | Feature count | Status |
|---|---|---:|---|
| Batch-1 | Student accessibility + session UX, Admin session policy + student CSV bulk ops | 12 | Completed |
| Batch-2 | Student resilience + readiness UX, Admin force-submit and question preview | 11 | Completed |
| Batch-3 | Student support/reporting/revision flows, Admin pause-resume-broadcast-audit-infra ops | 11 | Completed |

## Batch-1 Target Features
- Student: `#1, #3, #5, #8, #14, #15, #16, #25, #28, #30`
- Admin: `#3, #6`

## Batch-2 Target Features
- Student: `#20, #21, #24, #29, #40, #43, #47, #48, #50`
- Admin: `#24, #38, #39`

## Batch-3 Target Features
- Student: `#26, #27, #35, #37, #41, #42`
- Admin: `#36, #37, #40, #44, plus reliability hardening tests`

## CSV Simplification Direction
- Keep legacy question CSV import support unchanged.
- Keep simplified question/exam-package templates as preferred path.
- Add similarly simple student-id CSV template for new bulk import/export flow.
