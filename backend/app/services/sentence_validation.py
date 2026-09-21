"""Validate that generated sentences preserve the selected card meanings."""
import re
import unicodedata


SEMANTIC_TOKENS = {
    'me': ('저는', '제가', '저를', '저도', '나는', '내가', '나를', '나도'),
    'mom': ('엄마',),
    'water': ('물',),
    'rice': ('밥',),
    'apple': ('사과',),
    'milk': ('우유',),
    'drink': ('마시', '마셔', '마실'),
    'eat': ('먹',),
    'go': ('가고', '가요', '갈래', '갈게', '갑니다', '이동'),
    'rest': ('쉬', '쉴', '휴식'),
    'play': ('놀', '놀이'),
    'help': ('도와', '도움'),
    'toilet': ('화장실',),
    'home': ('집', '가정'),
    'happy': ('좋', '행복', '기뻐'),
    'hurt': ('아프', '아파', '통증', '다쳤'),
    'no': ('싫', '아니', '않', '못', '거절', '원하지'),
    'yes': ('네', '응', '동의', '좋아'),
}


def _normalize(value):
    normalized = unicodedata.normalize('NFKC', value).lower()
    return re.sub(r'[^0-9a-z가-힣]', '', normalized)


def _tokens_for(card):
    if card['id'] in SEMANTIC_TOKENS:
        return SEMANTIC_TOKENS[card['id']]
    label = card['label'].strip()
    if card.get('part_of_speech') in {'verb', 'adjective'} and label.endswith('다'):
        return (label, label[:-1])
    return (label,)


def validate_semantics(cards, generated_sentence):
    normalized_sentence = _normalize(generated_sentence)
    missing = []
    checked = set()
    for card in cards:
        if card['id'] in checked:
            continue
        checked.add(card['id'])
        tokens = tuple(_normalize(token) for token in _tokens_for(card))
        if not any(token and token in normalized_sentence for token in tokens):
            missing.append(card['id'])
    return {'passed': not missing, 'missing_card_ids': missing}
