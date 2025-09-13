# PROMPT ДЛЯ CURSOR — VPNserverManage: независимый порт и cookie

Цель: разрешить одновременный запуск двух .app (VPNserverManage и другое приложение) без конфликтов портов и сессий.

- Проект-цель: `/Users/olgazaharova/Project/ProjectPython/VPNserverManage`
- Файлы: правки только в `app.py`
- Хост: строго `127.0.0.1`

## Что нужно сделать (выполни в этом порядке)

1) Импорты
- Убедись, что вверху `app.py` есть:
```python
import os
import signal
import threading
import requests
from werkzeug.serving import make_server
```
- Если чего-то нет — добавь рядом с существующими импортами.

2) Уникальная cookie-сессия
- Сразу после создания приложения Flask добавь строку (или замени на неё):
```python
app.config['SESSION_COOKIE_NAME'] = 'vps_manager_session_vpn'
```

3) Маршрут выключения (если отсутствует)
```python
@app.route('/shutdown')
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return 'Сервер выключается...'
```

4) Надёжный запуск на свободном порте (без конфликтов)
- Вставь БЛОК НИЖЕ перед `if __name__ == "__main__":` (или рядом с другими утилитами запуска):
```python
# --- Надёжный запуск сервера на свободном порте (без конфликтов) ---
from werkzeug.serving import make_server

SERVER_PORT = None
_WSGI_SERVER = None

def _start_flask_server():
    global SERVER_PORT, _WSGI_SERVER
    try:
        # Порт 0 — ОС выдаст гарантированно свободный порт
        _WSGI_SERVER = make_server('127.0.0.1', 0, app)
        SERVER_PORT = _WSGI_SERVER.server_port
        print(f"🚀 Flask сервер запущен на http://127.0.0.1:{SERVER_PORT}")
        _WSGI_SERVER.serve_forever()
    except Exception as e:
        print(f"❌ Ошибка запуска Flask сервера: {e}")
        import traceback
        traceback.print_exc()
```

5) Главный блок запуска (перевести на make_server)
- В блоке `if __name__ == "__main__":`:
  - Заменить запуск Flask (в т.ч. любые `app.run(...)` или обёртки) на потоковый запуск `_start_flask_server`:
```python
print("🔄 Запуск Flask в отдельном потоке...")
flask_thread = threading.Thread(target=_start_flask_server)
flask_thread.daemon = True
flask_thread.start()

# Ждём, пока сервер поднимется и задаст порт
import time
for _ in range(100):
    if SERVER_PORT:
        break
    time.sleep(0.05)
```
  - Обновить обработчик закрытия окна, чтобы он бил по актуальному порту:
```python
def on_closing():
    print("Окно закрывается, отправка запроса на выключение...")
    try:
        requests.get(f'http://127.0.0.1:{SERVER_PORT}/shutdown', timeout=1)
    except requests.exceptions.RequestException:
        pass
```
  - При создании окна PyWebView явно подставить выбранный порт:
```python
window = webview.create_window(
    'VPS Manager',
    f'http://127.0.0.1:{SERVER_PORT or 5050}',
    width=1280,
    height=800,
    resizable=True
)
```

6) Проверка
- Убедись, что нигде не остались хардкоды вида `http://127.0.0.1:5050` для старта окна или выключения — везде должен использоваться `SERVER_PORT`.
- Хост всегда `127.0.0.1` (не `0.0.0.0`).

7) Сборка (если нужна новая .app)
- macOS (из корня проекта `VPNserverManage`):
```bash
source venv/bin/activate && python3 build_macos.py
```

Ожидаемый результат: `VPNserverManage` стартует на автоматически выделенном свободном порте и имеет уникальную cookie-сессию `vps_manager_session_vpn`; одновременно запущенное другое .app больше не перебивает интерфейс.

## Синхронизация версии и имени разработчика (macOS)

GUI берет версию/разработчика из пользовательского конфига: `~/Library/Application Support/VPNServerManager/config.json`. Этот файл перекрывает `config.json` из проекта/бандла. Если в футере показывается не та версия или стоит `Developer`, синхронизируй так:

1) Проверка текущего пользовательского конфига
```bash
cat "$HOME/Library/Application Support/VPNServerManager/config.json" | cat
```

2) Обновление версии и разработчика (пример для 3.5.3 и «Куреин М.Н.»)
```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser('~/Library/Application Support/VPNServerManager/config.json')
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)
d.setdefault('app_info', {})
d['app_info']['version'] = '3.5.3'
d['app_info']['developer'] = 'Куреин М.Н.'
with open(p, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print('✅ Обновлено:', p)
PY
```

3) Опционально синхронизируй даты:
```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser('~/Library/Application Support/VPNServerManager/config.json')
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)
d.setdefault('app_info', {})
d['app_info']['release_date'] = '13.09.2025'
d['app_info']['last_updated'] = '2025-08-03'
with open(p, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print('✅ Даты синхронизированы:', p)
PY
```

После обновления перезапусти приложение. Футер должен показывать актуальные значения.
