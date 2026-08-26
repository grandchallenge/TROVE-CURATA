from __future__ import annotations
import re
import unicodedata
from .trove_curata_duplicate_contract import require

def normalize_duplicate_text(value: str) -> str:
    normalized = unicodedata.normalize('NFC', value.replace('\r\n', '\n').replace('\r', '\n'))
    return ' '.join(normalized.lower().split())

def normalize_predecessor_text(value: str) -> str:
    normalized = unicodedata.normalize('NFC', value.replace('\r\n', '\n').replace('\r', '\n'))
    lines = [re.sub('[\\t ]+', ' ', line.strip()) for line in normalized.split('\n')]
    return '\n'.join((line for line in lines if line)).strip()

def tokenize(value: str) -> list[str]:
    return re.findall("[^\\W_]+(?:['’-][^\\W_]+)*", normalize_duplicate_text(value), flags=re.UNICODE)

def shingle_set(value: str, size: int=3) -> set[str]:
    require(isinstance(size, int) and size >= 1, 'shingle size must be positive')
    items = tokenize(value)
    if not items:
        return set()
    if len(items) < size:
        return {'\x1f'.join(items)}
    return {'\x1f'.join(items[index:index + size]) for index in range(len(items) - size + 1)}

def score_text(value: float) -> str:
    require(0.0 <= value <= 1.0, 'similarity score outside [0,1]')
    return f'{value:.6f}'

def jaccard_score(left: set[str], right: set[str]) -> float:
    union = left | right
    return 1.0 if not union else len(left & right) / len(union)
