from fastapi import APIRouter, Request
from sqlalchemy import select

from app.models.core import Subject
from app.schemas.subject import SubjectRead

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectRead])
def list_subjects(request: Request):
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        items = session.scalars(
            select(Subject).where(Subject.enabled.is_(True)).order_by(Subject.id)
        ).all()
        return items
