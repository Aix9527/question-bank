from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserSession

PBKDF2_ITERATIONS = 310_000


@dataclass(frozen=True)
class SessionAuth:
    user: User
    raw_token: str
    expires_at: datetime


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return 'pbkdf2_sha256${}${}${}'.format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode('ascii'),
        base64.urlsafe_b64encode(digest).decode('ascii'),
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode('ascii'))
        expected = base64.urlsafe_b64decode(digest_text.encode('ascii'))
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)


def ensure_local_user(session: Session) -> User:
    user = session.get(User, 1)
    if user is None:
        user = User(id=1, username='local', display_name='本地学习者', role='learner', password_hash=None, enabled=True)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def ensure_bootstrap_admin(session: Session, *, username: str | None, password: str | None) -> User | None:
    if not username or not password:
        return None
    existing = session.scalar(select(User).where(User.username == username))
    if existing is not None:
        changed = False
        if existing.role != 'admin':
            existing.role = 'admin'; changed = True
        if not existing.password_hash:
            existing.password_hash = hash_password(password); changed = True
        if not existing.enabled:
            existing.enabled = True; changed = True
        if changed:
            session.commit()
        return existing

    # Upgrade path: v0.4 stored every learner-owned row under user_id=1 without
    # a users table. v0.5 first seeds that placeholder as ``local``. When auth
    # is enabled for the first time, promote the placeholder in-place so all
    # legacy attempts/favorites/wrong questions remain attached to the first
    # administrator instead of becoming orphaned history.
    local = session.get(User, 1)
    if local is not None and local.username == 'local' and local.password_hash is None:
        local.username = username
        local.display_name = '管理员'
        local.role = 'admin'
        local.password_hash = hash_password(password)
        local.enabled = True
        session.commit()
        session.refresh(local)
        return local

    user = User(username=username, display_name='管理员', role='admin', password_hash=hash_password(password), enabled=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_user(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    role: str = 'learner',
) -> User | None:
    if session.scalar(select(User.id).where(User.username == username)) is not None:
        return None
    if role == 'admin' and not password:
        raise ValueError('admin account requires a non-empty password')
    user = User(
        username=username,
        display_name=display_name,
        role=role,
        password_hash=hash_password(password),
        enabled=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user(
    session: Session,
    user_id: int,
    *,
    display_name: str | None = None,
    role: str | None = None,
    enabled: bool | None = None,
    password: str | None = None,
    display_name_was_set: bool = False,
) -> User | None:
    user = session.get(User, user_id)
    if user is None:
        return None
    target_role = role if role is not None else user.role
    if target_role == 'admin' and password is not None and password == '':
        raise ValueError('admin account requires a non-empty password')
    if display_name_was_set:
        user.display_name = display_name
    if role is not None:
        user.role = role
    if enabled is not None:
        user.enabled = enabled
    if password is not None:
        user.password_hash = hash_password(password)
    session.commit()
    session.refresh(user)
    return user


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.id)).all())


def authenticate_credentials(session: Session, *, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username))
    if user is None or not user.enabled or not verify_password(password, user.password_hash):
        return None
    return user


def issue_session(session: Session, *, user: User, session_hours: int) -> SessionAuth:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=session_hours)
    row = UserSession(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode('utf-8')).hexdigest(),
        created_at=now,
        expires_at=expires_at,
    )
    session.add(row)
    session.commit()
    return SessionAuth(user=user, raw_token=raw_token, expires_at=expires_at)


def authenticate_token(session: Session, raw_token: str) -> User | None:
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    row = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if row is None or row.revoked_at is not None or _as_utc(row.expires_at) <= datetime.now(timezone.utc):
        return None
    user = session.get(User, row.user_id)
    if user is None or not user.enabled:
        return None
    return user


def change_password(
    session: Session,
    *,
    user_id: int,
    old_password: str,
    new_password: str,
    keep_raw_token: str | None,
) -> None:
    """修改本人密码。旧密码不正确或新密码为空时抛出 ValueError；
    成功后撤销除当前会话外的所有会话。"""
    user = session.get(User, user_id)
    if user is None:
        raise ValueError('user not found')
    if not new_password:
        raise ValueError('new password must not be empty')
    if not verify_password(old_password, user.password_hash):
        raise ValueError('current password is incorrect')
    user.password_hash = hash_password(new_password)
    current_hash = hashlib.sha256((keep_raw_token or '').encode('utf-8')).hexdigest()
    rows = list(
        session.scalars(
            select(UserSession).where(UserSession.user_id == user.id)
        ).all()
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        if row.token_hash == current_hash:
            continue  # 保留当前会话
        if row.revoked_at is None:
            row.revoked_at = now
    session.commit()


def revoke_token(session: Session, raw_token: str) -> bool:
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    row = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if row is None:
        return False
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        session.commit()
    return True
