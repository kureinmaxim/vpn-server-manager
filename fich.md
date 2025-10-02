# Задача: Добавить карточкам сервера модалку «Статус» с SSH‑метриками (Windows 11)

Контекст
- Приложение: Flask + Jinja2 (локальный GUI через браузер/PyWebView).
- Python 3.11+ (желательно 3.13).
- ОС: Windows 11.
- Данные серверов уже хранятся (IP, SSH логин/пароль/порт, флаг root login).
- UI — Bootstrap 5.

Цель
- В карточке сервера добавить кнопку “Статус”, открывающую модалку с метриками, читаемыми по SSH:
  - CPU (%), ядра (кол-во), версия ядра.
  - Память и swap.
  - Load average.
  - Диски (df -h) и Inodes (df -i).
  - Сеть: список интерфейсов с IP + RX/TX в чипах для каждого интерфейса.
  - Docker: подробности при наличии — версия, количество running, краткий список имён; таблица контейнеров (name, image, status, ports, size).
  - Автообновление каждые 10 секунд, корректная остановка таймера при закрытии модалки.
  - Мягкие фолбэки: если отсутствуют утилиты (top/free/ip/ifconfig/df/ps), показать предупреждение и команду установки пакетов, исходя из дистрибутива (apt/dnf/yum/apk/pacman/zypper/opkg).

Обязательные требования
- Бэкенд:
  - Использовать Paramiko для SSH (на Windows — устанавливается в venv: `pip install paramiko`).
  - Подключение с явными флагами: `allow_agent=False, look_for_keys=False`.
  - Таймауты 8–10 сек (настраиваемые из запроса).
  - Вынести в отдельные функции:
    - `_ssh_run(ssh, cmd, timeout=8) -> str`
    - `_collect_stats_via_ssh(host, user, password, port=22, timeout=8) -> dict` (возвращает структуру `stats`, см. «Схема данных» ниже).
  - Новый роут: `GET /server/<int:id>/stats?timeout=10` (опциональный `timeout` 3..30 c), возвращает JSON `{ ok, server_id, stats }` или `{ error, exception }`.
  - Разместить роут и helper‑функции ДО первого запроса (до запуска сервера/WSGI) — чтобы избежать ошибки Flask: “setup method 'route' can no longer be called...”.
  - Проверить что хранение и расшифровка паролей совместимы (если используются Fernet).

- Фронтенд:
  - В карточке сервера (список) добавить кнопку «Статус», открывающую модалку.
  - JS без синтаксиса ES2020 (без optional chaining `?.` и `??`), чтобы избежать ошибок парсера (особенно в WebView).
  - В модалке:
    - Первый рендер — сразу после открытия.
    - Автообновление: `setInterval(fetchAndRender, 10000)`, остановка в `hidden.bs.modal`. Авто‑стоп после N (по умолчанию 3) подряд ошибок.
    - RX/TX показывать бейджами (badge) справа от интерфейса; пояснение: «RX — принято, TX — отправлено (обновление каждые 10 с)».
    - Uptime выводить по‑английски (например, `6 months, 18 days`).
    - В заголовке «Сети» показывать Docker: `есть/нет`, `running: N`, первые контейнеры вида `name:size` (до 2, далее `+K`), в tooltip — версия Docker.
    - Ниже сетей — таблица контейнеров (Name, Image, Status, Ports, Size).
    - В Inodes длинные точки монтирования сокращать до 15 символов с tooltip полного пути.
    - Начальное состояние модалки — спиннер «Загрузка…».
    - Кнопка «Статус» — без инлайнового JS; делегирование клика по `.btn-show-stats`.
    - Предупреждение о недостающих утилитах (желтый alert) и команда установки (с кнопкой «копировать»).
  - Не использовать встраивание backticks внутри backticks (избежать конфликтов темплейтов).

Схема данных (response.stats)
```json
{
  "uptime": "string",
  "load": { "1m": "string", "5m": "string", "15m": "string" },
  "cpu": { "used_pct": number, "cores": number, "kernel": "string" },
  "mem": { "total_mb": number, "used_mb": number, "avail_mb": number, "used_pct": number },
  "swap": { "total_mb": number, "used_mb": number, "used_pct": number },
  "disks": [ { "mount": "string", "size": "string", "used": "string", "avail": "string", "pcent": "string" } ],
  "inodes": [ { "mount": "string", "inodes": "string", "iused": "string", "ipcent": "string" } ],
  "processes": [ { "pid": "string", "cmd": "string", "cpu": "string", "mem": "string" } ],
  "net": [ { "iface": "string", "addr": "string" } ],
  "traffic": [ { "iface": "string", "rx_bytes": number, "tx_bytes": number } ],
  "docker": {
    "present": boolean,
    "running": number,
    "version": "string",
    "names": ["string"],
    "containers": [
      { "name": "string", "image": "string", "status": "string", "ports": "string", "size": "string", "mounts": "string" }
    ]
  },
  "missing_tools": [ "top", "free", "df", "ps", "ip", "ifconfig" ],
  "install_hint": "string (команда установки для дистрибутива)"
}
```

Определение утилит/дистрибутива
- Проверять наличие `busybox/toybox`.
- Команда для недостающих утилит — по `ID` и `ID_LIKE` из `/etc/os-release`; fallback — по найденному пакетному менеджеру (apt/dnf/yum/apk/pacman/zypper/opkg).
- Для сетевого RX/TX: читать `/sys/class/net/<iface>/statistics/rx_bytes` и `tx_bytes`.

UI/UX
- CPU и память — с прогресс-барами.
- RX/TX как чипы (Bootstrap badge) справа от интерфейса.
- Docker: короткая подпись в заголовке блока «Сети» (present/running).
- Внизу — кнопка «Закрыть».

Безопасность/стабильность
- Не логировать чувствительные данные.
- Таймауты SSH; перехватывать `AuthenticationException`, `SSHException`.
- Возвращать `{ error, exception }` в JSON, чтобы фронтенд показывал понятную ошибку.

Тесты/проверки
- Сервер с корректным паролем — все метрики в норме.
- Сервер с отсутствующими утилитами — warning + команда установки.
- Сервер без Docker — `present=false`, `running=0`.
- Отсутствие optional chaining/?? в JS.
- Автообновление — раз в 10 сек; при закрытии модалки интервал очищается.

Deliverables
1) Изменённый backend (Flask): helpers + маршрут `/server/<id>/stats`.
2) Изменённый шаблон списка серверов (кнопка «Статус»).
3) Изменённый JS в шаблоне: модалка, `fetchAndRender()` + интервал 10 сек, RX/TX чипы.
4) `requirements.txt` обновлён (`paramiko`).
5) Короткая инструкция запуска в Windows:
   - Создать и активировать venv (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - Запуск:
     ```powershell
     python app.py
     ```
   - Проверка: открыть UI, нажать «Статус» в карточке.

Проверка готовности (acceptance)
- Нажатие «Статус» -> мгновенный рендер «Загрузка…», затем метрики.
- RX/TX бейджи рядом с каждым интерфейсом.
- Таймер 10 сек явно работает (видно обновление чисел).
- Закрытие модалки — таймер очищается.
- Нет ошибок в консоли WebView/браузера; нет `Property assignment expected`.

---

Новые фичи
- Docker: совместимая и надёжная загрузка таблицы контейнеров
  - Основной парсинг: `docker ps --format '{{json .}}'` (поля Names, Image, Status, Ports, Size).
  - Фолбэки: строковый формат, `docker ps -a --filter name=...`, `docker inspect` по каждому имени, и последний резерв — синтетическая строка по имени, чтобы таблица не пустовала.
  - Теперь в таблице заполняются колонки Name, Image, Status, Ports, Size; в заголовке «Сети» — версия Docker, число running и первые имена.
- Inodes: устойчивый разбор через `df -i --output`, с фолбэком на POSIX `df -iP` для старых систем.
- Улучшения UX модалки «Статус»
  - Заголовок показывает имя сервера и IP, индикатор «последнее обновление», мини‑спиннер во время загрузки.
  - Цветовые пороги для прогресс‑баров CPU/MEM.
  - Для предупреждения о недостающих утилитах — кнопка «Скопировать команду».
- Сохранение снимка вкладки «Статус» как PNG
  - Локальный роут `/vendor/html2canvas.min.js` кэширует библиотеку для работы без CDN.
  - Новый API `POST /snapshot/save` принимает data URL PNG и сохраняет файл в папку Downloads (возвращает имя файла).
  - На фронтенде при нажатии «Сохранить как PNG» снимок отправляется на сервер; при ошибке — фолбэк на клиентскую загрузку.