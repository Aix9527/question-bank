from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.auth import AdminUserCreate, AdminUserUpdate, UserRead
from app.services.auth_service import create_user, list_users, update_user

router = APIRouter(prefix='/api/admin/users', tags=['admin-users'])


def _read(user) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        enabled=user.enabled,
        created_at=user.created_at,
    )


@router.get('', response_model=list[UserRead])
def users(request: Request):
    with request.app.state.session_factory() as session:
        return [_read(user) for user in list_users(session)]


@router.post('', status_code=status.HTTP_201_CREATED, response_model=UserRead)
def add_user(payload: AdminUserCreate, request: Request):
    with request.app.state.session_factory() as session:
        user = create_user(
            session,
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
            role=payload.role,
        )
        if user is None:
            raise HTTPException(status_code=409, detail='username already exists')
        return _read(user)


@router.patch('/{user_id}', response_model=UserRead)
def edit_user(user_id: int, payload: AdminUserUpdate, request: Request):
    with request.app.state.session_factory() as session:
        fields_set = payload.model_fields_set
        user = update_user(
            session,
            user_id,
            display_name=payload.display_name,
            role=payload.role,
            enabled=payload.enabled,
            password=payload.password,
            display_name_was_set='display_name' in fields_set,
        )
        if user is None:
            raise HTTPException(status_code=404, detail='user not found')
        return _read(user)
