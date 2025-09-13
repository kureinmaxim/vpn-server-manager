# Руководство по сборке и релизу VPN Server Manager

Данное руководство описывает полный процесс сборки приложения VPN Server Manager, создания тега и публикации релиза на GitHub.

## Содержание

1. [Подготовка к сборке](#1-подготовка-к-сборке)
2. [Обновление версии](#2-обновление-версии)
3. [Сборка приложения](#3-сборка-приложения)
4. [Тестирование сборки](#4-тестирование-сборки)
5. [Создание тега в Git](#5-создание-тега-в-git)
6. [Создание релиза на GitHub](#6-создание-релиза-на-github)
7. [Решение проблем](#7-решение-проблем)

## 1. Подготовка к сборке

### 1.1. Требования

- macOS 10.14 или выше
- Python 3.8 или выше
- Установленный pip
- PyInstaller (`pip install pyinstaller`)
- Xcode Command Line Tools
- Git и GitHub CLI (опционально)

### 1.2. Клонирование репозитория

```bash
# Клонирование репозитория
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager

# Создание и активация виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install pyinstaller
```

### 1.3. Установка GitHub CLI (опционально)

Если у вас еще не установлен GitHub CLI:

```bash
# Для macOS с Homebrew
brew install gh

# Авторизация
gh auth login
```

## 2. Обновление версии

### 2.1. Изменение версии в config.json

Откройте файл `config.json` и обновите версию в разделе `app_info`:

```json
{
  "app_info": {
    "version": "3.6.8",  // Увеличьте номер версии
    "release_date": "ДД.ММ.ГГГГ",  // Обновите дату
    "developer": "Developer",
    "last_updated": "ГГГГ-ММ-ДД"  // Обновите дату
  }
}
```

### 2.2. Обновление CHANGELOG.md

Добавьте информацию о новом релизе в начало файла `CHANGELOG.md`:

```markdown
## [3.6.8] - ГГГГ-ММ-ДД

### Добавлено
- Новая функциональность 1
- Новая функциональность 2

### Изменено
- Изменение 1
- Изменение 2

### Исправлено
- Исправление ошибки 1
- Исправление ошибки 2
```

## 3. Сборка приложения

### 3.1. Запуск скрипта сборки

```bash
# Активация виртуального окружения (если еще не активировано)
source venv/bin/activate

# Запуск скрипта сборки
python3 build_macos.py
```

Скрипт выполнит следующие действия:
1. Очистит предыдущие сборки
2. Создаст `.app` бандл
3. Создаст `.dmg` установочный образ
4. Выполнит диагностику приложения

### 3.2. Результаты сборки

После успешной сборки вы найдете:
- `.app` файл в директории `dist/VPNServerManager-Clean.app`
- `.dmg` файл в директории `dist/VPNServerManager-Clean_Installer.dmg`

## 4. Тестирование сборки

### 4.1. Проверка приложения

1. Откройте `.app` файл двойным щелчком
2. Проверьте основные функции:
   - Вход с PIN-кодом
   - Добавление/редактирование/удаление серверов
   - Работа в офлайн режиме
   - Экспорт/импорт данных
   - Проверка подсказок и шпаргалок

### 4.2. Проверка установочного образа

1. Смонтируйте `.dmg` файл двойным щелчком
2. Проверьте интерфейс установки
3. Перетащите приложение в папку Applications
4. Запустите установленное приложение и проверьте его работу

## 5. Создание тега в Git

### 5.1. Коммит изменений

```bash
# Добавление всех изменений
git add config.json CHANGELOG.md

# Создание коммита
git commit -m "Релиз версии 3.6.8"

# Отправка изменений на GitHub
git push origin main
```

### 5.2. Создание тега

```bash
# Создание аннотированного тега
git tag -a v3.6.8 -m "Версия 3.6.8"

# Отправка тега на GitHub
git push origin v3.6.8
```

## 6. Создание релиза на GitHub

### 6.1. Через веб-интерфейс GitHub

1. Перейдите на страницу репозитория на GitHub
2. Нажмите на "Releases" в правой части страницы
3. Нажмите "Draft a new release"
4. Выберите созданный тег (v3.6.8)
5. Заполните заголовок (например, "VPN Server Manager v3.6.8")
6. Добавьте описание релиза (можно скопировать из CHANGELOG.md)
7. Загрузите `.dmg` файл как артефакт релиза
8. Нажмите "Publish release"

### 6.2. Через GitHub CLI

```bash
# Создание релиза с загрузкой DMG-файла
gh release create v3.6.8 \
  --title "VPN Server Manager v3.6.8" \
  --notes "## Версия 3.6.8

### Добавлено
- Новая функциональность 1
- Новая функциональность 2

### Изменено
- Изменение 1
- Изменение 2

### Исправлено
- Исправление ошибки 1
- Исправление ошибки 2" \
  dist/VPNServerManager-Clean_Installer.dmg
```

### 6.3. Проверка релиза

1. Перейдите на страницу "Releases" на GitHub
2. Убедитесь, что новый релиз отображается и помечен как "Latest"
3. Проверьте, что артефакты релиза доступны для скачивания

## 7. Решение проблем

### 7.1. Ошибки сборки

- **Проблема**: Ошибка "ImportError" при запуске приложения
  - **Решение**: Добавьте отсутствующий модуль в список `hidden_imports` в `build_macos.py`

- **Проблема**: Отсутствие иконки в собранном приложении
  - **Решение**: Убедитесь, что файл `icon_clean.png` или `icon_clean.ico` существует в папке `static/images/`

### 7.2. Ошибки с тегами Git

- **Проблема**: "fatal: tag 'vX.X.X' already exists"
  - **Решение**: Используйте другой номер версии или удалите существующий тег:
    ```bash
    git tag -d vX.X.X
    git push origin :refs/tags/vX.X.X
    ```

### 7.3. Ошибки с релизами GitHub

- **Проблема**: Релиз создан, но не отображается как "Latest"
  - **Решение**: Убедитесь, что релиз не помечен как "Pre-release" и имеет более новую версию, чем предыдущий релиз

- **Проблема**: Ошибка при загрузке артефактов
  - **Решение**: Проверьте размер файла (GitHub имеет ограничения) или загрузите через веб-интерфейс

---

## 8. Практический пример публикации (v3.6.8)

Ниже приведены команды, использованные для публикации релиза 3.6.8: пуш изменений, создание тега, релиза на GitHub и добавление SHA256-суммы для DMG.

### 8.1. Предварительные условия

```bash
# Активируйте виртуальное окружение (если потребуется сборка)
source venv/bin/activate

# Убедитесь, что установлен и настроен GitHub CLI
gh --version
gh auth status
```

### 8.2. Сборка приложения (macOS)

```bash
python3 build_macos.py
```

Результаты:
- .app: dist/VPNServerManager-Clean.app
- .dmg: dist/VPNServerManager-Clean_Installer.dmg

### 8.3. Публикация изменений в репозиторий

```bash
# Проверка статуса и удалённого репозитория
git status
git remote -v

# Публикация коммитов в main
git push origin main
```

### 8.4. Создание и публикация тега v3.6.8

```bash
# Создание аннотированного тега
git tag -a v3.6.8 -m "Release 3.6.8: dynamic port via make_server, unique session cookie, project-level config precedence, macOS build updated"

# Публикация тега
git push origin v3.6.8
```

### 8.5. Создание релиза на GitHub с загрузкой DMG

```bash
# Создание релиза для тега v3.6.8 и загрузка DMG
gh release create v3.6.8 \
  --repo kureinmaxim/vpn-server-manager \
  --title "VPN Server Manager 3.6.8" \
  --notes "- Новое: надёжный запуск Flask на свободном порте через make_server (host 127.0.0.1)\n- Уникальная cookie-сессия: vps_manager_session_vpn — исключает пересечение сессий с другим .app\n- Приоритет проектного config.json над пользовательским (для корректного отображения версии/разработчика)\n- Обновлена сборка macOS (.app и DMG)" \
  dist/VPNServerManager-Clean_Installer.dmg
```

### 8.6. Подсчёт SHA256 для DMG и добавление в релиз

```bash
# Подсчёт хэш-суммы
HASH=$(shasum -a 256 "dist/VPNServerManager-Clean_Installer.dmg" | awk '{print $1}'); echo "SHA256: $HASH"
```

Пример результата для 3.6.8:

```text
SHA256: b57abf517b112ed7956126c5fc3b5c48eeb457f5c48056fbe491ad0b976fb9ba
```

Обновление заметок релиза и пометка как Latest:

```bash
gh release edit v3.6.8 \
  --repo kureinmaxim/vpn-server-manager \
  --latest \
  --notes "- Новое: надёжный запуск Flask на свободном порте через make_server (host 127.0.0.1)\n- Уникальная cookie-сессия: vps_manager_session_vpn — исключает пересечение сессий с другим .app\n- Приоритет проектного config.json над пользовательским (для корректного отображения версии/разработчика)\n- Обновлена сборка macOS (.app и DMG)\n\nSHA256(DMG): b57abf517b112ed7956126c5fc3b5c48eeb457f5c48056fbe491ad0b976fb9ba"
```

### 8.7. Обновление README (опционально)

Добавьте раздел со ссылками на последний релиз и прямую ссылку на DMG, а также SHA256-сумму. Пример:

```markdown
## ⬇️ Скачать

- Последний релиз: [Latest Release](https://github.com/kureinmaxim/vpn-server-manager/releases/latest)
- Прямая ссылка (v3.6.8, macOS DMG): [VPNServerManager-Clean_Installer.dmg](https://github.com/kureinmaxim/vpn-server-manager/releases/download/v3.6.8/VPNServerManager-Clean_Installer.dmg)
- SHA256(DMG): `b57abf517b112ed7956126c5fc3b5c48eeb457f5c48056fbe491ad0b976fb9ba`
```

Команды для коммита изменений README:

```bash
git add README.md
git commit -m "docs: add download section with latest release link and DMG SHA256 (v3.6.8)"
git push origin main
```

### 8.8. Верификация релиза

```bash
# Быстрый просмотр в браузере
gh release view v3.6.8 --web
```

После выполнения этих шагов релиз будет доступен на странице релизов и помечен как Latest, а DMG-файл — с опубликованной контрольной суммой.

---

## Дополнительные ресурсы

- [Документация PyInstaller](https://pyinstaller.org/en/stable/)
- [Документация GitHub CLI](https://cli.github.com/manual/)
- [Semantic Versioning](https://semver.org/lang/ru/)
- [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/)

Для получения дополнительной информации о сборке приложения, смотрите файл `docs/project_info/BUILD.md`.
