from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from uuid import UUID
from app.services.communication import CARDS, save_session, statistics
from app.services.authentication import current_user, login, logout

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


class SentenceRequest(BaseModel):
    cards: list[str] = Field(min_length=1, max_length=12)
    request_id: UUID


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


@api_router.post('/auth/login')
def authenticate(request: LoginRequest):
    return login(request.username.strip(), request.password)


@api_router.get('/auth/me')
def me(user=Depends(current_user)):
    return user


@api_router.post('/auth/logout', status_code=204)
def sign_out(_=Depends(logout)):
    return None


@api_router.get('/cards')
def cards(_=Depends(current_user)):
    return CARDS


@api_router.post('/sentences')
def generate_sentence(request: SentenceRequest, user=Depends(current_user)):
    return save_session(request, user['id'])


@api_router.get('/recommendations')
def recommendations(user=Depends(current_user)):
    used = statistics(user['id'])['top_cards']
    keys = {c['id'] for c in used}
    return (used + [c for c in CARDS if c['id'] not in keys])[:6]


@api_router.get('/dashboard')
def dashboard(user=Depends(current_user)):
    return statistics(user['id'])
