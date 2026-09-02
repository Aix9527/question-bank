from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.ai_review import AIReviewSuggestionRead
from app.services.ai_grading import AIGradingError, AIGradingNotFound, save_ai_suggestion, suggestion_payload

router = APIRouter(prefix='/api/admin/reviews', tags=['ai-reviews'])


@router.post('/{answer_id}/ai-suggest', response_model=AIReviewSuggestionRead)
def ai_suggest(answer_id: int, request: Request):
    grader = getattr(request.app.state, 'ai_grader', None)
    if grader is None:
        raise HTTPException(status_code=503, detail='AI grading is not configured')
    with request.app.state.session_factory() as session:
        try:
            row = save_ai_suggestion(
                session,
                answer_id=answer_id,
                grader=grader,
                provider=request.app.state.settings.ai_provider if request.app.state.settings.ai_provider != 'disabled' else 'test',
                model=getattr(grader, 'model', None),
            )
        except AIGradingNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except AIGradingError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return suggestion_payload(row)
