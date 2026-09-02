from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    engine_kwargs = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        # Local SQLite keeps an in-thread connection for dev/tests.
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Vercel/serverless + Supabase Transaction Pooler (:6543) must not
        # hold pooled connections between requests.
        engine_kwargs["poolclass"] = NullPool
    return create_engine(settings.database_url, **engine_kwargs)


def build_session_factory(engine):
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
