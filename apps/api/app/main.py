from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, build_engine, build_session_factory
from app.models import ai_review, attempt, core, import_job, learning, question_bank, review, user  # noqa: F401
from app.routes.admin_backup import router as admin_backup_router
from app.routes.admin_content import router as admin_content_router
from app.routes.admin_imports import router as admin_imports_router
from app.routes.admin_users import router as admin_users_router
from app.routes.ai_reviews import router as ai_reviews_router
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.attempts import router as attempts_router
from app.routes.learning import router as learning_router
from app.routes.papers import router as papers_router
from app.routes.reviews import router as reviews_router
from app.routes.statistics import router as statistics_router
from app.routes.subjects import router as subjects_router
from app.security import require_admin
from app.services.ai_grading import build_ai_grader
from app.services.bootstrap import seed_subjects, seed_users


_RUNTIME_BOOTSTRAP_ENVS = frozenset(
    {
        "development",
        "dev",
        "test",
        "testing",
        "local",
    }
)


def _normalize_app_env(value: str | None) -> str:
    return (value or "development").strip().lower()


def _runtime_bootstrap_enabled(*, app_env: str, dialect_name: str) -> bool:
    """Runtime schema/bootstrap is intentionally limited to local SQLite.

    PostgreSQL databases are always Alembic-managed.
    """
    return (
        _normalize_app_env(app_env) in _RUNTIME_BOOTSTRAP_ENVS
        and dialect_name == "sqlite"
    )


def _validate_runtime_database(*, app_env: str, dialect_name: str) -> None:
    """Prevent accidental production deployment from silently falling back
    to a local/ephemeral SQLite database."""
    env = _normalize_app_env(app_env)
    if dialect_name == "sqlite" and env not in _RUNTIME_BOOTSTRAP_ENVS:
        raise RuntimeError(
            "SQLite is only allowed for local/dev/test runtime. "
            "Production/staging must use PostgreSQL."
        )


def create_app() -> FastAPI:
    settings = get_settings()
    engine = build_engine()
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_env = _normalize_app_env(settings.app_env)
        dialect_name = engine.dialect.name

        _validate_runtime_database(
            app_env=app_env,
            dialect_name=dialect_name,
        )

        if _runtime_bootstrap_enabled(
            app_env=app_env,
            dialect_name=dialect_name,
        ):
            # Local/dev/test SQLite only. PostgreSQL schema is NEVER
            # created here; it is managed exclusively by Alembic.
            Base.metadata.create_all(bind=engine)
            with session_factory() as session:
                seed_subjects(session)
                seed_users(
                    session,
                    admin_username=settings.bootstrap_admin_username,
                    admin_password=settings.bootstrap_admin_password,
                )

        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="专科复习在线题库", version="0.5.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_grader = build_ai_grader(settings)
    app.include_router(health_router)
    app.include_router(subjects_router)
    app.include_router(auth_router)
    admin_dependencies = [Depends(require_admin)]
    app.include_router(admin_backup_router, dependencies=admin_dependencies)
    app.include_router(admin_content_router, dependencies=admin_dependencies)
    app.include_router(admin_imports_router, dependencies=admin_dependencies)
    app.include_router(admin_users_router, dependencies=admin_dependencies)
    app.include_router(ai_reviews_router, dependencies=admin_dependencies)
    app.include_router(papers_router)
    app.include_router(attempts_router)
    app.include_router(learning_router)
    app.include_router(reviews_router)
    app.include_router(statistics_router)
    return app


app = create_app()
