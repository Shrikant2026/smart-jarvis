from fastapi import APIRouter, HTTPException

from app.models.schemas import LearnRequest, LearnResponse
from app.services.memory import store_memory

router = APIRouter()


@router.post("/learn", response_model=LearnResponse)
def learn(request: LearnRequest):
    text = request.text.strip()

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Knowledge cannot be empty.",
        )

    try:
        store_memory(text, source="knowledge")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not store the knowledge.",
        ) from exc

    return LearnResponse(
        message="Knowledge stored successfully."
    )