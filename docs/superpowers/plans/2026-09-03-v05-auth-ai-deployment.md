# Online Question Bank v0.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn v0.4 into a deployment-ready multi-user learning system with learner/admin separation, user-scoped data, refined knowledge tags, and advisory AI scoring for subjective answers.

**Architecture:** Keep the existing FastAPI + SQLAlchemy + Next.js stack and preserve SQLite upgrade compatibility. Add DB-backed users and bearer sessions, keep legacy local single-user mode when auth is disabled, scope all learner data by the authenticated user, and keep admin APIs role-protected. Add deterministic subject-specific knowledge tagging and an optional OpenAI Responses API grading adapter that only fills `suggested_score`; final scores remain human-controlled.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, standard-library PBKDF2 password hashing, httpx, pytest; Next.js 15, React 19, TypeScript; Docker Compose, SQLite persistent volume.

**Spec:** `docs/superpowers/specs/2026-09-02-online-question-bank-design.md`

## Global Constraints

- Existing v0.4 SQLite databases upgrade in place without losing attempts, wrong questions, favorites, reviews, papers, questions, or import jobs.
- Legacy local mode maps to seeded learner user id `1`; deployed auth mode requires login.
- Learners can only read/write their own attempts, wrong questions, favorites, history, and statistics.
- Admins can manage content, imports, backup/export, users, reviews, and AI suggestions.
- New passwords use PBKDF2-HMAC-SHA256 with per-user random salts; plaintext passwords are never stored.
- AI scoring is advisory only; it may update `suggested_score`, `comment`, and rubric suggestions but never `final_score` or answer grading status.
- Existing `QUESTION_BANK_ADMIN_TOKEN` remains a local/automation fallback only when auth-required mode is disabled.
- New question-bank imports write refined knowledge-point tags when deterministic rules are confident; manual admin edits remain authoritative.

---

### Task 1: Users, Sessions, Password Hashing, and Bootstrap

**Files:** create `models/user.py`, `schemas/auth.py`, `services/auth_service.py`, `routes/auth.py`; modify config/bootstrap/main; add `tests/test_auth.py`.

**Interfaces:** `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`; admin user CRUD under `/api/admin/users`.

- [ ] Write failing tests for local legacy user, deployed login, bad password, session expiry, learner/admin roles, and bootstrap admin.
- [ ] Implement password hashing/session tokens and bootstrap behavior.
- [ ] Run targeted then full tests.

### Task 2: User-Scoped Learner Data and Admin Authorization

**Files:** modify security, attempts/learning/statistics/reviews routes and services; add `tests/test_user_isolation.py`.

**Interfaces:** all learner APIs derive `user_id` from auth context; admin endpoints require admin role when auth is enabled.

- [ ] Write cross-user access failure tests for attempts, favorites, wrong questions, statistics, and history.
- [ ] Pass `current_user.id` through services and reject ownership mismatches.
- [ ] Preserve local mode behavior as user id 1.
- [ ] Run full tests.

### Task 3: Frontend Login, Session Cookie, and Admin/Learner Navigation

**Files:** create `/login`, `/api/session/login`, `/api/session/logout`, `/api/auth-proxy`; modify `lib/api.ts`, layout, home, admin proxy, admin navigation.

**Interfaces:** browser stores backend session token only in an HttpOnly cookie; server-side proxies attach bearer token.

- [ ] Add login/logout UI and role-aware navigation.
- [ ] Ensure learner pages never need the admin token.
- [ ] Keep local mode frictionless when auth is disabled.
- [ ] Run TypeScript/Next build where available.

### Task 4: Knowledge-Point Taxonomy and Real-Paper Enrichment

**Files:** create `services/knowledge_points.py`, `scripts/enrich_knowledge_points.py`; modify DOCX publisher; add `tests/test_knowledge_points.py`.

**Interfaces:** deterministic `infer_knowledge_points(subject_code, question_type, stem_html, material_html, section_title) -> list[str]`.

- [ ] Test Chinese, math, and English mappings against real-paper samples.
- [ ] Auto-tag only when non-empty; never overwrite existing manual tags unless explicitly requested by script.
- [ ] Add dry-run/apply enrichment script and real-six-paper coverage report.

### Task 5: Advisory AI Subjective Scoring

**Files:** create `models/ai_review.py`, `schemas/ai_review.py`, `services/ai_grading.py`, `routes/ai_reviews.py`; modify reviews UI; add `tests/test_ai_grading.py`.

**Interfaces:** `POST /api/admin/reviews/{answer_id}/ai-suggest` returns/stores suggestion; optional OpenAI Responses API provider configured by env; deterministic disabled-provider error when no key.

- [ ] Test prompt payload, structured result validation, score clamping/rejection, provider failure, idempotent persistence, and guarantee that `final_score` is unchanged.
- [ ] Implement current Responses API structured output request via `httpx`.
- [ ] Add admin UI button to request/refresh AI suggestion and copy suggestion into editable manual review form.

### Task 6: Deployment Hardening and Operations

**Files:** modify compose/env/README; create `scripts/create_admin.py`, `scripts/restore_db.py`, `scripts/healthcheck.py`; add `tests/test_deployment_config.py`.

**Interfaces:** Docker auth-required defaults, bootstrap admin env, health endpoints, persistent DB backup/restore workflow.

- [ ] Add `/api/health/live` and `/api/health/ready`.
- [ ] Update Docker healthcheck and auth-required env.
- [ ] Add backup restore safety checks and documented reverse-proxy/TLS boundary.
- [ ] Validate YAML structure and scripts.

### Task 7: Upgrade, Real-Data, and Package Verification

- [ ] Upgrade a v0.4 DB copy and verify legacy data maps to user id 1.
- [ ] Import/enrich the six real papers and report knowledge-point coverage.
- [ ] Run a two-user real-paper learning isolation smoke test.
- [ ] Run real subjective pending → AI suggestion fixture/provider → human final review → graded smoke test.
- [ ] Run full pytest, frontend static/build validation where available, `git diff --check`.
- [ ] Commit, export a clean ZIP, re-extract it, and repeat backend + real-data verification from the package.
