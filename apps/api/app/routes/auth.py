from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserRead,
)
from app.security import current_raw_token, get_current_user
from app.services.auth_service import (
    authenticate_credentials,
    change_password,
    create_user,
    issue_session,
    revoke_token,
)

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


@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=LoginResponse)
def register(payload: RegisterRequest, request: Request):
    """公开自助注册：只创建学习账号（learner），注册成功后直接返回会话。"""
    with request.app.state.session_factory() as session:
        try:
            user = create_user(
                session,
                username=payload.username,
                password=payload.password,
                display_name=payload.display_name,
                role='learner',
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if user is None:
            raise HTTPException(status_code=409, detail='username already exists')
        auth = issue_session(session, user=user, session_hours=request.app.state.settings.auth_session_hours)
        return LoginResponse(token=auth.raw_token, expires_at=auth.expires_at, user=_user_read(user))


@router.post('/change-password', status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    payload: ChangePasswordRequest,
    request: Request,
    user=Depends(get_current_user),
    raw_token: str | None = Depends(current_raw_token),
):
    """修改本人密码：校验旧密码后更新，并使其它已登录会话失效。"""
    with request.app.state.session_factory() as session:
        try:
            change_password(
                session,
                user_id=user.id,
                old_password=payload.old_password,
                new_password=payload.new_password,
                keep_raw_token=raw_token,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/me', response_model=UserRead)
def me(user=Depends(get_current_user)):
    return _user_read(user)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, raw_token: str | None = Depends(current_raw_token)):
    if raw_token:
        with request.app.state.session_factory() as session:
            revoke_token(session, raw_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
