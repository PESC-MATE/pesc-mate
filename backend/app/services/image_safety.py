"""Pluggable image-content safety checks with a manual-review fallback."""
import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check_image_safety(image_data, content_type):
    endpoint = os.environ.get('IMAGE_SAFETY_API_URL', '').strip()
    if not endpoint:
        return {
            'status': 'manual_review',
            'provider': 'administrator',
            'reasons': ['자동 검사 공급자가 설정되지 않아 수동 검토가 필요합니다.'],
        }

    payload = json.dumps({
        'image_base64': base64.b64encode(image_data).decode('ascii'),
        'mime_type': content_type,
    }).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    token = os.environ.get('IMAGE_SAFETY_API_TOKEN', '').strip()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = Request(endpoint, data=payload, headers=headers, method='POST')
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
        safe = result.get('safe') is True
        return {
            'status': 'passed' if safe else 'blocked',
            'provider': result.get('provider') or 'configured-api',
            'reasons': [str(reason)[:200] for reason in result.get('reasons', [])[:5]],
        }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return {
            'status': 'manual_review',
            'provider': 'administrator',
            'reasons': ['자동 검사에 실패해 수동 검토로 전환됐습니다.'],
        }
