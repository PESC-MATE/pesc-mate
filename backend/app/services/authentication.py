"""MongoDB-backed prototype authentication with opaque session tokens."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo import MongoClient
from pymongo.errors import PyMongoError

SESSION_HOURS = 12
security = HTTPBearer(auto_error=False)


def _database():
    client = MongoClient(
        os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017'),
        serverSelectionTimeoutMS=3000,
    )
    return client[os.environ.get('MONGODB_DATABASE', 'pesc_mate')]


def _password_hash(password, salt=None):
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt_bytes, 310_000)
    return salt_bytes.hex(), digest.hex()


def _public_user(user):
    return {'id': str(user['_id']), 'username': user['username'], 'name': user['name'], 'role': user['role']}


def ensure_demo_user():
    username = os.environ.get('DEMO_USERNAME', 'demo')
    password = os.environ.get('DEMO_PASSWORD', 'demo1234')
    salt, password_hash = _password_hash(password)
    database = _database()
    database.users.update_one(
        {'_id': username},
        {'$set': {'username': username, 'name': '데모 사용자', 'role': 'user',
                  'password_salt': salt, 'password_hash': password_hash},
         '$setOnInsert': {'created_at': datetime.now(timezone.utc)}},
        upsert=True,
    )


def login(username, password):
    try:
        ensure_demo_user()
        database = _database()
        user = database.users.find_one({'username': username})
        if not user:
            raise HTTPException(401, '아이디 또는 비밀번호가 올바르지 않습니다.')
        _, candidate = _password_hash(password, user['password_salt'])
        if not hmac.compare_digest(candidate, user['password_hash']):
            raise HTTPException(401, '아이디 또는 비밀번호가 올바르지 않습니다.')
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        database.auth_sessions.insert_one({
            '_id': hashlib.sha256(token.encode()).hexdigest(),
            'user_id': str(user['_id']),
            'expires_at': expires_at,
        })
        return {'access_token': token, 'token_type': 'bearer', 'expires_at': expires_at.isoformat(),
                'user': _public_user(user)}
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(503, '로그인 저장소에 연결하지 못했습니다.') from exc


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.scheme.lower() != 'bearer':
        raise HTTPException(401, '로그인이 필요합니다.', headers={'WWW-Authenticate': 'Bearer'})
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    try:
        database = _database()
        session = database.auth_sessions.find_one({'_id': token_hash})
        now = datetime.now(timezone.utc)
        expires_at = session.get('expires_at') if session else None
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if not session or not expires_at or expires_at <= now:
            if session:
                database.auth_sessions.delete_one({'_id': token_hash})
            raise HTTPException(401, '로그인 시간이 만료되었습니다.', headers={'WWW-Authenticate': 'Bearer'})
        user = database.users.find_one({'_id': session['user_id']})
        if not user:
            raise HTTPException(401, '사용자 계정을 찾을 수 없습니다.')
        return _public_user(user)
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(503, '로그인 저장소에 연결하지 못했습니다.') from exc


def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials:
        try:
            _database().auth_sessions.delete_one({'_id': hashlib.sha256(credentials.credentials.encode()).hexdigest()})
        except PyMongoError as exc:
            raise HTTPException(503, '로그아웃을 처리하지 못했습니다.') from exc
