from fastapi import APIRouter
from pydantic import BaseModel, Field
from uuid import UUID
from app.services.communication import CARDS, save_session, statistics

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


class SentenceRequest(BaseModel):
    cards: list[str] = Field(min_length=1, max_length=12)
    request_id: UUID


@api_router.get('/cards')
def cards():
    return CARDS


@api_router.post('/sentences')
def generate_sentence(request: SentenceRequest):
    return save_session(request)


@api_router.get('/recommendations')
def recommendations():
    used = statistics()['top_cards']
    keys = {c['id'] for c in used}
    return (used + [c for c in CARDS if c['id'] not in keys])[:6]


@api_router.get('/dashboard')
def dashboard():
    return statistics()
