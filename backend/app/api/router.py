from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from uuid import UUID
from app.services.communication import CARDS, save_session, statistics
from app.services.authentication import current_user, dashboard_user, linked_users, login, logout, register, security
from app.services.model import status as model_status
from app.services.caregiver_notes import delete_note, notes_for, save_note

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get('/model/status', tags=['모델'])
def get_model_status(user=Depends(current_user)):
    return model_status()


class SentenceRequest(BaseModel):
    cards: list[str] = Field(min_length=1, max_length=12)
    request_id: UUID


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(pattern=r'^[A-Za-z0-9_-]+$', min_length=4, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=30)


class CaregiverNoteRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=500)


class CaregiverNoteResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    content: str
    updated_at: datetime


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
    generation_source: str | None = None
    caregiver_note: str | None = None
    created_at: datetime


class DailyActivityResponse(BaseModel):
    date: str
    sessions: int


class AttentionResponse(CardResponse):
    count: int
    last_used_at: datetime


class DashboardResponse(BaseModel):
    sessions: int
    selections: int
    top_cards: list[CardResponse]
    categories: dict[str, int]
    recent: list[CommunicationSessionResponse]
    period_days: int | None
    today_sessions: int
    today_selections: int
    primary_emotion: CardResponse | None
    last_activity: datetime | None
    daily_activity: list[DailyActivityResponse]
    attention: list[AttentionResponse]


def require_communicator(user):
    if user['role'] != 'user':
        raise HTTPException(403, 'PECS 사용자만 카드 기능을 이용할 수 있습니다.')
    return user


@api_router.post('/auth/login', response_model=LoginResponse, tags=['인증'])
def authenticate(request: LoginRequest):
    return login(request.username.strip(), request.password)


@api_router.post('/auth/register', response_model=LoginResponse, status_code=201, tags=['인증'])
def create_account(request: RegisterRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(422, '이름을 입력해 주세요.')
    return register(request.username.strip(), request.password, name)


@api_router.get('/auth/me', response_model=UserResponse, tags=['인증'])
def me(user=Depends(current_user)):
    return user


@api_router.get('/care/linked-users', response_model=list[UserResponse], tags=['보호자'])
def care_users(user=Depends(current_user)):
    if user['role'] != 'caregiver':
        raise HTTPException(403, '보호자 계정만 접근할 수 있습니다.')
    return linked_users(user['id'])


@api_router.put('/care/notes/{session_id}', response_model=CaregiverNoteResponse, tags=['보호자'])
def put_caregiver_note(session_id: UUID, request: CaregiverNoteRequest, user=Depends(current_user)):
    if user['role'] != 'caregiver':
        raise HTTPException(403, '보호자 계정만 메모를 작성할 수 있습니다.')
    target = dashboard_user(user, request.user_id)
    content = request.content.strip()
    if not content:
        raise HTTPException(422, '메모 내용을 입력해 주세요.')
    return save_note(user['id'], target, str(session_id), content)


@api_router.delete('/care/notes/{session_id}', status_code=204, tags=['보호자'])
def remove_caregiver_note(session_id: UUID,
                          user_id: str = Query(min_length=1, max_length=64),
                          user=Depends(current_user)):
    if user['role'] != 'caregiver':
        raise HTTPException(403, '보호자 계정만 메모를 삭제할 수 있습니다.')
    target = dashboard_user(user, user_id)
    delete_note(user['id'], target, str(session_id))
    return None


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
    target = dashboard_user(user, user_id)
    result = statistics(target, days=days)
    if user['role'] == 'caregiver':
        notes = notes_for(user['id'], target, [row['id'] for row in result['recent']])
        for row in result['recent']:
            row['caregiver_note'] = notes.get(row['id'])
    return result
