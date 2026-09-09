from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from uuid import UUID
from app.services.communication import CARDS, save_session, statistics
from app.services.authentication import current_user, dashboard_user, linked_users, login, logout, security

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


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserResponse


class CardResponse(BaseModel):
    id: str
    label: str
    symbol: str
    category: str
    image_index: int
    count: int | None = None
    reason: str | None = None


class CommunicationSessionResponse(BaseModel):
    id: UUID
    user_id: str
    cards: list[str]
    sentence: str
    created_at: datetime


class DashboardResponse(BaseModel):
    sessions: int
    selections: int
    top_cards: list[CardResponse]
    categories: dict[str, int]
    recent: list[CommunicationSessionResponse]
    period_days: int | None


def require_communicator(user):
    if user['role'] != 'user':
        raise HTTPException(403, 'PECS 사용자만 카드 기능을 이용할 수 있습니다.')
    return user


@api_router.post('/auth/login', response_model=LoginResponse, tags=['인증'])
def authenticate(request: LoginRequest):
    return login(request.username.strip(), request.password)


@api_router.get('/auth/me', response_model=UserResponse, tags=['인증'])
def me(user=Depends(current_user)):
    return user


@api_router.get('/care/linked-users', response_model=list[UserResponse], tags=['보호자'])
def care_users(user=Depends(current_user)):
    if user['role'] != 'caregiver':
        raise HTTPException(403, '보호자 계정만 접근할 수 있습니다.')
    return linked_users(user['id'])


@api_router.post('/auth/logout', status_code=204, tags=['인증'])
def sign_out(_user=Depends(current_user), credentials=Depends(security)):
    logout(credentials)
    return None


@api_router.get('/cards', response_model=list[CardResponse], response_model_exclude_none=True, tags=['카드'])
def cards(_=Depends(current_user)):
    require_communicator(_)
    return CARDS


@api_router.post('/sentences', response_model=CommunicationSessionResponse, tags=['문장'])
def generate_sentence(request: SentenceRequest, user=Depends(current_user)):
    require_communicator(user)
    return save_session(request, user['id'])


@api_router.get('/recommendations', response_model=list[CardResponse], response_model_exclude_none=True, tags=['추천'])
def recommendations(user=Depends(current_user)):
    require_communicator(user)
    used = statistics(user['id'])['top_cards']
    keys = {c['id'] for c in used}
    frequent = [card | {'reason': f"자주 사용함 · {card['count']}회"} for card in used]
    defaults = [card | {'reason': '처음 시작하기 좋은 카드'} for card in CARDS if card['id'] not in keys]
    return (frequent + defaults)[:6]


@api_router.get('/dashboard', response_model=DashboardResponse, tags=['통계'])
def dashboard(days: int | None = Query(default=None, ge=1, le=365),
              user_id: str | None = Query(default=None, max_length=64),
              user=Depends(current_user)):
    return statistics(dashboard_user(user, user_id), days=days)
