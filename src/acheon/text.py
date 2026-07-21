"""Small deterministic text utilities used by the offline core."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable

_WORD_RE = re.compile(r"[a-z0-9_./:#-]+", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_SPACE_RE = re.compile(r"\s+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "的",
    "了",
    "和",
    "是",
}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _SPACE_RE.sub(" ", normalized).strip()


def tokenize(value: str) -> tuple[str, ...]:
    """Tokenize Latin text and add CJK unigrams/bigrams without dependencies."""

    normalized = normalize_text(value)
    words = [token for token in _WORD_RE.findall(normalized) if token not in _STOPWORDS]
    cjk = _CJK_RE.findall(normalized)
    words.extend(char for char in cjk if char not in _STOPWORDS)
    words.extend(a + b for a, b in zip(cjk, cjk[1:], strict=False))
    return tuple(words)


def estimate_tokens(value: str) -> int:
    """Deterministic provider-independent token-unit estimate for budgeting."""

    if not value:
        return 0
    ascii_chars = sum(1 for char in value if ord(char) < 128)
    non_ascii = len(value) - ascii_chars
    return max(1, math.ceil(ascii_chars / 3.6 + non_ascii / 1.25))


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set, right_set = set(left), set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def overlap_score(query_tokens: Iterable[str], document_tokens: Iterable[str]) -> float:
    """Blend query coverage and Jaccard similarity for stable lexical ranking."""

    query_set, document_set = set(query_tokens), set(document_tokens)
    if not query_set or not document_set:
        return 0.0
    intersection = len(query_set & document_set)
    coverage = intersection / len(query_set)
    similarity = intersection / len(query_set | document_set)
    return 0.7 * coverage + 0.3 * similarity
