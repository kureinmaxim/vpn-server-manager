# Руководство по запуску VPN Server Manager с Docker

Это руководство описывает запуск VPN Server Manager с Docker и Docker Compose.

## 📋 Содержание

- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Особенности Windows](#особенности-windows)
- [Особенности macOS](#особенности-macos)
- [Сборка образа](#сборка-образа)
- [Запуск контейнера](#запуск-контейнера)
- [Docker Compose](#docker-compose)
- [Переменные окружения](#переменные-окружения)
- [Volumes и данные](#volumes-и-данные)
- [Сетевые настройки](#сетевые-настройки)
- [Мониторинг и логи](#мониторинг-и-логи)
- [Разработка с Docker](#разработка-с-docker)
- [Troubleshooting](#troubleshooting)

## 🔧 Требования

- Docker 20.10+ 
- Docker Compose 2.0+
- Минимум 2GB свободного места на диске
- Порты 5000 и 5001 (для dev режима) должны быть свободны

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager
```

### 2. Создание .env файла
```bash
cp env.example .env
# Отредактируйте .env файл с вашими настройками
```

### 3. Запуск с Docker Compose
```bash
docker-compose up
```

Приложение будет доступно по адресу: http://localhost:5000

## 🪟 Особенности Windows

### Docker Desktop для Windows

Docker на Windows работает через WSL2 (Windows Subsystem for Linux) или Hyper-V.

#### Установка Docker Desktop
1. Скачайте [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop)
2. Установите с включенным WSL2 backend (рекомендуется)
3. Перезагрузите компьютер

#### Особенности синтаксиса команд

**PowerShell:**
```powershell
# Volumes - используйте ${PWD} вместо $(pwd)
docker run -p 5000:5000 `
  -v ${PWD}/data:/app/data `
  -v ${PWD}/logs:/app/logs `
  vpn-manager-clean:latest

# Docker Compose
docker-compose up -d
```

**CMD:**
```cmd
REM Volumes - используйте %cd% для текущей директории
docker run -p 5000:5000 ^
  -v %cd%/data:/app/data ^
  -v %cd%/logs:/app/logs ^
  vpn-manager-clean:latest

REM Docker Compose
docker-compose up -d
```

**Git Bash (рекомендуется):**
```bash
# Работает так же, как на Linux/macOS
docker run -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  vpn-manager-clean:latest
```

#### Пути к файлам в Windows

```powershell
# Абсолютный путь в PowerShell
-v C:\Users\YourName\vpn-manager\data:/app/data

# Относительный путь (рекомендуется)
-v ${PWD}\data:/app/data

# WSL2 путь (если репозиторий в WSL)
-v /mnt/c/Users/YourName/vpn-manager/data:/app/data
```

#### Создание директорий в Windows

```powershell
# PowerShell
New-Item -ItemType Directory -Force -Path data, logs, uploads

# CMD
mkdir data logs uploads

# Git Bash
mkdir -p data logs uploads
```

#### Проблемы и решения для Windows

**Проблема: "Error during connect"**
```powershell
# Убедитесь, что Docker Desktop запущен
# Проверьте статус WSL2
wsl --status

# Перезапустите Docker Desktop
Restart-Service com.docker.service
```

**Проблема: Медленная работа с volumes**
```powershell
# Рекомендация: храните проект в WSL2, а не в Windows файловой системе
# Откройте WSL2 терминал
wsl

# Клонируйте проект в WSL
cd ~
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager
docker-compose up
```

**Проблема: Line endings (CRLF vs LF)**
```bash
# Настройте Git для автоматической конвертации
git config --global core.autocrlf true

# Или используйте .gitattributes (уже настроено в проекте)
```

#### Docker Compose на Windows

```powershell
# PowerShell - используйте обратные кавычки ` для переноса строк
docker-compose `
  --profile dev `
  up -d

# CMD - используйте ^ для переноса строк  
docker-compose ^
  --profile dev ^
  up -d
```

#### Рекомендации для Windows

1. **Используйте WSL2** вместо Hyper-V для лучшей производительности
2. **Храните проект в WSL2** для быстрой работы с volumes
3. **Используйте Git Bash** или WSL2 терминал для команд
4. **Добавьте исключения в Windows Defender** для Docker volumes
5. **Выделите достаточно ресурсов** в Docker Desktop Settings (минимум 2GB RAM)

## 🍎 Особенности macOS

### Docker Desktop для macOS

Docker на macOS работает через виртуализацию (Hypervisor.framework).

#### Установка Docker Desktop
1. Скачайте [Docker Desktop для macOS](https://www.docker.com/products/docker-desktop)
2. Выберите версию для вашего процессора:
   - **Apple Silicon (M1/M2/M3)**: ARM64 версия
   - **Intel**: AMD64 версия
3. Перетащите Docker.app в Applications
4. Запустите и следуйте инструкциям

#### Особенности команд для macOS

```bash
# Стандартный синтаксис - работает как на Linux
docker run -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  vpn-manager-clean:latest

# Docker Compose
docker-compose up -d
```

#### Проблемы с правами доступа в macOS

```bash
# Если возникают проблемы с правами
sudo chown -R $(whoami):staff data logs uploads

# Или запустите с правильными правами
docker run --user $(id -u):$(id -g) \
  -v $(pwd)/data:/app/data \
  vpn-manager-clean:latest
```

#### Apple Silicon (M1/M2/M3) особенности

**Архитектура платформы:**
```bash
# Для Apple Silicon указывайте платформу явно
docker build --platform linux/arm64 -t vpn-manager-clean:latest .

# Или для совместимости с Intel
docker build --platform linux/amd64 -t vpn-manager-clean:latest .

# Multi-platform сборка
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t vpn-manager-clean:latest .
```

**Обновление docker-compose.yml для Apple Silicon:**
```yaml
services:
  vpn-manager:
    platform: linux/arm64  # Для M1/M2/M3
    # или
    platform: linux/amd64  # Для совместимости
```

#### Производительность на macOS

**Улучшение скорости volumes:**
```yaml
# В docker-compose.yml используйте делегированный режим
volumes:
  - ./data:/app/data:delegated
  - ./logs:/app/logs:delegated
  - ./uploads:/app/uploads:delegated
```

```bash
# Или в командной строке
docker run -v $(pwd)/data:/app/data:delegated vpn-manager-clean:latest
```

#### Проблемы и решения для macOS

**Проблема: "Cannot connect to Docker daemon"**
```bash
# Убедитесь, что Docker Desktop запущен
open -a Docker

# Проверьте статус
docker ps

# Перезапустите Docker Desktop
killall Docker && open -a Docker
```

**Проблема: Медленная работа с файлами**
```bash
# 1. Включите VirtioFS в Docker Desktop:
#    Settings → General → Enable VirtioFS

# 2. Используйте именованные volumes вместо bind mounts
docker volume create vpn-manager-data
docker run -v vpn-manager-data:/app/data vpn-manager-clean:latest

# 3. Добавьте :delegated или :cached к bind mounts
docker run -v $(pwd)/data:/app/data:delegated vpn-manager-clean:latest
```

**Проблема: Port уже используется**
```bash
# Найдите процесс на порту 5000
lsof -i :5000

# Завершите процесс
kill -9 <PID>

# Или используйте другой порт
docker run -p 5001:5000 vpn-manager-clean:latest
```

#### Рекомендации для macOS

1. **Используйте последнюю версию Docker Desktop** для лучшей производительности
2. **Для Apple Silicon**: используйте ARM64 образы когда возможно
3. **Включите VirtioFS** в настройках для быстрой работы с файлами
4. **Выделите достаточно ресурсов**: Settings → Resources (минимум 2GB RAM)
5. **Используйте именованные volumes** для критичных к производительности данных
6. **Регулярно обновляйте** Docker Desktop для исправления багов

#### Homebrew установка Docker

```bash
# Альтернативная установка через Homebrew
brew install --cask docker

# Или только Docker CLI
brew install docker docker-compose
```

## 🔨 Сборка образа

### Сборка production образа
```bash
docker build -t vpn-manager-clean:latest .
```

### Сборка с тегами версий
```bash
docker build -t vpn-manager-clean:4.3.5 .
docker build -t vpn-manager-clean:latest .
```

### Сборка без кеша
```bash
docker build --no-cache -t vpn-manager-clean:latest .
```

### Сборка с дополнительными аргументами
```bash
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  --build-arg FLASK_ENV=production \
  -t vpn-manager-clean:latest .
```

## 🏃 Запуск контейнера

### ⚠️ Важно о портах

**В Docker контейнере приложение НЕ использует динамические порты!**

- В **локальном режиме** (без Docker): приложение автоматически выбирает свободный порт
  - Desktop режим: порт `0` → ОС выбирает случайный свободный порт
  - Web режим: функция `find_free_port()` ищет порт начиная с 5000
  
- В **Docker контейнере**: приложение использует **фиксированный порт** 5000 внутри контейнера
  - Снаружи вы можете маппить любой порт хоста на порт 5000 контейнера
  - Формат: `-p HOST_PORT:CONTAINER_PORT`

### Базовый запуск
```bash
# Стандартный запуск на порту 5000
docker run -p 5000:5000 vpn-manager-clean:latest
```

### Запуск с переменными окружения
```bash
docker run -p 5000:5000 \
  -e SECRET_KEY=your-secret-key-here \
  -e BABEL_DEFAULT_LOCALE=ru \
  -e LOG_LEVEL=INFO \
  vpn-manager-clean:latest
```

### Запуск с volume для данных
```bash
docker run -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/uploads:/app/uploads \
  vpn-manager-clean:latest
```

### Запуск в фоновом режиме
```bash
docker run -d \
  --name vpn-manager \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  vpn-manager-clean:latest
```

### Запуск с пользовательскими настройками
```bash
docker run -p 5000:5000 \
  -e SECRET_KEY=your-secret-key-here \
  -e DEFAULT_PIN=1234 \
  -e DATA_DIR=/app/data \
  -e LOG_FILE=/app/logs/app.log \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  vpn-manager-clean:latest
```

## 🐙 Docker Compose

### Production конфигурация
```bash
# Запуск production версии
docker-compose up

# Запуск в фоновом режиме
docker-compose up -d

# Остановка
docker-compose down
```

### Development конфигурация
```bash
# Запуск dev версии с hot reload
docker-compose --profile dev up

# Запуск только dev сервиса
docker-compose up vpn-manager-dev
```

### Пересборка и запуск
```bash
# Пересборка образов
docker-compose build

# Принудительная пересборка
docker-compose build --no-cache

# Пересборка и запуск
docker-compose up --build
```

### Масштабирование и несколько экземпляров

**Запуск нескольких контейнеров одновременно:**

```bash
# Вариант 1: Указываем разные внешние порты вручную
docker run -d --name vpn-manager-1 -p 5000:5000 vpn-manager-clean:latest
docker run -d --name vpn-manager-2 -p 5001:5000 vpn-manager-clean:latest
docker run -d --name vpn-manager-3 -p 5002:5000 vpn-manager-clean:latest

# Вариант 2: Docker сам выберет случайные свободные порты хоста
docker run -d --name vpn-manager-1 -p 0:5000 vpn-manager-clean:latest
docker run -d --name vpn-manager-2 -p 0:5000 vpn-manager-clean:latest
docker run -d --name vpn-manager-3 -p 0:5000 vpn-manager-clean:latest

# Узнать, какие порты выбрал Docker:
docker ps

# Или для конкретного контейнера:
docker port vpn-manager-1
```

**Docker Compose масштабирование:**
```bash
# Внимание! Для масштабирования нужно убрать фиксированные порты из docker-compose.yml
# Или Docker Compose выдаст ошибку о конфликте портов

# В docker-compose.yml измените:
# ports:
#   - "5000:5000"
# на:
# ports:
#   - "5000-5010:5000"  # Диапазон портов
# или:
# ports:
#   - "5000"  # Без маппинга - Docker выберет случайный порт

# Затем запустите несколько экземпляров:
docker-compose up --scale vpn-manager=3
```

**Рекомендации для multi-app setup:**
- ✅ Используйте разные имена контейнеров (`--name`)
- ✅ Маппите разные внешние порты для каждого экземпляра
- ✅ Используйте разные volumes для каждого экземпляра (если нужна изоляция данных)
- ✅ Или используйте `-p 0:5000` для автоматического выбора портов

## ⚙️ Переменные окружения

### Основные переменные
```bash
# Секретный ключ Flask (ОБЯЗАТЕЛЬНО!)
SECRET_KEY=your-secret-key-here

# Настройки приложения
APP_VERSION=4.3.5
APP_NAME=VPNServerManager-Clean

# Интернационализация
BABEL_DEFAULT_LOCALE=ru
BABEL_SUPPORTED_LOCALES=ru,en,zh

# Настройки сервера
# PORT - порт ВНУТРИ контейнера (по умолчанию 5000)
# Если меняете PORT, не забудьте изменить маппинг портов!
PORT=5000
HOST=0.0.0.0

# Логирование
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# PIN код
DEFAULT_PIN=1234
```

### Переменные для разработки
```bash
# Режим разработки
FLASK_ENV=development
FLASK_DEBUG=1

# Дополнительные порты
DEV_PORT=5001
```

### Переменные для production
```bash
# Production настройки
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=WARNING

# Безопасность
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
```

## 💾 Volumes и данные

### Создание необходимых директорий
```bash
mkdir -p data logs uploads
```

### Маппинг volumes
```bash
# Основные данные
-v $(pwd)/data:/app/data

# Логи
-v $(pwd)/logs:/app/logs

# Загруженные файлы
-v $(pwd)/uploads:/app/uploads

# Конфигурация (опционально)
-v $(pwd)/.env:/app/.env
```

### Docker Compose volumes
```yaml
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
  - ./uploads:/app/uploads
  - app_data:/app/data  # Named volume
```

### Backup данных
```bash
# Создание backup
docker run --rm \
  -v vpn-manager_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz -C /data .

# Восстановление backup
docker run --rm \
  -v vpn-manager_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/backup.tar.gz -C /data
```

## 🌐 Сетевые настройки

### Кастомная сеть
```bash
# Создание сети
docker network create vpn-manager-network

# Запуск с кастомной сетью
docker run --network vpn-manager-network \
  -p 5000:5000 \
  vpn-manager-clean:latest
```

### Docker Compose сеть
```yaml
networks:
  vpn-manager:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Прокси и reverse proxy
```bash
# Запуск за nginx
docker run -p 8080:5000 \
  -e HOST=0.0.0.0 \
  vpn-manager-clean:latest
```

## 📊 Мониторинг и логи

### Просмотр логов
```bash
# Логи контейнера
docker logs vpn-manager

# Следить за логами в реальном времени
docker logs -f vpn-manager

# Логи с временными метками
docker logs -t vpn-manager
```

### Docker Compose логи
```bash
# Все сервисы
docker-compose logs

# Конкретный сервис
docker-compose logs vpn-manager

# Следить за логами
docker-compose logs -f
```

### Мониторинг ресурсов
```bash
# Статистика контейнера
docker stats vpn-manager

# Информация о контейнере
docker inspect vpn-manager

# Health check
docker exec vpn-manager curl -f http://localhost:5000/ || echo "Container unhealthy"
```

### Логи приложения
```bash
# Просмотр логов приложения
docker exec vpn-manager tail -f /app/logs/app.log

# Поиск ошибок
docker exec vpn-manager grep -i error /app/logs/app.log
```

## 🛠️ Разработка с Docker

### Development контейнер
```bash
# Запуск dev версии
docker-compose --profile dev up

# Или напрямую
docker run -p 5001:5000 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
  -e FLASK_DEBUG=1 \
  vpn-manager-clean:latest
```

### Hot reload для разработки
```bash
# Запуск с монтированием исходного кода
docker run -p 5001:5000 \
  -v $(pwd)/app:/app/app \
  -v $(pwd)/templates:/app/templates \
  -v $(pwd)/static:/app/static \
  -e FLASK_ENV=development \
  vpn-manager-clean:latest
```

### Отладка
```bash
# Запуск с отладчиком
docker run -p 5000:5000 \
  -p 5678:5678 \
  -e FLASK_DEBUG=1 \
  -e PYTHONPATH=/app \
  vpn-manager-clean:latest

# Подключение к контейнеру
docker exec -it vpn-manager bash

# Запуск Python в контейнере
docker exec -it vpn-manager python
```

### Тестирование
```bash
# Запуск тестов в контейнере
docker run --rm \
  -v $(pwd):/app \
  vpn-manager-clean:latest \
  python -m pytest

# Запуск конкретных тестов
docker run --rm \
  -v $(pwd):/app \
  vpn-manager-clean:latest \
  python -m pytest tests/test_services/
```

## 🔧 Troubleshooting

### Частые проблемы

#### 1. Контейнер не запускается
```bash
# Проверка логов
docker logs vpn-manager

# Проверка статуса
docker ps -a

# Перезапуск
docker restart vpn-manager
```

#### 2. Порт уже используется
```bash
# Проверка занятых портов (на хосте)
lsof -i :5000

# Решение 1: Использование другого внешнего порта
docker run -p 5001:5000 vpn-manager-clean:latest
# Приложение доступно на http://localhost:5001

# Решение 2: Docker выберет случайный свободный порт
docker run -p 0:5000 vpn-manager-clean:latest
# Узнать порт: docker ps или docker port <container_name>

# Решение 3: Изменить порт внутри контейнера
docker run -p 8080:8080 \
  -e PORT=8080 \
  vpn-manager-clean:latest
# Внимание: внешний порт должен совпадать с внутренним!
```

**Понимание портов в Docker:**
```bash
# Формат: -p HOST_PORT:CONTAINER_PORT
# 
# HOST_PORT - порт на вашем компьютере (можно любой свободный)
# CONTAINER_PORT - порт внутри контейнера (определяется переменной PORT)

# Примеры:
-p 5000:5000   # хост:5000 → контейнер:5000
-p 8080:5000   # хост:8080 → контейнер:5000 (приложение на http://localhost:8080)
-p 0:5000      # Docker выберет случайный свободный порт хоста
```

#### 3. Проблемы с правами доступа
```bash
# Создание директорий с правильными правами
mkdir -p data logs uploads
chmod 755 data logs uploads

# Запуск с правильным пользователем
docker run --user $(id -u):$(id -g) \
  -v $(pwd)/data:/app/data \
  vpn-manager-clean:latest
```

#### 4. Проблемы с .env файлом
```bash
# Проверка .env файла
cat .env

# Создание .env из примера
cp env.example .env

# Проверка переменных в контейнере
docker exec vpn-manager env | grep SECRET_KEY
```

#### 5. Проблемы с данными
```bash
# Проверка volumes
docker volume ls

# Очистка данных
docker volume rm vpn-manager_data

# Проверка монтирования
docker exec vpn-manager ls -la /app/data
```

### Полезные команды

#### Очистка Docker
```bash
# Удаление неиспользуемых контейнеров
docker container prune

# Удаление неиспользуемых образов
docker image prune

# Удаление неиспользуемых volumes
docker volume prune

# Полная очистка
docker system prune -a
```

#### Информация о контейнере
```bash
# Детальная информация
docker inspect vpn-manager

# Процессы в контейнере
docker exec vpn-manager ps aux

# Использование диска
docker exec vpn-manager df -h

# Сетевая информация
docker exec vpn-manager netstat -tlnp
```

## 📝 Примеры использования

### Разница между локальным запуском и Docker

**Локальный запуск (без Docker):**
```bash
# Desktop режим - динамический порт (автоматически выбирается ОС)
python run.py --desktop
# Вывод: 🚀 Flask сервер запущен на http://127.0.0.1:54321 (случайный порт)

# Web режим - поиск свободного порта начиная с 5000
python run.py
# Вывод: 📡 Web server: http://127.0.0.1:5000
# Если порт 5000 занят, попробует 5001, 5002, и т.д.

# Несколько экземпляров - каждый получит свой порт
python run.py &  # Порт 5000
python run.py &  # Порт 5001 (5000 занят)
python run.py &  # Порт 5002 (5000 и 5001 заняты)
```

**Docker запуск:**
```bash
# В Docker внутри контейнера всегда фиксированный порт 5000
docker run -p 5000:5000 vpn-manager-clean:latest
# Приложение слушает на порту 5000 ВНУТРИ контейнера
# Доступно на http://localhost:5000

# Несколько экземпляров - меняем ВНЕШНИЙ порт вручную
docker run -d -p 5000:5000 --name vpn-1 vpn-manager-clean:latest
docker run -d -p 5001:5000 --name vpn-2 vpn-manager-clean:latest
docker run -d -p 5002:5000 --name vpn-3 vpn-manager-clean:latest

# Или пусть Docker выберет порты автоматически
docker run -d -p 0:5000 --name vpn-1 vpn-manager-clean:latest
docker run -d -p 0:5000 --name vpn-2 vpn-manager-clean:latest
docker ps  # Посмотреть, какие порты выбрал Docker
```

**Почему в Docker не используются динамические порты?**
- Docker контейнеры изолированы от хост-системы
- Порт внутри контейнера фиксирован (5000 по умолчанию)
- Docker маппинг портов (`-p`) связывает порт хоста с портом контейнера
- Это дает больше контроля и предсказуемости в production окружении

### Production deployment
```bash
# 1. Создание .env файла
cp env.example .env
# Отредактируйте .env с production настройками

# 2. Создание директорий
mkdir -p data logs uploads

# 3. Запуск
docker-compose up -d

# 4. Проверка
curl http://localhost:5000/
```

### Development setup
```bash
# 1. Клонирование и настройка
git clone <repo>
cd vpn-server-manager
cp env.example .env

# 2. Запуск dev версии
docker-compose --profile dev up

# 3. Приложение доступно на http://localhost:5001
```

### CI/CD pipeline
```yaml
# .github/workflows/docker.yml
name: Docker Build
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t vpn-manager-clean .
      - name: Run tests
        run: docker run --rm vpn-manager-clean python -m pytest
```

## 🔗 Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask Docker Guide](https://flask.palletsprojects.com/en/2.0.x/deploying/docker/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/)

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker logs vpn-manager`
2. Убедитесь в правильности .env файла
3. Проверьте доступность портов
4. Создайте issue в репозитории с подробным описанием проблемы

---

**Примечание**: Это руководство для текущей модульной архитектуры VPN Server Manager. Версию релиза смотрите в `config/config.json.template`.
