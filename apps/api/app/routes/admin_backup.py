from __future__ import annotations

from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.services.backup import backup_sqlite_bytes
from app.services.export import build_csv_zip, build_export

router = APIRouter(prefix='/api/admin', tags=['admin-backup'])


@router.get('/export')
def admin_export(request: Request, format: str = Query(default='json', pattern='^(json|csv)$')):
    with request.app.state.session_factory() as session:
        payload = build_export(session)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    if format == 'json':
        return Response(
            content=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
            media_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="question-bank-export-{stamp}.json"'},
        )
    content = build_csv_zip(payload)
    return Response(
        content=content,
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="question-bank-export-{stamp}.zip"'},
    )


@router.get('/backup/database')
def admin_database_backup(request: Request):
    try:
        content = backup_sqlite_bytes(request.app.state.settings.database_url)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    return Response(
        content=content,
        media_type='application/vnd.sqlite3',
        headers={'Content-Disposition': f'attachment; filename="question-bank-{stamp}.db"'},
    )
