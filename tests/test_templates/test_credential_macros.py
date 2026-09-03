"""Тесты рендеринга макросов с секретами.

Проверяем, что пароль доезжает до data-атрибута байт в байт: браузер не
парсит JSON в HTML-атрибутах, поэтому |tojson там ломает спецсимволы.
"""

import base64
import re

import pytest
from html import unescape

MACROS = "{% import 'macros/credentials.html' as cred %}"

# Пароли с символами, которые ломались при |tojson в атрибуте и при URL-decode `%:`.
TRICKY_SECRETS = [
    r"nb7\Fyhqa#%z55&g}&3%:",
    "aguJ#%z&g}&%:",
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


def _secret_from_display(html):
    assert 'data-enc="b64"' in html
    return base64.b64decode(_attr(html, "data-password")).decode("utf-8")


@pytest.mark.parametrize("secret", TRICKY_SECRETS)
def test_password_display_preserves_secret(app, secret):
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_display(value) }}"
    ).render(value=secret)

    assert _secret_from_display(html) == secret


@pytest.mark.parametrize("secret", TRICKY_SECRETS)
def test_text_copy_display_preserves_value(app, secret):
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.text_copy_display(value) }}"
    ).render(value=secret)

    assert _attr(html, "data-copy-value") == secret


def test_password_display_escapes_html(app):
    """Секрет в атрибуте — base64, не сырой HTML."""
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_display(value) }}"
    ).render(value='"><script>alert(1)</script>')

    assert "<script>" not in html
    assert _secret_from_display(html) == '"><script>alert(1)</script>'


def test_password_display_attribute_is_quoted(app):
    """Атрибут должен быть в кавычках: без них пробел в значении рвёт разметку."""
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_display(value) }}"
    ).render(value="two words")

    assert _secret_from_display(html) == "two words"


def test_current_secret_row_preserves_secret(app):
    secret = r"nb7\Fyhqa#%z55&g}&3%:"
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.current_secret_row(value) }}"
    ).render(value=secret)

    assert _secret_from_display(html) == secret


def test_password_input_starts_as_text_without_monospace(app):
    """Пустое поле — type=text без monospace, иначе WebView рисует точки поверх placeholder."""
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_input('ssh_password', 'ssh_password', 'Пароль', placeholder='Paste') }}"
    ).render()

    assert 'type="text"' in html
    assert "font-monospace" not in html
    assert "secret-input" in html
    assert 'autocomplete="new-password"' in html


def test_password_input_compact_hides_help_text(app):
    html = app.jinja_env.from_string(
        MACROS + "{{ cred.password_input('p', 'p', 'L', help_text='Hint', compact=True) }}"
    ).render()

    assert 'input-group-sm' in html
    assert 'form-text' not in html
    assert 'title="Hint"' in html


def test_set_badge_and_edit_labels_are_english(app):
    from flask_babel import force_locale, gettext as _

    with force_locale('en'):
        html = app.jinja_env.from_string(
            MACROS + "{{ cred.password_input('p', 'p', 'L', is_set=True) }}"
        ).render()
        assert 'Set' in html
        assert 'задан' not in html.lower()
        assert _('Текущий пароль хостера') == 'Current hoster password'
        assert _('Вставьте новый пароль панели') == 'Paste the new panel password'
        assert _('Куреин М.Н.') == 'Kurein M.N.'


def test_developer_name_latin_for_zh(app):
    from flask_babel import force_locale, gettext as _

    with force_locale('zh'):
        assert _('Куреин М.Н.') == 'Kurein M.N.'


def test_file_picker_uses_app_language_not_os_widget(app):
    from flask_babel import force_locale

    with force_locale('en'):
        html = app.jinja_env.from_string(
            MACROS + "{{ cred.file_picker('server_icon', 'server_icon', compact=True) }}"
        ).render()
    assert 'Select File' in html
    assert 'No file selected' in html
    assert 'js-file-picker-input' in html
    assert 'Выбор файла' not in html
