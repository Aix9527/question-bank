from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select

from app.models.import_job import ImportJob
from app.schemas.import_job import ImportJobSummary, ImportPublishResult, ImportReview, ImportReviewUpdate
from app.services.imports.publisher import create_import_job, job_summary, publish_job, review_payload, update_review

router = APIRouter(prefix='/api/admin/imports', tags=['admin-imports'])


@router.get('', response_model=list[ImportJobSummary])
def list_imports(request: Request):
    with request.app.state.session_factory() as session:
        jobs = list(session.scalars(select(ImportJob).order_by(ImportJob.id.desc())).all())
        return [job_summary(job) for job in jobs]


@router.post('/docx', response_model=ImportJobSummary, status_code=status.HTTP_201_CREATED)
async def upload_docx(request: Request, subject_code: str = Form(...), file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.docx'):
        raise HTTPException(status_code=400, detail='only .docx is supported')
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail='empty file')
    with request.app.state.session_factory() as session:
        try:
            job, reused = create_import_job(session, subject_code=subject_code, filename=file.filename, data=data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = job_summary(job, reused=reused)
    if reused:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=200, content=response)
    return response


@router.get('/{import_id}/review', response_model=ImportReview)
def get_review(import_id: int, request: Request):
    with request.app.state.session_factory() as session:
        job = session.get(ImportJob, import_id)
        if job is None:
            raise HTTPException(status_code=404, detail='import not found')
        return review_payload(job)


@router.patch('/{import_id}/review', response_model=ImportReview)
def patch_review(import_id: int, payload: ImportReviewUpdate, request: Request):
    with request.app.state.session_factory() as session:
        job = session.get(ImportJob, import_id)
        if job is None:
            raise HTTPException(status_code=404, detail='import not found')
        job = update_review(
            session,
            job,
            draft=payload.draft,
            resolve_warning_ids=payload.resolve_warning_ids,
            resolution_note=payload.resolution_note,
        )
        return review_payload(job)


@router.post('/{import_id}/publish', response_model=ImportPublishResult)
def publish(import_id: int, request: Request):
    with request.app.state.session_factory() as session:
        job = session.get(ImportJob, import_id)
        if job is None:
            raise HTTPException(status_code=404, detail='import not found')
        try:
            paper = publish_job(session, job)
        except RuntimeError as exc:
            if str(exc) == 'blocking warnings unresolved':
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            raise
        return {'id': job.id, 'status': job.status, 'paper_id': paper.id}
