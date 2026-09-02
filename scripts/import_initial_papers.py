from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def _find_candidate(draft: dict, candidate_id: str) -> dict:
    for section in draft.get("sections", []):
        for question in section.get("questions", []):
            if question.get("candidate_id") == candidate_id:
                return question
    raise RuntimeError(f"candidate not found: {candidate_id}")


def _standard_scalar(question: dict) -> str | None:
    answer = dict(question.get("standard_answer_json") or {})
    if "value" in answer:
        return answer.get("value")
    return answer.get("answer")


def _apply_correction(question: dict, field: str, value: str) -> None:
    if field not in {"standard_answer_json.value", "standard_answer_json.answer"}:
        raise RuntimeError(f"unsupported correction field: {field}")
    answer = dict(question.get("standard_answer_json") or {})
    answer.pop("answer", None)
    answer["value"] = value
    question["standard_answer_json"] = answer


def run(mode: str, source_dir: Path, database: str | None = None) -> list[dict]:
    if database:
        os.environ["QUESTION_BANK_DATABASE_URL"] = database

    # Imports must happen after QUESTION_BANK_DATABASE_URL is set.
    from app.db import Base, build_engine, build_session_factory
    from app.config import get_settings
    from app.models import ai_review, attempt, core, import_job, learning, question_bank, review, user  # noqa: F401
    from app.services.bootstrap import seed_subjects, seed_users
    from app.services.imports.publisher import create_import_job, publish_job, update_review

    manifest = json.loads((ROOT / "data" / "import-manifest.json").read_text(encoding="utf-8"))
    decisions_doc = json.loads((ROOT / "data" / "initial-review-decisions.json").read_text(encoding="utf-8"))
    decisions = {item["source_filename"]: item for item in decisions_doc.get("papers", [])}

    engine = build_engine()
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    results: list[dict] = []
    try:
        with factory() as session:
            seed_subjects(session)
            settings = get_settings()
            seed_users(
                session,
                admin_username=settings.bootstrap_admin_username,
                admin_password=settings.bootstrap_admin_password,
            )
            for item in manifest["papers"]:
                path = source_dir / item["source_filename"]
                data = path.read_bytes()
                job, reused = create_import_job(
                    session,
                    subject_code=item["subject_code"],
                    filename=item["source_filename"],
                    data=data,
                )
                if job.published_paper_id is None:
                    draft = copy.deepcopy(job.draft_json)
                    draft["title"] = item["title"]
                    resolve_ids: list[str] = []
                    notes: list[str] = []
                    if mode == "publish-reviewed":
                        for correction in decisions.get(item["source_filename"], {}).get("corrections", []):
                            question = _find_candidate(draft, correction["candidate_id"])
                            current = _standard_scalar(question)
                            if current != correction["original"]:
                                raise RuntimeError(
                                    f"review source changed for {item['source_filename']} {correction['candidate_id']}: "
                                    f"expected {correction['original']}, got {current}"
                                )
                            _apply_correction(question, correction["field"], correction["corrected"])
                            matching = [
                                w for w in (job.warnings_json or [])
                                if w.get("candidate_id") == correction["candidate_id"]
                                and w.get("code") == correction["warning_code"]
                            ]
                            if len(matching) != 1:
                                raise RuntimeError(f"review warning mismatch: {correction['candidate_id']}")
                            resolve_ids.append(matching[0]["id"])
                            notes.append(correction["reason"])
                    needs_update = draft != job.draft_json or resolve_ids
                    if needs_update:
                        job = update_review(
                            session, job, draft=draft, resolve_warning_ids=resolve_ids,
                            resolution_note="；".join(notes) if notes else "设置正式试卷标题",
                        )
                    if mode == "publish-reviewed":
                        paper = publish_job(session, job)
                        published_paper_id = paper.id
                    else:
                        published_paper_id = job.published_paper_id
                else:
                    published_paper_id = job.published_paper_id

                results.append({
                    "source_filename": item["source_filename"],
                    "subject_code": item["subject_code"],
                    "title": item["title"],
                    "job_id": job.id,
                    "status": job.status,
                    "published_paper_id": published_paper_id,
                    "reused": reused,
                    "blocking_warning_count": sum(
                        1 for w in (job.warnings_json or [])
                        if w.get("severity") == "blocking" and not w.get("resolved")
                    ),
                })
    finally:
        engine.dispose()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="导入首批 6 套真实专科复习模拟卷")
    parser.add_argument("--mode", choices=["review", "publish-reviewed"], default="publish-reviewed")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data" / "source_papers")
    parser.add_argument("--database", help="例如 sqlite:///D:/question-bank/question_bank.db")
    args = parser.parse_args()
    rows = run(args.mode, args.source_dir, args.database)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
