from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.auth import LoginRequest, LoginResponse, UserRead
from app.security import current_raw_token, get_current_user
from app.services.auth_service import authenticate_credentials, issue_session, revoke_token

router = APIRouter(prefix='/api/auth', tags=['auth'])


def _user_read(user) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        enabled=user.enabled,
        created_at=user.created_at,
    )


@router.post('/login', response_model=LoginResponse)
def login(payload: LoginRequest, request: Request):
    with request.app.state.session_factory() as session:
        user = authenticate_credentials(session, username=payload.username, password=payload.password)
        if user is None:
            raise HTTPException(status_code=401, detail='invalid username or password')
        auth = issue_session(session, user=user, session_hours=request.app.state.settings.auth_session_hours)
        return LoginResponse(token=auth.raw_token, expires_at=auth.expires_at, user=_user_read(user))


@router.get('/me', response_model=UserRead)
def me(user=Depends(get_current_user)):
    return _user_read(user)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, raw_token: str | None = Depends(current_raw_token)):
    if raw_token:
        with request.app.state.session_factory() as session:
            revoke_token(session, raw_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
