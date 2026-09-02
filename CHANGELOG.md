# Changelog

## v0.5

- Add DB-backed learner/admin users, PBKDF2 password hashing, random bearer sessions, login/logout/me APIs, and admin user management.
- Preserve v0.4 data by promoting the legacy `user_id=1` local placeholder in place when authentication is first enabled.
- Scope attempts, answers, favorites, wrong questions, history, and statistics to the authenticated learner.
- Add HttpOnly-cookie Next.js session handling plus same-origin learner/admin API proxies and server-side admin route guarding.
- Add deterministic Chinese/math/English knowledge-point taxonomy, publish-time tagging, and dry-run/apply enrichment tooling.
- Add optional advisory OpenAI Responses API subjective scoring with strict structured outputs; AI never writes `final_score`.
- Add liveness/readiness endpoints, admin/restore/health CLI operations, multi-user-safe cleanup scripts, and sanitized account export.
- Add a Caddy HTTPS production Compose that keeps FastAPI private and enables Secure cookies.
- Validate six real papers at 6 papers / 188 questions / 667 options with 188/188 knowledge-point coverage and idempotent import.
- Validate real two-user isolation and real Chinese subjective answer AI-suggestion → human-final review flow.

## v0.4

- Fix Windows DOCX temporary-file reopen failure by parsing only after the writer is closed.
- Make `value` the canonical scalar answer field while keeping read compatibility for legacy `answer` data.
- Add admin paper/question CRUD with archive semantics and version increments.
- Add full JSON export, CSV ZIP export, SQLite consistent backup, and CLI backup script.
- Add optional admin-token protection and Next.js server-side admin proxy.
- Add Docker Compose deployment baseline and environment example.
- Render retained DOCX formula/image HTML safely in learner/review pages.
- Add real-paper acceptance flow covering wrong-question mastery and subjective manual review.
