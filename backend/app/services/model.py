"""Ollama-backed Korean sentence generation with a safe local fallback."""
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger('uvicorn.error')


def enabled():
    return os.environ.get('OLLAMA_ENABLED', 'false').lower() in {'1', 'true', 'yes', 'on'}


def generate_sentence(labels, fallback):
    if not enabled():
        return fallback, 'rule'
    base_url = os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    model = os.environ.get('OLLAMA_MODEL', 'qwen2.5:0.5b')
    payload = json.dumps({
        'model': model, 'stream': False, 'think': False, 'keep_alive': '10m',
        'system': ('당신은 PECS 보완대체의사소통 도우미입니다. 주어진 카드의 순서와 의미를 유지해 '
                   '쉽고 자연스러운 한국어 한 문장만 출력하세요. 설명, 따옴표, 새로운 사실을 추가하지 마세요.'),
        'prompt': f"선택 카드: {' → '.join(labels)}\n기본 문장: {fallback}\n출력:",
        'options': {'temperature': 0.1, 'num_predict': 60},
    }, ensure_ascii=False).encode('utf-8')
    request = Request(f'{base_url}/api/generate', data=payload,
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=float(os.environ.get('OLLAMA_TIMEOUT_SECONDS', '60'))) as response:
            result = json.load(response)
        text = str(result.get('response', '')).strip().strip('"')
        if not text or len(text) > 150 or '\n' in text:
            raise ValueError('유효하지 않은 모델 응답')
        logger.info('MODEL | OLLAMA | %s | 문장 생성 성공', model)
        return text, 'ollama'
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
        logger.warning('MODEL | FALLBACK | 규칙 기반 문장 사용 (%s)', type(exc).__name__)
        return fallback, 'rule'


def status():
    return {'enabled': enabled(), 'model': os.environ.get('OLLAMA_MODEL', 'qwen2.5:0.5b')}
