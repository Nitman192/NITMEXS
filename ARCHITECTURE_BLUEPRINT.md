# Offline Python Examination System Architecture Blueprint

## 1) Layer Diagram

```text
+-----------------------------------------------------------------------------------+
|                                   Presentation Layer                              |
|-----------------------------------------------------------------------------------|
| Desktop/Web UI (Offline) | CLI Admin Console | Proctor Dashboard (Local Network) |
+------------------------------------------|----------------------------------------+
                                           v
+-----------------------------------------------------------------------------------+
|                                  Application Layer                                |
|-----------------------------------------------------------------------------------|
| Exam Session Controller | Authentication Controller | Scheduling Controller        |
| Submission Controller   | Evaluation Controller     | Sync Controller (optional)   |
+------------------------------------------|----------------------------------------+
                                           v
+-----------------------------------------------------------------------------------+
|                                   Domain Layer (MVC)                              |
|-----------------------------------------------------------------------------------|
| Models: User, Candidate, Exam, Question, Attempt, Response, Result, AuditEvent   |
| Services: ExamEngine, RuleEngine, GradingEngine, TimerService, IntegrityService   |
| Policies: AccessPolicy, AttemptPolicy, ScoringPolicy                               |
+------------------------------------------|----------------------------------------+
                                           v
+-----------------------------------------------------------------------------------+
|                              Data Access & Persistence Layer                       |
|-----------------------------------------------------------------------------------|
| Repositories (UserRepo, ExamRepo, AttemptRepo, AnalyticsRepo)                     |
| UnitOfWork / Transaction Manager | SQLite Adapter | Migration Manager              |
| Local File Store (encrypted media, logs, exports, backups)                        |
+------------------------------------------|----------------------------------------+
                                           v
+-----------------------------------------------------------------------------------+
|                                 Infrastructure Layer                               |
|-----------------------------------------------------------------------------------|
| SQLite DB | Encryption Key Store | Background Workers | Monitoring/Telemetry       |
| Config Manager | Plugin Loader (future extensibility)                              |
+-----------------------------------------------------------------------------------+
```

---

## 2) Module Responsibilities

### A. Presentation Layer
- **Candidate UI**
  - Exam onboarding, question navigation, timer display, autosave indicators.
  - Local caching of in-progress answers for resilience.
- **Admin UI**
  - Exam authoring, scheduling, user enrollment, and report export.
- **Proctor UI**
  - Live local status (connected clients, suspicious events, submission progress).

### B. Controller Layer (MVC Controller)
- **AuthenticationController**
  - Login/session lifecycle, role-based access control (RBAC), lockout policies.
- **ExamSessionController**
  - Start/pause/resume exam, enforce timing windows, route question flow.
- **SubmissionController**
  - Autosave and final submit workflow, idempotent submit handling.
- **EvaluationController**
  - Trigger objective grading and queue subjective/manual review.
- **SchedulingController**
  - Exam windows, seat allocations, and offline availability policies.

### C. Domain Layer (MVC Model + Business Services)
- **Core Models**
  - `User`, `Role`, `CandidateProfile`, `Exam`, `Section`, `Question`, `Option`, `Attempt`, `Response`, `Score`, `AuditEvent`.
- **ExamEngine**
  - Orchestrates exam state machine: `Draft -> Published -> Scheduled -> Active -> Closed -> Archived`.
- **RuleEngine**
  - Encodes constraints (negative marking, section cutoffs, attempt limits, randomization rules).
- **GradingEngine**
  - Objective grading (MCQ, true/false, matching), normalized scoring, partial marks.
- **IntegrityService**
  - Detects anomalies (rapid answer toggles, out-of-focus events if desktop app supports it).
- **TimerService**
  - Authoritative countdown and grace period handling.

### D. Data Access Layer
- **Repository Pattern**
  - Abstracts SQLite operations and isolates SQL from business logic.
- **UnitOfWork**
  - Groups operations into atomic transactions (attempt start, answer save, final submission).
- **Migration Manager**
  - Versioned schema updates for safe upgrades.
- **Event Store Table(s)**
  - Captures immutable audit trail and future analytics events.

### E. Infrastructure Layer
- **SQLite Engine**
  - WAL mode, periodic checkpointing, index tuning for read-heavy exam operations.
- **Encryption Module**
  - Database-at-rest encryption and secure key retrieval.
- **Background Workers**
  - Backup, export, deferred grading, local sync packaging.
- **Config Manager**
  - Environment-specific settings (lab mode, standalone mode, institution mode).

---

## 3) Data Flow

### Flow 1: Candidate Login and Exam Launch
1. Candidate authenticates via `AuthenticationController`.
2. Controller validates credentials and role using `UserRepo`.
3. Eligible exams fetched via `ExamRepo` and policy checks in `AccessPolicy`.
4. `ExamSessionController` creates `Attempt` in transaction (`UnitOfWork`).
5. UI receives randomized question order from `ExamEngine`.

### Flow 2: In-Exam Autosave
1. Candidate answers question.
2. UI sends response delta to `SubmissionController`.
3. `SubmissionController` validates current attempt state and time eligibility.
4. `AttemptRepo.save_response()` persists response and timestamp.
5. `AuditEvent` recorded for traceability.

### Flow 3: Final Submission and Grading
1. Candidate clicks submit or timer expires.
2. `SubmissionController` closes attempt atomically.
3. `EvaluationController` invokes `GradingEngine` for objective items.
4. Scores persisted to `Result` and `ScoreBreakdown`.
5. Admin/proctor UI reads summarized outcomes and exceptions.

### Flow 4: Reporting and Export
1. Admin requests report.
2. `AnalyticsRepo` runs aggregated queries (section accuracy, time per question).
3. Export service generates CSV/PDF for offline sharing.

---

## 4) Design Decisions

- **MVC Separation for Maintainability**
  - UI evolution does not impact grading/business rules; models remain framework-agnostic.
- **SQLite for Offline-First Reliability**
  - Single-file DB simplifies deployment in labs/remote centers with poor connectivity.
- **Repository + UnitOfWork for Scalability of Codebase**
  - Enables swap from SQLite to PostgreSQL later with minimal domain impact.
- **Event/Audit-Driven Internal Logging**
  - Supports compliance, dispute resolution, and analytics without redesign.
- **State Machine for Attempt Lifecycle**
  - Prevents invalid transitions (e.g., grading before submission).
- **WAL and Batched Writes**
  - Improves concurrency for many simultaneous local clients.
- **Policy/Rule Engines**
  - Exam rules configurable per institution/exam type without controller rewrites.

---

## 5) Future Upgrade Plan (Adaptive Testing + Analytics)

### Phase 1: Analytics Foundation
- Introduce **event schema standardization** (`event_type`, `actor_id`, `attempt_id`, `payload_json`, `ts`).
- Build materialized analytics views for:
  - Item difficulty index
  - Distractor analysis
  - Candidate pacing patterns
- Add local dashboard widgets for cohort performance trends.

### Phase 2: Adaptive Testing Readiness
- Add **Item Bank Module** with metadata:
  - Difficulty, discrimination, topic tags, cognitive level.
- Extend `ExamEngine` to support **section-level adaptive routing**.
- Implement **AdaptivePolicyService**:
  - Next-question selection based on running ability estimate.
- Keep deterministic fallback mode for auditability in regulated exams.

### Phase 3: Hybrid Sync & Central Insights
- Add optional **Sync Gateway** for periodic upload of anonymized events when internet is available.
- Central service computes cross-center analytics and sends updated calibrated item parameters.
- Plugin architecture allows enabling/disabling sync per deployment.

### Phase 4: Advanced Intelligence
- Add psychometric modules (IRT-based scoring, test form equating).
- Add anomaly detection models (potential collusion or guessing behavior).
- Add recommendation engine for remediation content by weak topic clusters.

---

## Suggested SQLite Schema Domains (High-Level)
- **Identity**: users, roles, permissions, candidate_profiles
- **Assessment**: exams, sections, questions, options, exam_versions
- **Delivery**: attempts, responses, timers, proctor_events
- **Evaluation**: scores, rubrics, manual_reviews
- **Observability**: audit_events, system_events, sync_queue

This structure keeps the system modular, offline-capable, and ready for progressive enhancement into adaptive and analytics-heavy scenarios without re-architecting the core.
