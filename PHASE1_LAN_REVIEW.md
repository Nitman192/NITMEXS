# Phase 1 FastAPI LAN Server Review (Target: 50 Concurrent Clients)

## Scope and Assumptions
This review focuses on a typical **Phase 1 offline/LAN FastAPI exam server** architecture (single app process, SQLite backend, session-based exam flow).  
Because the repository currently contains architecture docs only (no FastAPI source files), the findings below are structured as a **gap-oriented review checklist** and a practical refactor plan you can apply to the implementation without a full rewrite.

---

## 1) Architectural Weaknesses

### 1.1 Single-process bottleneck
**Weakness**
- Running one Uvicorn worker with in-process state (active sessions, timers, candidate maps).

**Why it hurts at 50 clients**
- CPU-bound grading or heavy endpoints can block request handling.
- Any process restart can drop in-memory exam state.

**Refactor direction**
- Move volatile exam/session state from memory to persistence-backed services (SQLite tables + cache abstraction).
- Run multiple workers (if deployment allows) only after state externalization.

---

### 1.2 MVC boundary leakage
**Weakness**
- Route handlers often contain validation, rules, SQL calls, and response formatting together.

**Risk**
- High change cost and regression risk when introducing adaptive logic or analytics events.

**Refactor direction**
- Enforce 4 explicit layers:
  1) API routers (transport)
  2) Application services (use-cases)
  3) Domain services/policies (rules)
  4) Repository/data layer (SQL only)

---

### 1.3 SQLite contention under bursty writes
**Weakness**
- Frequent autosave writes per client (e.g., every answer/timer tick) to same DB without write-throttling.

**Risk at 50 clients**
- `database is locked` errors, latency spikes, and retries cascading.

**Refactor direction**
- WAL mode + `busy_timeout` + bounded write queue.
- Store only answer deltas; batch non-critical telemetry writes.
- Add indexes for `attempt_id`, `candidate_id`, `question_id`, `submitted_at`.

---

### 1.4 No explicit state machine for attempt lifecycle
**Weakness**
- Implicit status checks in multiple endpoints.

**Risk**
- Invalid transitions (double submit, edit after submit, grading before close).

**Refactor direction**
- Centralize attempt transitions in `AttemptStateService` with strict guards and audit logs.

---

### 1.5 Tight coupling between delivery and grading
**Weakness**
- Submission endpoint performs full grading synchronously.

**Risk**
- Slow final submit, timeout risk, poor UX when many candidates submit together.

**Refactor direction**
- Split into `FinalizeAttempt` (sync, fast) and `GradeAttempt` (async background job).

---

## 2) Scalability Risks for 50-Client LAN Deployment

### 2.1 Request storm during autosave
- If all clients autosave every N seconds, writes align and spike.
- **Mitigation:** jitter autosave interval (e.g., 8–15s randomized), server-side debounce.

### 2.2 Hot endpoints without caching
- Re-fetching static exam metadata repeatedly creates avoidable DB reads.
- **Mitigation:** immutable exam snapshot cache keyed by `exam_version_id`.

### 2.3 Unbounded payload and N+1 query patterns
- Large response payloads (full question set every request) and per-question DB loops.
- **Mitigation:** pagination/section fetch, select-only needed columns, prefetch strategy.

### 2.4 Lack of backpressure and rate limits
- A misbehaving client can starve resources.
- **Mitigation:** per-IP/per-session request limits and max concurrent in-flight requests.

### 2.5 Operational blind spots
- No latency/error metrics means bottlenecks are discovered too late.
- **Mitigation:** endpoint timing, DB timing, queue depth, autosave failure rate, submission SLA.

---

## 3) Security Gaps (LAN ≠ Trusted)

### 3.1 Weak authentication/session model
- Risk: predictable tokens, long-lived sessions, missing device binding.
- **Fix:** short-lived signed tokens, rotation, device/session fingerprint checks.

### 3.2 Missing authorization boundaries
- Risk: candidate endpoint access by proctor/admin or cross-attempt data leakage.
- **Fix:** RBAC + ownership checks in service layer, not only routers.

### 3.3 Transport and replay risks
- Risk: plain HTTP on LAN allows sniffing/replay.
- **Fix:** TLS in LAN where feasible; nonce/timestamp validation for critical actions.

### 3.4 Input validation gaps
- Risk: malformed JSON, oversized payloads, injection vectors in dynamic query composition.
- **Fix:** strict Pydantic schemas, payload limits, parameterized SQL only.

### 3.5 Insufficient auditability
- Risk: disputes cannot be resolved for “who changed what and when”.
- **Fix:** append-only `audit_events` with actor, action, target, timestamp, hash chain optional.

### 3.6 Secrets and local data exposure
- Risk: plaintext admin credentials or DB files readable on host.
- **Fix:** salted password hashing (Argon2/bcrypt), OS file permissions, encrypted backups.

---

## 4) Structured Refactor Plan (No Full Rewrite)

## Phase A (Week 1): Stabilize Runtime and Data Access
1. Add DB hardening defaults:
   - Enable WAL, busy timeout, tuned pragmas.
   - Introduce connection/session management per request.
2. Create repository interfaces and move SQL out of routers.
3. Add idempotency keys for submit/finalize operations.

**Deliverables**
- `repositories/` package, DB config module, migration for indexes.

---

## Phase B (Week 2): Enforce Domain Workflow
1. Introduce `AttemptStateService` with explicit state transition table.
2. Move exam rules to `RuleEngine` (timing, section lock, marking policy).
3. Normalize error model (`DomainError` -> API error mapper).

**Deliverables**
- State transition tests and rule unit tests.

---

## Phase C (Week 3): Submission/Grading Decoupling
1. Refactor submit endpoint into:
   - `POST /attempts/{id}/finalize` (atomic close)
   - background `grade_attempt(id)` worker
2. Persist grading jobs table (`pending/running/done/failed`).
3. Add retry with bounded attempts and dead-letter status.

**Deliverables**
- Background worker module, grading job schema, operational dashboard fields.

---

## Phase D (Week 4): Security and Abuse Controls
1. Harden auth/session lifecycle (expiration, rotation, invalidation).
2. Add RBAC and ownership guards to application services.
3. Add request limits and payload caps.
4. Add audit event logging for auth, exam start, autosave, submit, grade.

**Deliverables**
- Security middleware, policy checks, audit event repository.

---

## Phase E (Week 5): Observability and Capacity Validation
1. Instrument metrics:
   - p95/p99 latency per endpoint
   - DB lock wait time
   - autosave success rate
   - finalize-to-score SLA
2. Run LAN load test at 50 virtual clients with realistic autosave cadence.
3. Tune based on evidence (query plans, index adjustments, queue sizing).

**Deliverables**
- Load test report, tuning changelog, go-live acceptance checklist.

---

## 5) Minimal Target Architecture After Refactor

```text
[FastAPI Routers]
     -> [Application Services / Use Cases]
         -> [Domain Services: RuleEngine, AttemptStateService, GradingPolicy]
             -> [Repositories + UnitOfWork]
                 -> [SQLite (WAL) + Audit/Event tables]

Background Worker:
[Grading Job Runner] -> [Repositories] -> [SQLite]
```

This preserves the current stack and project direction while removing the main blockers for a reliable 50-client LAN exam session.

---

## 6) Prioritized Risk Register
1. **High:** SQLite write contention during autosave bursts.
2. **High:** Missing lifecycle state machine causing invalid attempt transitions.
3. **High:** Weak auth/RBAC boundaries in LAN assumptions.
4. **Medium:** Synchronous grading path under concurrent submissions.
5. **Medium:** Limited observability delaying incident response.

Addressing the top 3 first gives the largest stability and integrity gains with minimal rewrites.
