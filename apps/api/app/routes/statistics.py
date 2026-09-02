from fastapi import APIRouter, Depends, Request

from app.security import get_current_user
from app.services.statistics import get_history, get_statistics

router = APIRouter(prefix="/api/me", tags=["statistics"])


@router.get("/history")
def history(request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        return get_history(session, user_id=user.id)


@router.get("/statistics")
def statistics(request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        return get_statistics(session, user_id=user.id)
