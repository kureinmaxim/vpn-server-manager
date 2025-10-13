# VPN Server Manager v4.0.6

Современное приложение для управления VPN-серверами с модульной архитектурой, шифрованием данных и поддержкой офлайн режима.

![VPN Server Manager](static/VPSc.png)

## 🆕 Последние обновления

### v4.0.6 (13 октября 2025)
- 🔒 **КРИТИЧЕСКОЕ обновление безопасности**: Удалены конфиденциальные файлы из Git истории
- 🔐 **SECRET_KEY**: Сгенерирован новый ключ шифрования (старый был скомпрометирован)
- 📝 **config.json**: Теперь локальный файл, не хранится в Git
- 🛡️ **Документация по безопасности**: Добавлены SECURITY.md, SECURITY_AUDIT_REPORT.md, URGENT_ACTIONS.md
- ⚙️ **build_macos.py**: Исправлен - больше не включает .env и config.json в DMG
- 📋 **Шаблоны**: Созданы config.json.example и обновлен env.example

### v4.0.5 (12 октября 2025)
- 🐛 **Функция "Сохранить как PNG"**: Полностью реализована функция сохранения статистики сервера в PNG-файл в папку Downloads
- 🔐 **PIN аутентификация**: Исправлено отображение ошибки при неправильном PIN - теперь показывается текст "Неверный PIN-код"
- 🌐 **SSH подключение**: Добавлена поддержка нестандартных SSH портов (например, 2222)
- 🌍 **Переводы**: Добавлены и скомпилированы новые строки перевода для английского и китайского языков
- 📝 **Опечатки**: Исправлена опечатка "Выберать" → "Выберите" в форме импорта данных

### v4.0.4 (12 октября 2025)
- 🪟 **Поддержка Windows**: Добавлены автоматические скрипты установки и запуска для Windows (`setup_windows.bat`, `start_windows.bat`).
- 📖 **Документация для Windows**: Создано подробное руководство [README_WINDOWS.md](README_WINDOWS.md) с пошаговыми инструкциями.
- 🔧 **Исправлен generate_key.py**: Теперь сохраняет все настройки из `env.example` при генерации ключа шифрования.
- 📝 **Улучшенная документация**: Обновлены инструкции по установке с разделением команд для macOS/Linux и Windows.
- 🎯 **Единая версия**: Синхронизация версии приложения во всех компонентах из `config.json`.
- 🔄 **Git конфигурация**: Добавлен `.gitattributes` для корректной работы с line endings на разных платформах.

### v4.0.3 (12 октября 2025)
- 📦 **Исправлена сборка для macOS**: Приложение (`.app`) теперь запускается корректно с правильной версией и путями к данным.
- 💡 **Умная конфигурация**: При первом запуске решена проблема "Error loading servers" - приложение предлагает импортировать файл данных.
- 🎯 **Единая версия**: Все компоненты приложения теперь используют единую версию из `config.json`.
- 🚪 **Система выхода**: Полностью рабочий механизм выхода и закрытия desktop приложения.
- 🔐 **Управление сессиями**: Исправлена проблема с постоянными сессиями - PIN требуется при каждом запуске.
- 🎨 **UI/UX улучшения**: Увеличенное окно (880px), исправлена видимость в светлой теме, информация о сервере в футере.
- 🌐 **Локализация**: Добавлены недостающие переводы, локализованные диалоги выхода и закрытия.
- 🔧 **Исправления**: Страница "Управление подсказками" теперь работает корректно.

### v4.0.2 (12 октября 2025)
- 🚀 **Multi-App Support**: Добавлена возможность параллельного запуска нескольких экземпляров приложения без конфликтов портов и сессий.
- ⚡ **Graceful Shutdown**: Реализовано корректное завершение работы сервера.

### v4.0.1 (11 октября 2025)
- 🔐 **Исправлена критическая ошибка входа по PIN**: JavaScript в `layout.html` теперь отправляет данные в правильном формате JSON
- ✅ **PIN-аутентификация работает корректно** во всех шаблонах
- 📚 **Обновлена документация**: Добавлен [индекс документации](docs/INDEX.md) и технические отчеты
- Подробнее: [PIN_AUTHENTICATION_FIX.md](PIN_AUTHENTICATION_FIX.md)

## ⬇️ Скачать

- Последний релиз: [Latest Release](https://github.com/kureinmaxim/vpn-server-manager/releases/latest)
- ⚠️ **ВАЖНО**: Релиз v4.0.5 был удален по соображениям безопасности
- Новый релиз v4.0.6 будет доступен после пересборки с исправлениями безопасности

## 🚀 Возможности v4.0

### 🏗️ Новая архитектура
- **Модульная структура**: Application Factory Pattern, Service Layer, Blueprint Architecture
- **Dependency Injection**: Реестр сервисов для управления зависимостями
- **Custom Exceptions**: Централизованная обработка ошибок
- **Structured Logging**: Настроенное логирование с ротацией файлов
- **Comprehensive Testing**: Unit и integration тесты с покрытием кода

### 🔧 Функциональность
- Хранение данных о VPN-серверах в зашифрованном виде
- Удобный веб-интерфейс на Flask с PyWebView
- Поддержка офлайн режима работы
- Многоязычный интерфейс (русский, английский, китайский)
- Система подсказок и шпаргалок
- Экспорт/импорт данных с шифрованием
- Защита PIN-кодом
- **🌐 IP-анализ**: Интеграция с IP2Location для определения владельца IP-адресов
- **📚 Шпаргалка**: Комплексная шпаргалка с командами NGINX, Docker, Systemd и содержанием

### 🛠️ Инструменты разработки
- **Docker Support**: Контейнеризация с Dockerfile и docker-compose.yml
- **Development Tools**: Makefile, pytest.ini, инструменты качества кода
- **Security Enhancements**: Валидация данных, декораторы безопасности, CSRF защита
- **Modern Python**: Type hints, dataclasses, современные практики разработки

## 📋 Документация

- 📚 **[Индекс документации](docs/INDEX.md)** - Полный каталог всей документации проекта
- 🪟 **[Руководство для Windows](README_WINDOWS.md)** - Подробная инструкция для пользователей Windows

### Основная документация

- [Новая архитектура v4.0.1](README_NEW_STRUCTURE.md) - Подробное описание новой структуры
- [Отчет о реструктуризации](RESTRUCTURING_REPORT.md) - Полный отчет о изменениях
- [Руководство по миграции](MIGRATION_GUIDE.md) - Как перейти на новую версию
- [Docker руководство](DOCKER_GUIDE.md) - Полное руководство по работе с Docker
- [Git и GitHub руководство](GIT_GITHUB_GUIDE.md) - Работа с Git, .gitignore и публикация на GitHub
- [Git шпаргалка](GIT_CHEATSHEET.md) - Быстрая шпаргалка по Git командам
- [Структура проекта](docs/project_info/PROJECT_STRUCTURE.md)
- [Инструкция по сборке](docs/project_info/BUILD.md)

### 🔧 Технические отчеты и исправления

- [PIN Authentication Fix](PIN_AUTHENTICATION_FIX.md) - ✅ Исправление проблемы входа по PIN (11 октября 2025)
- [Port Solution Report](PORT_SOLUTION_REPORT.md) - Решение проблем с портами
- [Testing Report](TESTING_REPORT_CHROME_MCP.md) - Отчет о тестировании с Chrome DevTools
- [Руководство по сборке и релизу](docs/release_guide.md)
- [Инструменты резервного копирования](docs/project_info/BACKUP_TOOLS.md)
- [Управление ключами шифрования](docs/project_info/SECRET_KEY.md)

### Учебные материалы

- [Уроки по GitHub](docs/lessons/github_tutorials/)
- [Документация GitHub](docs/lessons/github_docs/)
- [Локализация (i18n)](docs/lessons/i18n/)
- [GitHub Actions](docs/lessons/github-actions/)

## 🛠 Установка

### Требования

- Python 3.8 или выше
- Установленный pip
- Виртуальное окружение Python (рекомендуется)

### Быстрая установка (Windows)

Для пользователей Windows доступны готовые скрипты:

```cmd
# Автоматическая установка (создание venv, установка зависимостей, генерация ключа)
setup_windows.bat

# Запуск приложения
start_windows.bat
```

### Ручная установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/kureinmaxim/vpn-server-manager.git
   cd vpn-server-manager
   ```

2. Создайте и активируйте виртуальное окружение:

   **macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   
   **Windows (CMD):**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
   
   **Windows (PowerShell):**
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   
   # Если возникает ошибка "execution policy":
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. Установите зависимости:

   **macOS/Linux:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Windows:**
   ```cmd
   pip install -r requirements.txt
   ```

4. Сгенерируйте ключ шифрования и создайте .env файл:

   **macOS/Linux:**
   ```bash
   python3 generate_key.py
   ```
   
   **Windows:**
   ```cmd
   python generate_key.py
   ```
   
   Скрипт автоматически:
   - Скопирует `env.example` в `.env` (если `.env` не существует)
   - Сгенерирует и установит безопасный `SECRET_KEY`
   - Сохранит все остальные настройки из `env.example`

5. (Опционально) Настройте дополнительные параметры в `.env`:

   **macOS/Linux:**
   ```bash
   nano .env
   # или
   vim .env
   ```
   
   **Windows:**
   ```cmd
   notepad .env
   ```

6. Запустите приложение:

   **macOS/Linux:**
   ```bash
   # Web режим
   python3 run.py
   
   # Desktop режим
   python3 run.py --desktop
   
   # Debug режим
   python3 run.py --debug
   ```
   
   **Windows:**
   ```cmd
   # Web режим
   python run.py
   
   # Desktop режим
   python run.py --desktop
   
   # Debug режим
   python run.py --debug
   ```

### 🐳 Docker

```bash
# Сборка образа
docker build -t vpn-manager-clean .

# Запуск
docker run -p 5000:5000 vpn-manager-clean

# Или с docker-compose
docker-compose up
```

**📖 Подробное руководство**: [DOCKER_GUIDE.md](DOCKER_GUIDE.md) - Полное руководство по работе с Docker

### 🛠️ Разработка

```bash
# Установка зависимостей для разработки
make install-dev

# Запуск тестов
make test

# Проверка качества кода
make lint

# Форматирование кода
make format

# Все проверки
make all
```

### 🔧 Git команды

```bash
# Клонирование репозитория
git clone https://github.com/username/vpn-server-manager.git
cd vpn-server-manager

# Первоначальная настройка
git config user.name "Ваше Имя"
git config user.email "your.email@example.com"

# Создание .env файла
cp env.example .env

# Первый коммит
git add .
git commit -m "feat: initial commit v4.0.0"

# Публикация на GitHub
git remote add origin https://github.com/username/vpn-server-manager.git
git push -u origin main
```

**📖 Подробное руководство**: [GIT_GITHUB_GUIDE.md](GIT_GITHUB_GUIDE.md) - Полное руководство по работе с Git и GitHub  
**⚡ Быстрая шпаргалка**: [GIT_CHEATSHEET.md](GIT_CHEATSHEET.md) - Основные Git команды

## 🔒 Безопасность

- Все пароли и чувствительные данные хранятся в зашифрованном виде
- Используется алгоритм Fernet (AES-128 + HMAC-SHA256)
- Ключ шифрования хранится отдельно от данных
- Защита PIN-кодом от несанкционированного доступа

## 🌐 Многоязычность

Приложение поддерживает следующие языки:
- Русский (по умолчанию)
- Английский
- Китайский

Язык определяется автоматически по настройкам системы или может быть выбран вручную.

## 📝 История изменений

См. [CHANGELOG.md](CHANGELOG.md) для информации о всех изменениях.

## 📜 Лицензия

Распространяется под лицензией MIT. См. [LICENSE](LICENSE) для получения дополнительной информации. 