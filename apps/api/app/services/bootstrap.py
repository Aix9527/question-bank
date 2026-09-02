from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Subject
from app.services.auth_service import ensure_bootstrap_admin, ensure_local_user


SUBJECTS = (
    ("chinese", "语文"),
    ("math", "数学"),
    ("english", "英语"),
)


def seed_subjects(session: Session) -> None:
    existing = set(session.scalars(select(Subject.code)).all())
    for code, name in SUBJECTS:
        if code not in existing:
            session.add(Subject(code=code, name=name, enabled=True))
    session.commit()


def seed_users(session: Session, *, admin_username: str | None, admin_password: str | None) -> None:
    ensure_local_user(session)
    ensure_bootstrap_admin(session, username=admin_username, password=admin_password)
