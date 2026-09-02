from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

router = APIRouter(prefix='/api/health', tags=['health'])


@router.get('/live')
def live():
    return {'status': 'ok'}


@router.get('/ready')
def ready(request: Request):
    try:
        with request.app.state.session_factory() as session:
            session.execute(text('SELECT 1'))
    except Exception as exc:
        raise HTTPException(status_code=503, detail='database unavailable') from exc
    return {'status': 'ready', 'database': 'ok'}
