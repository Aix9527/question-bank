from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request

from app.services.auth_service import authenticate_token, ensure_local_user


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        return None
    return token.strip()


def current_raw_token(authorization: str | None = Header(default=None)) -> str | None:
    return _bearer_token(authorization)


def get_current_user(request: Request, authorization: str | None = Header(default=None)):
    settings = request.app.state.settings
    with request.app.state.session_factory() as session:
        if not settings.auth_required:
            return ensure_local_user(session)
        raw_token = _bearer_token(authorization)
        if not raw_token:
            raise HTTPException(status_code=401, detail='authentication required')
        user = authenticate_token(session, raw_token)
        if user is None:
            raise HTTPException(status_code=401, detail='invalid or expired session')
        session.expunge(user)
        return user


def require_admin(
    request: Request,
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
):
    settings = request.app.state.settings
    if settings.auth_required:
        user = get_current_user(request, authorization)
        if user.role != 'admin':
            raise HTTPException(status_code=403, detail='admin role required')
        return user

    expected = settings.admin_token
    if expected:
        if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
            raise HTTPException(status_code=401, detail='invalid admin token')
    with request.app.state.session_factory() as session:
        return ensure_local_user(session)
