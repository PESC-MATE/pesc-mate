"""Curated PECS cards, rule-based sentences, and MongoDB history."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError
from app.services.database import database, log_crud

CARDS = [dict(id=k, label=l, symbol=s, category=c) for k, l, s, c in [
    ('me', '나', '🙋', '사람'), ('mom', '엄마', '👩', '사람'),
    ('water', '물', '💧', '음식'), ('rice', '밥', '🍚', '음식'),
    ('apple', '사과', '🍎', '음식'), ('milk', '우유', '🥛', '음식'),
    ('drink', '마시다', '🥤', '행동'), ('eat', '먹다', '🍽️', '행동'),
    ('go', '가다', '🚶', '행동'), ('rest', '쉬다', '🛋️', '행동'),
    ('play', '놀다', '🧸', '행동'), ('help', '도와주세요', '🤝', '행동'),
    ('toilet', '화장실', '🚻', '장소'), ('home', '집', '🏠', '장소'),
    ('happy', '좋아요', '😊', '감정'), ('hurt', '아파요', '🤕', '감정'),
    ('no', '싫어요', '🙅', '감정'), ('yes', '네', '👍', '감정'),
]]
INDEX = {card['id']: card for card in CARDS}


def _collection():
    return database().communication_sessions


def _public(document):
    result = dict(document)
    result['id'] = str(result.pop('_id'))
    created_at = result.get('created_at')
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        result['created_at'] = created_at.isoformat()
    return result


def sentence(ids):
    if any(key not in INDEX for key in ids):
        raise HTTPException(422, '알 수 없는 카드가 포함되어 있습니다.')
    prefix = '저는 ' if ids[0] == 'me' else ''
    rest = ids[1:] if prefix else ids
    if len(rest) == 2:
        noun, verb = rest
        objects = dict(water='물을', rice='밥을', apple='사과를', milk='우유를')
        places = dict(home='집에', toilet='화장실에')
        if noun in objects and verb in ('eat', 'drink'):
            return prefix + objects[noun] + (' 먹고 싶어요.' if verb == 'eat' else ' 마시고 싶어요.')
        if noun in places and verb == 'go':
            return prefix + places[noun] + ' 가고 싶어요.'
    return ' · '.join(INDEX[key]['label'] for key in ids)


def save_session(request, user_id):
    card_ids = list(request.cards)
    result = sentence(card_ids)
    request_id = str(request.request_id)
    try:
        collection = _collection()
        existing = collection.find_one({'_id': request_id, 'user_id': user_id})
        log_crud('READ', 'communication_sessions', '중복 요청 확인')
        if existing:
            if existing['cards'] != card_ids:
                raise HTTPException(409, '같은 요청 번호에 다른 카드가 전달되었습니다.')
            return _public(existing)
        document = {'_id': request_id, 'user_id': user_id, 'cards': card_ids, 'sentence': result, 'created_at': datetime.now(timezone.utc)}
        try:
            collection.insert_one(document)
            log_crud('CREATE', 'communication_sessions', '문장 기록 저장')
        except DuplicateKeyError:
            existing = collection.find_one({'_id': request_id, 'user_id': user_id})
            log_crud('READ', 'communication_sessions', '동시 요청 결과 확인')
            if not existing or existing['cards'] != card_ids:
                raise HTTPException(409, '같은 요청 번호에 다른 카드가 전달되었습니다.')
            return _public(existing)
        return _public(document)
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(503, 'MongoDB에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.') from exc


def statistics(user_id, days=None, now=None):
    query = {'user_id': user_id}
    if days is not None:
        reference_time = now or datetime.now(timezone.utc)
        query['created_at'] = {'$gte': reference_time - timedelta(days=days)}
    try:
        rows = [_public(row) for row in _collection().find(query).sort('created_at', -1)]
        period = f'최근 {days}일' if days is not None else '전체 기간'
        log_crud('READ', 'communication_sessions', f'사용자 통계 조회 ({period})')
    except PyMongoError as exc:
        raise HTTPException(503, 'MongoDB에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.') from exc
    counts = Counter(key for row in rows for key in row['cards'])
    categories = Counter()
    for key, count in counts.items():
        if key in INDEX:
            categories[INDEX[key]['category']] += count
    return dict(sessions=len(rows), selections=sum(counts.values()),
                top_cards=[INDEX[key] | {'count': count} for key, count in counts.most_common() if key in INDEX],
                categories=dict(categories), recent=rows[:10], period_days=days)
