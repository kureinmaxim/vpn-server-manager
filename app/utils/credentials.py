"""Нормализация паролей и секретов перед сохранением / использованием."""
from __future__ import annotations

import base64
import re
import unicodedata

# Невидимые / format-символы, часто попадающие при копировании из писем и веб-кабинетов
_INVISIBLE_RE = re.compile(
    r'[\u200B-\u200D\u2060\uFEFF\u00AD'
    r'\u202A-\u202E\u2066-\u2069]'
)


def sanitize_secret(value: str | None, *, strip_whitespace: bool = True) -> str:
    """
    Очищает пароль/логин от артефактов вставки.

    - убирает CR/LF (многострочная вставка)
    - убирает zero-width / BOM / soft hyphen / bidi marks
    - нормализует Unicode (NFC)
    - по умолчанию trim пробелов по краям (типичный мусор из буфера)
    """
    if value is None:
        return ''
    text = str(value)
    if not text:
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '')
    text = _INVISIBLE_RE.sub('', text)
    text = unicodedata.normalize('NFC', text)
    if strip_whitespace:
        text = text.strip()
    return text


def encode_secret_attr(value: str | None) -> str:
    """Base64 for HTML attributes so `%`, `&`, `#` are not URL/entity-decoded by the WebView."""
    text = '' if value is None else str(value)
    return base64.b64encode(text.encode('utf-8')).decode('ascii')
