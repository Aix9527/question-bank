# Online Question Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable online question bank for Chinese, Math, and English with practice/exam flows, auto-grading, manual review, wrong-question review, favorites, statistics, DOCX import/review, and deployment-ready storage boundaries.

**Architecture:** A Next.js/React TypeScript web client consumes a FastAPI application organized by domain modules. SQLAlchemy models store versioned question-bank and attempt data in SQLite for local development with PostgreSQL-compatible usage patterns. DOCX ingestion is isolated behind parser/mapper/review stages and never publishes uncertain content automatically.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic-ready models, pytest; Next.js 15+, React, TypeScript, Vitest/Testing Library; SQLite locally, PostgreSQL later.

**Spec:** `docs/superpowers/specs/2026-09-02-online-question-bank-design.md`

## Global Constraints

- Subjects are fixed to `chinese`, `math`, `english` in v1.
- Development database is SQLite; application code must not rely on SQLite-only business behavior.
- Question content is versioned; historical answers must retain the question version used at answer time.
- Every answer change is persisted immediately.
- Attempt submission is idempotent.
- DOCX import is fail-closed: uncertain parsing produces warnings and requires review before publish.
- AI scoring is advisory only and may populate `suggested_score`; `final_score` remains human-overridable.
- v1 excludes payments, class ranking, livestreaming, social features, and complex institutional roles.

---

## File Structure

### Backend

- `backend/app/main.py` — FastAPI composition and router registration.
- `backend/app/config.py` — environment-backed settings.
- `backend/app/db.py` — SQLAlchemy engine/session/base helpers.
- `backend/app/models/*.py` — focused persistence models by domain.
- `backend/app/schemas/*.py` — request/response contracts.
- `backend/app/services/grading.py` — objective/fill-in grading rules.
- `backend/app/services/attempts.py` — attempt lifecycle, autosave, idempotent submit.
- `backend/app/services/wrong_questions.py` — wrong-question state transitions.
- `backend/app/services/statistics.py` — subject/type/knowledge-point summaries.
- `backend/app/services/imports/docx_parser.py` — structural DOCX parser only.
- `backend/app/services/imports/question_mapper.py` — subject-aware AST-to-question candidate mapping.
- `backend/app/api/*.py` — learner/admin HTTP boundaries.
- `backend/tests/unit/*` — isolated rule tests.
- `backend/tests/integration/*` — API/database lifecycle tests.

### Frontend

- `web/app/page.tsx` — dashboard with three subject entries.
- `web/app/subjects/[code]/page.tsx` — subject hub.
- `web/app/papers/[id]/page.tsx` — paper overview.
- `web/app/attempts/[id]/page.tsx` — practice/exam workspace.
- `web/app/wrong-questions/page.tsx` — wrong-question review.
- `web/app/favorites/page.tsx` — favorites.
- `web/app/statistics/page.tsx` — study analytics.
- `web/app/admin/*` — paper/question/import/review/admin pages.
- `web/lib/api.ts` — typed API client.
- `web/components/*` — reusable question, answer-card, subject-card components.
- `web/tests/*` — UI behavior tests.

---

### Task 1: Backend Foundation and Three Subjects

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Create: `backend/app/models/subject.py`
- Create: `backend/app/schemas/subject.py`
- Create: `backend/app/api/subjects.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/integration/test_subjects_api.py`

**Interfaces:**
- Produces: `GET /api/subjects -> list[SubjectOut]`
- Produces: `Subject(code: Literal['chinese','math','english'], name: str, enabled: bool)` persisted in DB.

- [ ] **Step 1: Write the failing subjects API test**

```python
def test_subjects_are_seeded(client):
    response = client.get('/api/subjects')
    assert response.status_code == 200
    assert [item['code'] for item in response.json()] == ['chinese', 'math', 'english']
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/integration/test_subjects_api.py -v
```

Expected: FAIL because the app and endpoint do not exist.

- [ ] **Step 3: Implement settings, database session, Subject model, startup seed, and route**

```python
SUBJECTS = (
    ('chinese', '语文'),
    ('math', '数学'),
    ('english', '英语'),
)
```

On startup, insert missing subjects only; never duplicate existing rows.

- [ ] **Step 4: Run the test suite**

```bash
cd backend && pytest -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: bootstrap question bank backend"
```

---

### Task 2: Papers, Sections, Questions, Options, and Versioned Paper Links

**Files:**
- Create: `backend/app/models/paper.py`
- Create: `backend/app/models/question.py`
- Create: `backend/app/schemas/paper.py`
- Create: `backend/app/schemas/question.py`
- Create: `backend/app/api/papers.py`
- Create: `backend/tests/integration/test_papers_api.py`

**Interfaces:**
- Produces: `GET /api/subjects/{subject_code}/papers`
- Produces: `GET /api/papers/{paper_id}` returning ordered sections and question summaries.
- Produces: `Question.version: int` and `PaperQuestion.question_version: int` to freeze history references.

- [ ] **Step 1: Write failing tests for subject paper listing and ordered paper detail**

```python
def test_paper_questions_preserve_section_and_order(client, seeded_paper):
    response = client.get(f'/api/papers/{seeded_paper.id}')
    body = response.json()
    assert body['sections'][0]['questions'][0]['order_index'] == 1
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/integration/test_papers_api.py -v
```

- [ ] **Step 3: Implement models and read APIs**

Use separate `PaperSection` and `PaperQuestion` tables. `PaperQuestion` stores `score_override` and the question version used by that paper version.

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest -q
```

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add papers and versioned questions"
```

---

### Task 3: Objective Grading Engine

**Files:**
- Create: `backend/app/services/grading.py`
- Create: `backend/tests/unit/test_grading.py`

**Interfaces:**
- Produces: `grade_answer(question_type: str, answer_mode: str, standard: dict, submitted: object, max_score: float) -> GradeResult`
- `GradeResult` contains `is_correct: bool | None`, `score: float | None`, and `needs_manual_review: bool`.

- [ ] **Step 1: Write failing grading tests**

```python
def test_single_choice_exact_match():
    result = grade_answer('single_choice', 'exact', {'answer': 'B'}, 'B', 5)
    assert result.is_correct is True
    assert result.score == 5


def test_numeric_tolerance():
    result = grade_answer('fill_blank', 'numeric_tolerance', {'value': 3.14, 'tolerance': 0.01}, '3.145', 4)
    assert result.is_correct is True


def test_subjective_requires_manual_review():
    result = grade_answer('essay', 'manual', {}, '作文内容', 60)
    assert result.needs_manual_review is True
    assert result.score is None
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/unit/test_grading.py -v
```

- [ ] **Step 3: Implement single choice, multiple choice `exact_only`/`partial`, normalized text, numeric exact/tolerance, multiple acceptable, and manual modes**

Text normalization must trim surrounding whitespace, collapse internal whitespace, and use Unicode normalization before comparison.

- [ ] **Step 4: Run unit tests**

```bash
cd backend && pytest tests/unit/test_grading.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/grading.py backend/tests/unit/test_grading.py
git commit -m "feat: add objective grading engine"
```

---

### Task 4: Attempt Lifecycle, Autosave, and Idempotent Submission

**Files:**
- Create: `backend/app/models/attempt.py`
- Create: `backend/app/schemas/attempt.py`
- Create: `backend/app/services/attempts.py`
- Create: `backend/app/api/attempts.py`
- Create: `backend/tests/integration/test_attempt_flow.py`

**Interfaces:**
- Produces: `POST /api/attempts`
- Produces: `PATCH /api/attempts/{attempt_id}/answers/{question_id}`
- Produces: `GET /api/attempts/{attempt_id}`
- Produces: `POST /api/attempts/{attempt_id}/submit`

- [ ] **Step 1: Write failing lifecycle test**

```python
def test_autosave_survives_reload_and_submit_is_idempotent(client, seeded_paper):
    attempt = client.post('/api/attempts', json={'paper_id': seeded_paper.id, 'mode': 'exam'}).json()
    client.patch(f"/api/attempts/{attempt['id']}/answers/1", json={'answer': 'B'})
    restored = client.get(f"/api/attempts/{attempt['id']}").json()
    assert restored['answers']['1']['answer'] == 'B'
    first = client.post(f"/api/attempts/{attempt['id']}/submit").json()
    second = client.post(f"/api/attempts/{attempt['id']}/submit").json()
    assert first['submitted_at'] == second['submitted_at']
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/integration/test_attempt_flow.py -v
```

- [ ] **Step 3: Implement create/autosave/restore/submit**

Submission must grade all objective responses exactly once and leave subjective records as `pending_manual`.

- [ ] **Step 4: Run integration tests**

```bash
cd backend && pytest tests/integration/test_attempt_flow.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add repeatable attempt lifecycle"
```

---

### Task 5: Wrong Questions, Favorites, and Learning Statistics

**Files:**
- Create: `backend/app/models/learning.py`
- Create: `backend/app/services/wrong_questions.py`
- Create: `backend/app/services/statistics.py`
- Create: `backend/app/api/learning.py`
- Create: `backend/tests/unit/test_wrong_question_state.py`
- Create: `backend/tests/integration/test_learning_api.py`

**Interfaces:**
- Produces: `GET /api/me/wrong-questions`
- Produces: `POST /api/questions/{question_id}/favorite`
- Produces: `DELETE /api/questions/{question_id}/favorite`
- Produces: `GET /api/me/statistics`

- [ ] **Step 1: Write failing state transition test**

```python
def test_repeated_correct_reviews_can_master_wrong_question():
    state = WrongQuestionState(wrong_count=2, correct_review_count=0, mastery_status='learning')
    state = apply_review_result(state, correct=True)
    state = apply_review_result(state, correct=True)
    assert state.mastery_status == 'mastered'
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/unit/test_wrong_question_state.py -v
```

- [ ] **Step 3: Implement wrong-question accumulation, reason tagging, two-success mastery threshold, favorites, and aggregate statistics**

Statistics include totals and correctness by subject, question type, and knowledge point plus 7/30-day activity.

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest -q
```

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add wrong questions favorites and stats"
```

---

### Task 6: Manual Review Center

**Files:**
- Create: `backend/app/models/review.py`
- Create: `backend/app/schemas/review.py`
- Create: `backend/app/services/reviews.py`
- Create: `backend/app/api/admin_reviews.py`
- Create: `backend/tests/integration/test_manual_review.py`

**Interfaces:**
- Produces: `GET /api/admin/reviews/pending`
- Produces: `POST /api/admin/reviews/{answer_record_id}`
- Review request fields: `suggested_score?`, `final_score`, `comment`, `rubric_json?`.

- [ ] **Step 1: Write failing pending-review/final-score test**

```python
def test_manual_review_updates_attempt_total(client, subjective_attempt):
    pending = client.get('/api/admin/reviews/pending').json()
    answer_id = pending[0]['answer_record_id']
    client.post(f'/api/admin/reviews/{answer_id}', json={'final_score': 42, 'comment': '结构完整'})
    result = client.get(f"/api/attempts/{subjective_attempt.id}").json()
    assert result['status'] == 'graded'
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/integration/test_manual_review.py -v
```

- [ ] **Step 3: Implement manual review and final score recomputation**

AI suggestions, when present, are stored separately and never replace `final_score` without reviewer submission.

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest -q
```

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: add subjective review center"
```

---

### Task 7: DOCX Parser, Mapper, Import Review, and Publish

**Files:**
- Create: `backend/app/models/import_job.py`
- Create: `backend/app/services/imports/__init__.py`
- Create: `backend/app/services/imports/docx_parser.py`
- Create: `backend/app/services/imports/question_mapper.py`
- Create: `backend/app/services/imports/publisher.py`
- Create: `backend/app/api/admin_imports.py`
- Create: `backend/tests/unit/test_docx_parser.py`
- Create: `backend/tests/unit/test_question_mapper.py`
- Create: `backend/tests/integration/test_import_publish.py`

**Interfaces:**
- Produces: `parse_docx(path: Path) -> DocumentAst`
- Produces: `map_document(ast: DocumentAst, subject_code: str) -> ImportDraft`
- Produces: `POST /api/admin/imports/docx`
- Produces: `GET /api/admin/imports/{import_id}/review`
- Produces: `POST /api/admin/imports/{import_id}/publish`

- [ ] **Step 1: Write failing parser test using a generated DOCX fixture**

```python
def test_parser_preserves_paragraph_order_and_tables(tmp_path):
    path = build_docx_fixture(tmp_path)
    ast = parse_docx(path)
    assert ast.blocks[0].kind == 'paragraph'
    assert any(block.kind == 'table' for block in ast.blocks)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/unit/test_docx_parser.py tests/unit/test_question_mapper.py -v
```

- [ ] **Step 3: Implement parser as structural extraction only**

Parser records paragraphs, tables, embedded images, numbering/style metadata, and raw XML references for unsupported equations/objects. It must not decide correct answers or question types.

- [ ] **Step 4: Implement mapper with warnings instead of guesses**

Recognize section headings, numbered questions, A/B/C/D options, answer regions, score hints, and materials. Any ambiguous split or answer mapping adds a warning and sets candidate status to `pending_review`.

- [ ] **Step 5: Implement SHA-256 duplicate detection, review DTO, and publish gate**

Publish must reject any draft containing unresolved blocking warnings.

- [ ] **Step 6: Run import tests**

```bash
cd backend && pytest tests/unit/test_docx_parser.py tests/unit/test_question_mapper.py tests/integration/test_import_publish.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: add fail closed docx import pipeline"
```

---

### Task 8: Frontend Foundation and Subject Dashboard

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/app/layout.tsx`
- Create: `web/app/globals.css`
- Create: `web/app/page.tsx`
- Create: `web/lib/api.ts`
- Create: `web/components/SubjectCard.tsx`
- Create: `web/tests/home.test.tsx`

**Interfaces:**
- Consumes: `GET /api/subjects`, `GET /api/me/statistics`
- Produces: homepage cards for 语文/数学/英语 and links into `/subjects/{code}`.

- [ ] **Step 1: Write failing homepage test**

```tsx
it('renders three subject entrances', async () => {
  render(<HomePage />)
  expect(await screen.findByText('语文')).toBeInTheDocument()
  expect(screen.getByText('数学')).toBeInTheDocument()
  expect(screen.getByText('英语')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd web && npm test -- --run
```

- [ ] **Step 3: Implement responsive dashboard and typed API client**

Cards show subject name, recent score, wrong-question count, and a primary “开始学习” action when data is available; empty state remains usable before history exists.

- [ ] **Step 4: Run tests and production build**

```bash
cd web && npm test -- --run && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: add three subject learner dashboard"
```

---

### Task 9: Subject Hub, Paper Center, and Attempt Workspace

**Files:**
- Create: `web/app/subjects/[code]/page.tsx`
- Create: `web/app/papers/[id]/page.tsx`
- Create: `web/app/attempts/[id]/page.tsx`
- Create: `web/components/QuestionRenderer.tsx`
- Create: `web/components/AnswerCard.tsx`
- Create: `web/components/ExamTimer.tsx`
- Create: `web/tests/attempt.test.tsx`

**Interfaces:**
- Consumes: paper and attempt APIs from Tasks 2 and 4.
- Produces: practice immediate-feedback mode and exam hidden-feedback mode.

- [ ] **Step 1: Write failing autosave UI test**

```tsx
it('autosaves when an answer changes', async () => {
  render(<AttemptPage params={{ id: '1' }} />)
  await user.click(await screen.findByLabelText('B'))
  expect(mockPatchAnswer).toHaveBeenCalledWith('1', expect.anything(), 'B')
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd web && npm test -- --run web/tests/attempt.test.tsx
```

- [ ] **Step 3: Implement question renderer, answer card, exam timer, local optimistic state, and immediate PATCH autosave**

Exam mode never reveals answers before submission; practice mode shows grading feedback after each answer is saved and graded.

- [ ] **Step 4: Run tests/build**

```bash
cd web && npm test -- --run && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: add practice and exam workspace"
```

---

### Task 10: Wrong Questions, Favorites, Statistics, and Manual Review UI

**Files:**
- Create: `web/app/wrong-questions/page.tsx`
- Create: `web/app/favorites/page.tsx`
- Create: `web/app/statistics/page.tsx`
- Create: `web/app/admin/reviews/page.tsx`
- Create: `web/tests/learning-pages.test.tsx`

**Interfaces:**
- Consumes: learning and review APIs from Tasks 5 and 6.

- [ ] **Step 1: Write failing wrong-question and review-page tests**

```tsx
it('shows pending and mastered wrong question groups', async () => {
  render(<WrongQuestionsPage />)
  expect(await screen.findByText('待复习')).toBeInTheDocument()
  expect(screen.getByText('已掌握')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd web && npm test -- --run web/tests/learning-pages.test.tsx
```

- [ ] **Step 3: Implement pages with clear empty states and reviewer score/comment form**

- [ ] **Step 4: Run tests/build**

```bash
cd web && npm test -- --run && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: add learning review and statistics pages"
```

---

### Task 11: Admin Paper/Question CRUD and DOCX Review UI

**Files:**
- Create: `backend/app/api/admin_content.py`
- Create: `backend/tests/integration/test_admin_content.py`
- Create: `web/app/admin/page.tsx`
- Create: `web/app/admin/papers/page.tsx`
- Create: `web/app/admin/questions/page.tsx`
- Create: `web/app/admin/imports/page.tsx`
- Create: `web/app/admin/imports/[id]/page.tsx`
- Create: `web/tests/admin-import.test.tsx`

**Interfaces:**
- Produces/consumes admin CRUD and import-review endpoints.

- [ ] **Step 1: Write failing publish-gate API/UI tests**

```python
def test_publish_rejects_unresolved_blocking_warning(client, draft_import):
    response = client.post(f'/api/admin/imports/{draft_import.id}/publish')
    assert response.status_code == 409
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/integration/test_admin_content.py -v
```

- [ ] **Step 3: Implement minimal CRUD, archive instead of destructive delete for published content, and side-by-side import review editing**

- [ ] **Step 4: Run backend/frontend suites**

```bash
cd backend && pytest -q
cd ../web && npm test -- --run && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add backend web
git commit -m "feat: add question bank administration"
```

---

### Task 12: Import the Six Source Papers and Verify Data

**Files:**
- Create: `scripts/import_initial_papers.py`
- Create: `backend/tests/integration/test_initial_papers.py`
- Create: `data/import-manifest.json`

**Interfaces:**
- Consumes: import pipeline from Task 7.
- Produces: six import jobs mapped to the subject/paper titles in the specification, each with SHA-256, source filename, warning counts, and publication status.

- [ ] **Step 1: Make the source archive accessible and extract only the six DOCX files**

Use an available RAR-capable extractor. Do not modify the originals.

- [ ] **Step 2: Write failing manifest test**

```python
def test_initial_manifest_has_two_papers_per_subject(initial_manifest):
    assert initial_manifest['counts'] == {'chinese': 2, 'math': 2, 'english': 2}
```

- [ ] **Step 3: Run import in review mode**

```bash
python scripts/import_initial_papers.py --source ../专科复习资料.rar --mode review
```

Expected: six import jobs; unresolved items remain unpublished.

- [ ] **Step 4: Verify every candidate has source traceability and no blocking warning is auto-published**

```bash
cd backend && pytest tests/integration/test_initial_papers.py -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts data backend/tests/integration/test_initial_papers.py
git commit -m "data: stage six initial exam papers"
```

---

### Task 13: Backup, Export, Security Baseline, and Deployment

**Files:**
- Create: `backend/app/services/export.py`
- Create: `backend/app/api/admin_backup.py`
- Create: `scripts/backup_db.py`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `Dockerfile.api`
- Create: `Dockerfile.web`
- Create: `README.md`
- Create: `backend/tests/integration/test_export.py`

**Interfaces:**
- Produces JSON/CSV learning exports.
- Produces repeatable DB backup command.
- Documents environment variables and local/public deployment.

- [ ] **Step 1: Write failing export test**

```python
def test_json_export_contains_attempts_and_wrong_questions(client):
    response = client.get('/api/admin/export?format=json')
    assert response.status_code == 200
    assert 'attempts' in response.json()
    assert 'wrong_questions' in response.json()
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend && pytest tests/integration/test_export.py -v
```

- [ ] **Step 3: Implement export/backup and deployment files**

Set CORS through explicit environment configuration, keep admin routes behind a simple v1 admin token dependency, and document replacing that mechanism with real identity before wider multi-user exposure.

- [ ] **Step 4: Run full verification**

```bash
cd backend && pytest -q
cd ../web && npm test -- --run && npm run build
cd .. && docker compose config
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: add backup export and deployment baseline"
```

---

## Final Verification

- [ ] `GET /api/subjects` returns exactly Chinese/Math/English.
- [ ] All six imported files exist as reviewable import jobs and are assigned two per subject.
- [ ] Practice answers autosave and can show immediate objective feedback.
- [ ] Exam answers autosave, survive reload, and hide solutions until submit.
- [ ] Repeated submit is idempotent.
- [ ] Subjective answers remain pending until reviewed.
- [ ] Wrong questions accumulate and can become mastered after two correct reviews.
- [ ] Favorites can be added/removed.
- [ ] Statistics include subject/type/knowledge-point views and 7/30-day counts.
- [ ] DOCX publish refuses unresolved blocking warnings.
- [ ] Backend tests pass.
- [ ] Frontend tests pass and production build succeeds.
- [ ] Docker Compose configuration validates.
