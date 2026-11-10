"""Подготовленный экспорт секретов, который забирают отдельным GET-запросом.

Окно приложения (WebKit, WebView2) сохраняет файл так: получает ответ, видит вложение и
запрашивает тот же адрес ещё раз обычным GET. Экспорт секретов принимает только POST с
подтверждением и защитным токеном, поэтому повторный GET получал «405 Method Not Allowed»,
и именно эта страница сохранялась под именем файла. Теперь POST проверяет всё, что должен,
кладёт готовые байты сюда и перенаправляет на адрес со случайным одноразовым именем.

Байты живут только в памяти и недолго; на диск ничего не пишется. Забрать их может только
та же сессия, которая их подготовила. Несколько GET подряд допустимы: окно приложения может
сделать запрос дважды.
"""
import hmac
import secrets
import threading
import time

TTL_SECONDS = 120
MAX_PENDING = 4
_lock = threading.Lock()
_pending = {}


def _purge(now):
    for token in [token for token, item in _pending.items() if item['expires'] <= now]:
        del _pending[token]


def put(raw, filename, mimetype, owner):
    """Сохранить байты на TTL_SECONDS и вернуть случайный токен для адреса загрузки."""
    token = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _lock:
        _purge(now)
        while len(_pending) >= MAX_PENDING:
            del _pending[min(_pending, key=lambda key: _pending[key]['expires'])]
        _pending[token] = {'raw': raw, 'filename': filename, 'mimetype': mimetype,
                           'owner': owner, 'expires': now + TTL_SECONDS}
    return token


def get(token, owner):
    """Запись для этого токена и этой сессии, либо None."""
    with _lock:
        _purge(time.monotonic())
        item = _pending.get(token)
        if item is None or not owner or not hmac.compare_digest(item['owner'], owner):
            return None
        return item


def clear():
    with _lock:
        _pending.clear()
