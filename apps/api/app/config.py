from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    admin_token: str | None
    cors_origins: tuple[str, ...]
    auth_required: bool
    auth_session_hours: int
    bootstrap_admin_username: str | None
    bootstrap_admin_password: str | None
    ai_provider: str
    openai_api_key: str | None
    ai_model: str
    openai_base_url: str


def _cors_origins() -> tuple[str, ...]:
    raw = os.getenv('QUESTION_BANK_CORS_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000')
    return tuple(item.strip() for item in raw.split(',') if item.strip())


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv('QUESTION_BANK_DATABASE_URL', 'sqlite:///./question_bank.db'),
        admin_token=os.getenv('QUESTION_BANK_ADMIN_TOKEN') or None,
        cors_origins=_cors_origins(),
        auth_required=os.getenv('QUESTION_BANK_AUTH_REQUIRED', 'false').strip().lower() in {'1','true','yes','on'},
        auth_session_hours=int(os.getenv('QUESTION_BANK_AUTH_SESSION_HOURS', '168')),
        bootstrap_admin_username=os.getenv('QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME') or None,
        bootstrap_admin_password=os.getenv('QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD') or None,
        ai_provider=os.getenv('QUESTION_BANK_AI_PROVIDER', 'disabled').strip().lower(),
        openai_api_key=os.getenv('OPENAI_API_KEY') or None,
        ai_model=os.getenv('QUESTION_BANK_AI_MODEL', 'gpt-5.6-luna'),
        openai_base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
    )
