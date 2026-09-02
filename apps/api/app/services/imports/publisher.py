from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Subject
from app.models.import_job import ImportJob
from app.models.question_bank import Paper, PaperQuestion, PaperSection, Question, QuestionOption
from app.services.imports.docx_parser import parse_docx
from app.services.imports.question_mapper import map_document
from app.services.knowledge_points import infer_knowledge_points


def blocking_warning_count(warnings: list[dict[str, Any]]) -> int:
    return sum(1 for warning in warnings if warning.get('severity') == 'blocking' and not warning.get('resolved'))


def warning_count(warnings: list[dict[str, Any]]) -> int:
    return len(warnings)


def job_summary(job: ImportJob, *, reused: bool = False) -> dict[str, Any]:
    warnings = job.warnings_json or []
    return {
        'id': job.id,
        'subject_code': job.subject_code,
        'source_filename': job.source_filename,
        'source_sha256': job.source_sha256,
        'source_size': job.source_size,
        'title': job.title,
        'status': job.status,
        'blocking_warning_count': blocking_warning_count(warnings),
        'warning_count': warning_count(warnings),
        'published_paper_id': job.published_paper_id,
        'reused': reused,
    }


def _parse_docx_bytes(*, filename: str, data: bytes) -> dict[str, Any]:
    """Parse uploaded DOCX bytes from a closed temporary file.

    ``NamedTemporaryFile`` kept open while parsing works on POSIX but fails on
    Windows because a second reader cannot reopen the locked file. Writing via
    ``Path.write_bytes`` closes the writer before ``parse_docx`` is called, and
    ``TemporaryDirectory`` guarantees cleanup afterwards.
    """
    suffix = Path(filename).suffix or '.docx'
    with TemporaryDirectory(prefix='question-bank-import-') as tmpdir:
        temp_path = Path(tmpdir) / f'source{suffix}'
        temp_path.write_bytes(data)
        return parse_docx(temp_path)


def create_import_job(session: Session, *, subject_code: str, filename: str, data: bytes) -> tuple[ImportJob, bool]:
    if subject_code not in {'chinese', 'math', 'english'}:
        raise ValueError('unsupported subject')
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    existing = session.scalar(select(ImportJob).where(ImportJob.source_sha256 == digest, ImportJob.subject_code == subject_code))
    if existing is not None:
        return existing, True

    ast = _parse_docx_bytes(filename=filename, data=data)
    ast['source_filename'] = filename
    ast['source_sha256'] = digest
    ast['source_size'] = len(data)
    draft = map_document(ast, subject_code)
    warnings = draft.pop('warnings')
    status = 'ready' if blocking_warning_count(warnings) == 0 else 'pending_review'
    job = ImportJob(
        subject_code=subject_code,
        source_filename=filename,
        source_sha256=digest,
        source_size=len(data),
        title=draft.get('title') or Path(filename).stem,
        status=status,
        ast_json=ast,
        draft_json=draft,
        warnings_json=warnings,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job, False


def review_payload(job: ImportJob) -> dict[str, Any]:
    warnings = job.warnings_json or []
    return {
        'id': job.id,
        'subject_code': job.subject_code,
        'source_filename': job.source_filename,
        'source_sha256': job.source_sha256,
        'status': job.status,
        'review_revision': job.review_revision,
        'draft': job.draft_json,
        'warnings': warnings,
        'blocking_warning_count': blocking_warning_count(warnings),
    }


def update_review(session: Session, job: ImportJob, *, draft: dict[str, Any], resolve_warning_ids: list[str], resolution_note: str | None) -> ImportJob:
    warning_ids = set(resolve_warning_ids)
    warnings = []
    for warning in job.warnings_json or []:
        item = dict(warning)
        if item.get('id') in warning_ids:
            item['resolved'] = True
            item['resolution_note'] = resolution_note or '人工审核已确认'
        warnings.append(item)
    job.draft_json = draft
    job.title = str(draft.get('title') or job.title)
    job.warnings_json = warnings
    job.review_revision += 1
    job.status = 'ready' if blocking_warning_count(warnings) == 0 else 'pending_review'
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def publish_job(session: Session, job: ImportJob) -> Paper:
    if job.published_paper_id is not None:
        paper = session.get(Paper, job.published_paper_id)
        if paper is not None:
            return paper
    if blocking_warning_count(job.warnings_json or []):
        raise RuntimeError('blocking warnings unresolved')

    subject = session.scalar(select(Subject).where(Subject.code == job.subject_code))
    if subject is None:
        raise RuntimeError('subject missing')
    draft = job.draft_json
    paper = Paper(
        subject_id=subject.id,
        title=str(draft.get('title') or job.title),
        source_file=job.source_filename,
        paper_type='mock',
        total_score=sum(float(section.get('score_total') or 0) for section in draft.get('sections', [])),
        status='published',
        version=1,
    )
    session.add(paper)
    session.flush()

    for section_data in draft.get('sections', []):
        section = PaperSection(
            paper_id=paper.id,
            title=str(section_data.get('title') or '未命名大题'),
            order_index=int(section_data.get('order_index') or 1),
            instruction=section_data.get('instruction'),
            score_total=float(section_data.get('score_total') or 0),
        )
        session.add(section)
        session.flush()
        for qidx, qdata in enumerate(section_data.get('questions', []), start=1):
            question = Question(
                subject_id=subject.id,
                type=str(qdata.get('type') or 'subjective'),
                stem_html=str(qdata.get('stem_html') or ''),
                material_html=qdata.get('material_html'),
                answer_mode=str(qdata.get('answer_mode') or 'manual'),
                standard_answer_json=qdata.get('standard_answer_json'),
                explanation_html=qdata.get('explanation_html'),
                score=float(qdata.get('score') or 0),
                difficulty=qdata.get('difficulty'),
                knowledge_points=qdata.get('knowledge_points') or infer_knowledge_points(
                    job.subject_code,
                    str(qdata.get('type') or 'subjective'),
                    qdata.get('stem_html'),
                    qdata.get('material_html'),
                    section_data.get('title'),
                ),
                source=f'{job.source_filename}#{qdata.get("candidate_id", qidx)}',
                status='published',
                version=1,
            )
            session.add(question)
            session.flush()
            for oidx, option in enumerate(qdata.get('options', []), start=1):
                session.add(QuestionOption(
                    question_id=question.id,
                    label=str(option.get('label') or chr(64 + oidx)),
                    content_html=str(option.get('content_html') or ''),
                    order_index=int(option.get('order_index') or oidx),
                ))
            session.add(PaperQuestion(
                paper_id=paper.id,
                question_id=question.id,
                section_id=section.id,
                order_index=qidx,
                score_override=float(qdata.get('score') or 0),
            ))

    job.status = 'published'
    job.published_paper_id = paper.id
    job.published_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    session.refresh(paper)
    return paper
