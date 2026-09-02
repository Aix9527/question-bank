from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.schemas.learning import FavoriteRead, ReviewAttemptCreate, ReviewAttemptRead, WrongQuestionRead
from app.security import get_current_user
from app.services.learning_service import (
    add_favorite,
    create_wrong_review_attempt,
    list_favorites,
    list_wrong_questions,
    remove_favorite,
)

router = APIRouter(tags=["learning"])


@router.get("/api/me/wrong-questions", response_model=list[WrongQuestionRead])
def wrong_questions(request: Request, include_mastered: bool = True, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        return list_wrong_questions(session, user_id=user.id, include_mastered=include_mastered)


@router.post("/api/me/wrong-questions/review-attempt", status_code=status.HTTP_201_CREATED, response_model=ReviewAttemptRead)
def wrong_review_attempt(payload: ReviewAttemptCreate, request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        result = create_wrong_review_attempt(session, question_ids=payload.question_ids, user_id=user.id)
        if result is None:
            raise HTTPException(status_code=400, detail="no eligible wrong questions for review")
        return result


@router.get("/api/me/favorites", response_model=list[FavoriteRead])
def favorites(request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        return list_favorites(session, user_id=user.id)


@router.post("/api/questions/{question_id}/favorite", response_model=FavoriteRead)
def favorite_question(question_id: int, request: Request, response: Response, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        payload, created = add_favorite(session, question_id=question_id, user_id=user.id)
        if payload is None:
            raise HTTPException(status_code=404, detail="question not found")
        response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return payload


@router.delete("/api/questions/{question_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def unfavorite_question(question_id: int, request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        remove_favorite(session, question_id=question_id, user_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
