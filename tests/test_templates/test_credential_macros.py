"""Тесты рендеринга макросов с секретами.

Проверяем, что пароль доезжает до data-атрибута байт в байт: браузер не
парсит JSON в HTML-атрибутах, поэтому |tojson там ломает спецсимволы.
"""

import re

import pytest
from html import unescape

MACROS = "{% import 'macros/credentials.html' as cred %}"

# Пароли с символами, которые ломались при |tojson в атрибуте.
TRICKY_SECRETS = [
    r"nb7\Fyhqa#%z55&g}&3%:",
    r"a&b<c>d",
    r"back\\slash",
    "quote\"inside",
    "apos'inside",
    "unicode—тире",
    r"tab\tliteral",
]


def _attr(html, name):
    """Достаёт значение атрибута name и разэкранирует его как это делает браузер."""
    match = re.search(r'%s="([^"]*)"' % re.escape(name), html)
    assert match is not None, "атрибут %s не найден в: %s" % (name, html)
    return unescape(match.group(1))


@pytest.mark.parametrize("secret", TRICKY_SECRETS)
def test_password_display_preserves_secret(app, secret):
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_display(value) }}"
    ).render(value=secret)

    assert _attr(html, "data-password") == secret


@pytest.mark.parametrize("secret", TRICKY_SECRETS)
def test_text_copy_display_preserves_value(app, secret):
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.text_copy_display(value) }}"
    ).render(value=secret)

    assert _attr(html, "data-copy-value") == secret


def test_password_display_escapes_html(app):
    """Значение экранируется, а не вставляется сырым — иначе XSS."""
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_display(value) }}"
    ).render(value='"><script>alert(1)</script>')

    assert "<script>" not in html
    assert _attr(html, "data-password") == '"><script>alert(1)</script>'


def test_password_display_attribute_is_quoted(app):
    """Атрибут должен быть в кавычках: без них пробел в значении рвёт разметку."""
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_display(value) }}"
    ).render(value="two words")

    assert 'data-password="two words"' in html


def test_current_secret_row_preserves_secret(app):
    secret = r"nb7\Fyhqa#%z55&g}&3%:"
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.current_secret_row(value) }}"
    ).render(value=secret)

    assert _attr(html, "data-password") == secret
