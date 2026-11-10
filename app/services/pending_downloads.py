"""Подготовленный экспорт секретов, который забирают отдельным GET-запросом по одноразовому адресу.

Окно приложения на macOS (pywebview + WKWebView) сохраняет файл в два запроса: сначала сама
страница получает ответ с заголовком вложения, затем pywebview отменяет переход и скачивает
тот же адрес заново через общий NSURLSession. У второго запроса нет cookie сессии окна, поэтому
любая загрузка «только для вошедших» превращалась в экран входа, сохранённый под именем файла
(а раньше, пока экспорт принимал только POST, — в страницу «405 Method Not Allowed»).

Поэтому доступ к загрузке даёт сам адрес, а не сессия. Экспорт секретов по-прежнему принимает
только POST от вошедшего пользователя с подтверждением и защитным токеном; готовые байты
кладутся сюда, а в ответ уходит адрес со случайным токеном:

- токен — 256 бит из secrets, угадать его нельзя;
- живёт TTL_SECONDS, после этого запись удаляется;
- отдаётся не больше MAX_FETCHES раз (запрос окна, запрос системной загрузки и один запас),
  затем запись удаляется сразу;
- байты хранятся только в памяти, на диск ничего не пишется;
- сервер слушает только 127.0.0.1, посторонний Host отклоняется.
"""
import secrets
import threading
import time

TTL_SECONDS = 60
MAX_FETCHES = 3
MAX_PENDING = 4
_lock = threading.Lock()
_pending = {}


def _purge(now):
    for token in [token for token, item in _pending.items() if item['expires'] <= now]:
        del _pending[token]


def put(raw, filename, mimetype):
    """Сохранить байты на TTL_SECONDS и вернуть случайный токен для адреса загрузки."""
    token = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _lock:
        _purge(now)
        while len(_pending) >= MAX_PENDING:
            del _pending[min(_pending, key=lambda key: _pending[key]['expires'])]
        _pending[token] = {'raw': raw, 'filename': filename, 'mimetype': mimetype,
                           'expires': now + TTL_SECONDS, 'left': MAX_FETCHES}
    return token


def take(token):
    """Запись по токену или None. Каждый вызов расходует одну из MAX_FETCHES попыток."""
    with _lock:
        _purge(time.monotonic())
        item = _pending.get(token)
        if item is None:
            return None
        item['left'] -= 1
        if item['left'] <= 0:
            del _pending[token]
        return item


def clear():
    with _lock:
        _pending.clear()
