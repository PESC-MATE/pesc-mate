"""User card submissions waiting for administrator review."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import PyMongoError

from app.services.database import database, log_crud

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _collection():
    return database().card_submissions


def _public(document):
    return {
        'id': str(document['_id']),
        'label': document['label'],
        'meaning': document['meaning'],
        'category': document['category'],
        'visibility': document['visibility'],
        'owner_id': document['owner_id'],
        'status': document['status'],
        'image_filename': document['image']['filename'],
        'image_content_type': document['image']['content_type'],
        'created_at': document['created_at'],
    }


def create_submission(owner_id, label, meaning, category, visibility,
                      image_filename, image_content_type, image_data):
    label = label.strip()
    meaning = meaning.strip()
    category = category.strip()
    if not label or not meaning or not category:
        raise HTTPException(422, '카드명과 뜻, 카테고리를 모두 입력해 주세요.')
    if visibility not in {'private', 'shared'}:
        raise HTTPException(422, '공개 범위가 올바르지 않습니다.')
    if image_content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(422, 'JPG, PNG, WebP 이미지만 등록할 수 있습니다.')
    if not image_data or len(image_data) > MAX_IMAGE_BYTES:
        raise HTTPException(422, '이미지는 5MB 이하로 등록해 주세요.')

    document = {
        '_id': str(uuid4()),
        'label': label,
        'meaning': meaning,
        'category': category,
        'visibility': visibility,
        'owner_id': owner_id,
        'status': 'pending',
        'image': {
            'filename': image_filename or 'card-image',
            'content_type': image_content_type,
            'data': image_data,
        },
        'created_at': datetime.now(timezone.utc),
    }
    try:
        _collection().insert_one(document)
        log_crud('CREATE', 'card_submissions', '카드 승인 요청 저장')
        return _public(document)
    except PyMongoError as exc:
        raise HTTPException(503, '카드 등록 요청을 저장하지 못했습니다.') from exc


def submissions_for(owner_id):
    try:
        rows = _collection().find({'owner_id': owner_id}).sort('created_at', -1)
        log_crud('READ', 'card_submissions', '본인 카드 요청 조회')
        return [_public(row) for row in rows]
    except PyMongoError as exc:
        raise HTTPException(503, '카드 등록 내역을 불러오지 못했습니다.') from exc
