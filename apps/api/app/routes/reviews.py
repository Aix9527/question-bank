from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.review import ManualReviewRead, ManualReviewSubmit
from app.security import require_admin
from app.services.review_service import list_pending_reviews, submit_manual_review

router = APIRouter(prefix="/api/admin/reviews", tags=["reviews"])


@router.get("/pending", response_model=list[ManualReviewRead])
def pending_reviews(request: Request, admin=Depends(require_admin)):
    with request.app.state.session_factory() as session:
        return list_pending_reviews(session)


@router.post("/{answer_id}", response_model=ManualReviewRead)
def review_answer(answer_id: int, payload: ManualReviewSubmit, request: Request, admin=Depends(require_admin)):
    with request.app.state.session_factory() as session:
        result, error = submit_manual_review(
            session,
            answer_id=answer_id,
            suggested_score=payload.suggested_score,
            final_score=payload.final_score,
            comment=payload.comment,
            rubric_json=payload.rubric_json,
            reviewer_user_id=admin.id,
        )
        if result is None:
            status_code = 404 if error in {"answer not found", "question not found"} else 400
            raise HTTPException(status_code=status_code, detail=error)
        return result
