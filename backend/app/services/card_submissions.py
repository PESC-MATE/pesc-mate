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


def _audit_collection():
    return database().card_audit_logs


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
        'image_url': f"/api/cards/submissions/{document['_id']}/image",
        'review_reason': document.get('review_reason'),
        'reviewer_id': document.get('reviewer_id'),
        'reviewed_at': document.get('reviewed_at'),
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


def submissions_for_review():
    try:
        rows = _collection().find({}).sort('created_at', -1)
        log_crud('READ', 'card_submissions', '관리자 승인 목록 조회')
        return [_public(row) for row in rows]
    except PyMongoError as exc:
        raise HTTPException(503, '카드 승인 목록을 불러오지 못했습니다.') from exc


def review_submission(submission_id, reviewer_id, decision, reason=''):
    if decision not in {'approved', 'rejected'}:
        raise HTTPException(422, '승인 또는 반려만 선택할 수 있습니다.')
    reason = reason.strip()
    if decision == 'rejected' and not reason:
        raise HTTPException(422, '반려 사유를 입력해 주세요.')
    try:
        collection = _collection()
        document = collection.find_one({'_id': submission_id})
        if not document:
            raise HTTPException(404, '카드 등록 요청을 찾을 수 없습니다.')
        if document['status'] != 'pending':
            raise HTTPException(409, '이미 처리된 카드 요청입니다.')
        reviewed_at = datetime.now(timezone.utc)
        changes = {'status': decision, 'review_reason': reason or None,
                   'reviewer_id': reviewer_id, 'reviewed_at': reviewed_at}
        collection.update_one({'_id': submission_id, 'status': 'pending'}, {'$set': changes})
        _audit_collection().insert_one({
            '_id': str(uuid4()), 'card_submission_id': submission_id,
            'actor_id': reviewer_id, 'action': decision,
            'reason': reason or None, 'created_at': reviewed_at,
        })
        log_crud('UPDATE', 'card_submissions', f'카드 {decision}')
        log_crud('CREATE', 'card_audit_logs', '카드 승인 작업 기록')
        return _public(document | changes)
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(503, '카드 승인 결과를 저장하지 못했습니다.') from exc


def approved_cards_for(owner_id):
    try:
        rows = _collection().find({'status': 'approved'}).sort('created_at', 1)
        visible = [row for row in rows if row['visibility'] == 'shared' or row['owner_id'] == owner_id]
        return [{
            'id': f"custom:{row['_id']}", 'label': row['label'], 'meaning': row['meaning'],
            'symbol': '🖼️', 'category': row['category'], 'image_index': None,
            'image_url': f"/api/cards/submissions/{row['_id']}/image", 'custom': True,
        } for row in visible]
    except PyMongoError as exc:
        raise HTTPException(503, '사용자 카드를 불러오지 못했습니다.') from exc


def image_for(submission_id, requester):
    try:
        document = _collection().find_one({'_id': submission_id})
        if not document:
            raise HTTPException(404, '카드 이미지를 찾을 수 없습니다.')
        can_review = requester['role'] == 'admin'
        can_use = document['status'] == 'approved' and (
            document['visibility'] == 'shared' or document['owner_id'] == requester['id']
        )
        if not can_review and not can_use:
            raise HTTPException(403, '이 카드 이미지를 볼 수 없습니다.')
        return document['image']['data'], document['image']['content_type']
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise HTTPException(503, '카드 이미지를 불러오지 못했습니다.') from exc
