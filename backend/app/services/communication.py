"""Curated PECS cards, rule-based sentences, and MongoDB history."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError, PyMongoError
from app.services.card_metadata import with_inferred_metadata
from app.services.database import database, log_crud
from app.services.model import generate_sentence

CARDS = [with_inferred_metadata(dict(id=key, label=label, symbol=symbol, category=category,
                                      meaning=meaning, part_of_speech=part_of_speech,
                                      sentence_role=sentence_role, image_index=index))
         for index, (key, label, symbol, category, meaning, part_of_speech, sentence_role) in enumerate([
    ('me', '나', '🙋', '사람', '말하는 사용자 자신', 'pronoun', 'subject'),
    ('mom', '엄마', '👩', '사람', '사용자의 어머니', 'noun', 'subject'),
    ('water', '물', '💧', '음식', '마시는 물', 'noun', 'object'),
    ('rice', '밥', '🍚', '음식', '먹는 밥', 'noun', 'object'),
    ('apple', '사과', '🍎', '음식', '과일 사과', 'noun', 'object'),
    ('milk', '우유', '🥛', '음식', '마시는 우유', 'noun', 'object'),
    ('drink', '마시다', '🥤', '행동', '음료를 마시는 행동', 'verb', 'predicate'),
    ('eat', '먹다', '🍽️', '행동', '음식을 먹는 행동', 'verb', 'predicate'),
    ('go', '가다', '🚶', '행동', '장소로 이동하는 행동', 'verb', 'predicate'),
    ('rest', '쉬다', '🛋️', '행동', '휴식을 취하는 행동', 'verb', 'predicate'),
    ('play', '놀다', '🧸', '행동', '놀이를 하는 행동', 'verb', 'predicate'),
    ('help', '도와주세요', '🤝', '행동', '다른 사람에게 도움을 요청함', 'verb', 'predicate'),
    ('toilet', '화장실', '🚻', '장소', '화장실 장소', 'noun', 'destination'),
    ('home', '집', '🏠', '장소', '사용자가 생활하는 집', 'noun', 'destination'),
    ('happy', '좋아요', '😊', '감정', '좋거나 만족스러운 감정', 'adjective', 'predicate'),
    ('hurt', '아파요', '🤕', '감정', '몸이 아픈 상태', 'adjective', 'predicate'),
    ('no', '싫어요', '🙅', '감정', '원하지 않거나 거절하는 표현', 'adjective', 'predicate'),
    ('yes', '네', '👍', '감정', '동의하거나 긍정하는 표현', 'interjection', 'response'),
])]
INDEX = {card['id']: card for card in CARDS}

PARTICLES = {
    'topic': ('은', '는'),
    'subject': ('이', '가'),
    'object': ('을', '를'),
    'with': ('과', '와'),
}

PREDICATE_PHRASES = {
    'drink': '마시고 싶어요.',
    'eat': '먹고 싶어요.',
    'go': '가고 싶어요.',
    'rest': '쉬고 싶어요.',
    'play': '놀고 싶어요.',
    'help': '도와주세요.',
    'happy': '좋아요.',
    'hurt': '아파요.',
    'no': '싫어요.',
    'yes': '네.',
}


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


def attach_particle(card, kind):
    if kind == 'location':
        return f"{card['label']}에"
    batchim_particle, vowel_particle = PARTICLES[kind]
    return f"{card['label']}{batchim_particle if card['has_batchim'] else vowel_particle}"


def _format_group(cards, final_particle):
    if not cards:
        return ''
    connected = [attach_particle(card, 'with') for card in cards[:-1]]
    return ' '.join(connected + [attach_particle(cards[-1], final_particle)])


def _predicate_phrase(card):
    if card['id'] in PREDICATE_PHRASES:
        return PREDICATE_PHRASES[card['id']]
    label = card['label']
    if card['part_of_speech'] == 'verb' and label.endswith('다'):
        return f'{label[:-1]}고 싶어요.'
    return f"{label}{'' if label.endswith(('.', '!', '?')) else '.'}"


def sentence(ids, card_index=None):
    cards = card_index or INDEX
    if any(key not in cards for key in ids):
        raise HTTPException(422, '알 수 없는 카드가 포함되어 있습니다.')
    selected = [with_inferred_metadata(cards[key]) for key in ids]
    if selected and selected[-1]['sentence_role'] in {'predicate', 'response'}:
        predicate = selected[-1]
        arguments = selected[:-1]
        subjects = [card for card in arguments if card['sentence_role'] == 'subject']
        objects = [card for card in arguments if card['sentence_role'] == 'object']
        destinations = [card for card in arguments if card['sentence_role'] == 'destination']
        parts = []
        if subjects:
            if len(subjects) == 1 and subjects[0]['id'] == 'me':
                parts.append(attach_particle(subjects[0] | {'label': '저', 'has_batchim': False}, 'topic'))
            else:
                parts.append(_format_group(subjects, 'subject'))
        if objects:
            object_particle = 'subject' if predicate['part_of_speech'] == 'adjective' else 'object'
            parts.append(_format_group(objects, object_particle))
        if destinations:
            parts.append(_format_group(destinations, 'location'))
        if len(subjects) + len(objects) + len(destinations) == len(arguments):
            parts.append(_predicate_phrase(predicate))
            return ' '.join(parts)
    return ' · '.join(cards[key]['label'] for key in ids)


def save_session(request, user_id, custom_cards=None):
    card_ids = list(request.cards)
    custom_index = {card['id']: with_inferred_metadata(card) for card in (custom_cards or [])}
    card_index = INDEX | custom_index
    fallback = sentence(card_ids, card_index)
    result, generation_source = generate_sentence([card_index[key]['label'] for key in card_ids], fallback)
    request_id = str(request.request_id)
    try:
        collection = _collection()
        existing = collection.find_one({'_id': request_id, 'user_id': user_id})
        log_crud('READ', 'communication_sessions', '중복 요청 확인')
        if existing:
            if existing['cards'] != card_ids:
                raise HTTPException(409, '같은 요청 번호에 다른 카드가 전달되었습니다.')
            return _public(existing)
        snapshots = {key: {field: card_index[key].get(field) for field in (
            'id', 'label', 'symbol', 'category', 'meaning', 'part_of_speech', 'has_batchim', 'sentence_role')}
                     for key in card_ids if key in custom_index}
        document = {'_id': request_id, 'user_id': user_id, 'cards': card_ids, 'card_metadata': snapshots,
                    'sentence': result,
                    'generation_source': generation_source, 'created_at': datetime.now(timezone.utc)}
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
    reference_time = now or datetime.now(timezone.utc)
    query = {'user_id': user_id}
    if days is not None:
        query['created_at'] = {'$gte': reference_time - timedelta(days=days)}
    try:
        rows = [_public(row) for row in _collection().find(query).sort('created_at', -1)]
        period = f'최근 {days}일' if days is not None else '전체 기간'
        log_crud('READ', 'communication_sessions', f'사용자 통계 조회 ({period})')
    except PyMongoError as exc:
        raise HTTPException(503, 'MongoDB에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.') from exc
    counts = Counter(key for row in rows for key in row['cards'])
    card_index = dict(INDEX)
    for row in rows:
        card_index.update(row.get('card_metadata') or {})
    categories = Counter()
    for key, count in counts.items():
        if key in card_index:
            categories[card_index[key]['category']] += count
    today = reference_time.date()
    today_rows = [row for row in rows if datetime.fromisoformat(row['created_at']).date() == today]
    daily_counts = Counter(datetime.fromisoformat(row['created_at']).date().isoformat() for row in rows)
    daily_activity = [
        {'date': (today - timedelta(days=offset)).isoformat(),
         'sessions': daily_counts[(today - timedelta(days=offset)).isoformat()]}
        for offset in range(6, -1, -1)
    ]
    primary_emotion_key = next((key for key, _ in counts.most_common() if key in {'happy', 'hurt', 'no', 'yes'}), None)
    primary_emotion = INDEX[primary_emotion_key] if primary_emotion_key else None
    attention = []
    for key in ('hurt', 'help', 'no'):
        matching = [row for row in rows if key in row['cards']]
        if matching:
            attention.append(INDEX[key] | {'count': sum(row['cards'].count(key) for row in matching),
                                           'last_used_at': matching[0]['created_at']})
    return dict(sessions=len(rows), selections=sum(counts.values()),
                top_cards=[card_index[key] | {'count': count} for key, count in counts.most_common() if key in card_index],
                categories=dict(categories), recent=rows[:10], period_days=days,
                today_sessions=len(today_rows),
                today_selections=sum(len(row['cards']) for row in today_rows),
                primary_emotion=primary_emotion,
                last_activity=rows[0]['created_at'] if rows else None,
                daily_activity=daily_activity,
                attention=attention)


def ensure_demo_history(user_id):
    """Create stable sample records only when the demo user has no history."""
    collection = _collection()
    if collection.count_documents({'user_id': user_id}, limit=1):
        return
    now = datetime.now(timezone.utc)
    samples = [
        ('10000000-0000-4000-8000-000000000001', ['me', 'water', 'drink'], 1),
        ('10000000-0000-4000-8000-000000000002', ['me', 'rice', 'eat'], 4),
        ('10000000-0000-4000-8000-000000000003', ['toilet', 'go'], 12),
        ('10000000-0000-4000-8000-000000000004', ['help'], 38),
    ]
    for request_id, cards, days_ago in samples:
        collection.update_one(
            {'_id': request_id},
            {'$setOnInsert': {'user_id': user_id, 'cards': cards, 'sentence': sentence(cards),
                              'created_at': now - timedelta(days=days_ago), 'source': 'demo'}},
            upsert=True,
        )
    log_crud('CREATE', 'communication_sessions', '시연용 기록 생성')
