# Система шифрования SECRET_KEY в VPN Server Manager

> Резервная копия, перенос на другой компьютер и восстановление (серверы + DNS) — пошагово в [BACKUP_RESTORE_ru.md](BACKUP_RESTORE_ru.md).

## 🔐 Назначение ключа

`SECRET_KEY` — симметричный ключ Fernet. Им зашифрованы:

- пароли SSH (основной и root);
- логины и пароли панели управления;
- логины и пароли личного кабинета хостера;
- файл данных целиком — серверы **и** DNS-карточка.

Без ключа файл данных не читается. Восстановления ключа нет.

## 🧅 Два слоя шифрования

Данные шифруются Fernet'ом дважды — это важно понимать при ротации и отладке.

| Слой | Что шифруется | Как выглядит |
|---|---|---|
| 1. Поля | Отдельные пароли и логины внутри JSON | строка-токен `gAAAAA...` |
| 2. Файл | Весь `servers.json.enc` поверх первого слоя | бинарный Fernet-токен |

Поэтому в расшифрованном JSON пароли всё ещё остаются токенами `gAAAAA...` — их расшифровывает второй вызов Fernet.

Реализация: `app/services/data_manager_service.py` (`encrypt_data`, `decrypt_data`, `load_servers`, `save_servers`).

## 📦 Формат файла данных

С версии 4.x внутри зашифрованного файла лежит объект:

```json
{
  "servers": [ ... ],
  "dns": { "domains": [ ... ] }
}
```

Старый формат — просто список серверов `[ ... ]` — по-прежнему читается: `split_payload()` распознаёт оба варианта.

## 🎲 Создание ключа

```bash
python3 tools/generate_key.py
```

Или вручную:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())   # 44 символа base64
```

Ключ Fernet — это **не** токен: он не начинается с `gAAAAA`.

При первом запуске собранного приложения `.env` с новым ключом создаётся автоматически (`app/config.py`), если файла ещё нет.

## 📁 Хранение ключа

Файл `.env`:

```
SECRET_KEY=44-символьный_base64_ключ
```

Расположение зависит от режима:

| Режим | Путь |
|---|---|
| Разработка | `.env` в корне проекта |
| macOS (собранное) | `~/Library/Application Support/VPNServerManager-Clean/.env` |
| Windows (собранное) | `%APPDATA%\VPNServerManager-Clean\.env` |
| Linux (собранное) | `~/.local/share/VPNServerManager-Clean/.env` |

Каталог приложения называется `VPNServerManager-Clean` — именно так, с суффиксом.

## ⚙️ Применение в приложении

Ключ читается в `app/config.py` и отдаётся `DataManagerService`:

```python
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
```

Шифрование и расшифровка поля — `app/services/data_manager_service.py`:

```python
def encrypt_data(self, data: str) -> str:
    if not data:
        return ""
    return self.fernet.encrypt(data.encode()).decode()

def decrypt_data(self, encrypted_data) -> str:
    if encrypted_data.startswith('gAAAAA'):
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except InvalidToken:
            return encrypted_data
    return encrypted_data          # не токен — возвращаем как есть
```

## 👁️ Расшифрованные пароли в памяти

При загрузке `load_servers()` кладёт открытые значения в отдельные поля с суффиксом `_decrypted`:

```
ssh_credentials.password_decrypted
ssh_credentials.root_password_decrypted
panel_credentials.user_decrypted / password_decrypted
hoster_credentials.user_decrypted / password_decrypted
```

Эти поля нужны только для показа в интерфейсе. Перед записью на диск их снимает `_strip_runtime_secrets()`, поэтому **открытые пароли в файл не попадают**. Если вы видите `_decrypted` в расшифрованном дампе — значит дамп снят из памяти, а не из файла.

Все открытые значения проходят `sanitize_secret()` (`app/utils/credentials.py`): убираются CR/LF, zero-width-символы, BOM, soft hyphen и bidi-метки, выполняется нормализация Unicode NFC и обрезка пробелов по краям.

## 🖥️ Передача секрета в интерфейс

Пароль попадает в HTML-атрибут **в base64**, а не в открытом виде:

```html
<span data-password="{{ value | secret_attr }}" data-enc="b64">
```

Фильтр `secret_attr` — это `encode_secret_attr()` из `app/utils/credentials.py`, он регистрируется в `app/__init__.py`. Base64 выбран потому, что WebView декодирует `%`, `&` и `#` в обычных атрибутах и искажает пароль. Обратное преобразование делает `static/js/credentials.js` (`atob` + UTF-8) при `data-enc="b64"`.

Не подставляйте секреты через `|tojson` в атрибут и не вставляйте их в `onclick="...('пароль')"`.

## 🔄 Ротация ключа

Если ключ скомпрометирован (попал в git, в чат, в публичный артефакт), его надо сменить. Простая замена строки в `.env` **уничтожит доступ к данным** — нужен перешифровывающий скрипт:

```bash
python scripts/rotate_secret_key.py --dry-run   # показать план, ничего не менять
python scripts/rotate_secret_key.py             # выполнить ротацию
python scripts/rotate_secret_key.py --data-file data/servers.json.enc
```

Скрипт читает старый ключ из `.env`, расшифровывает оба слоя, генерирует новый ключ, перешифровывает поля и файл, а также делает резервные копии `.env` и файла данных с отметкой времени.

## 🛡️ Безопасность

- Алгоритм: Fernet — AES-128-CBC + HMAC-SHA256, симметричный, с аутентификацией.
- Ключ не хранится в Git; `.env` в `.gitignore`.
- Облачной синхронизации и восстановления ключа нет.

### Потеря ключа

Без ключа данные восстановить **невозможно**. Резервная копия всегда состоит из двух частей: файл `.enc` **и** ключ.

## 🔍 Отладка

Просмотр расшифрованных данных без запуска GUI:

```bash
python3 tools/decrypt_tool.py
```

Проверка, подходит ли ключ к файлу, — `verify_key_for_file()` в `DataManagerService`; тот же путь используется в настройках приложения и показывает количество серверов и доменов DNS в файле.

## ⚠️ PIN — это не SECRET_KEY

PIN блокирует интерфейс, но **ничего не шифрует** и хранится в открытом виде в `config.json`. Подробности — в [DATA_STORAGE_GUIDE_ru.md](DATA_STORAGE_GUIDE_ru.md), раздел про `config.json`. Не путайте эти два механизма: знание PIN не даёт доступа к данным без ключа, и наоборот.
