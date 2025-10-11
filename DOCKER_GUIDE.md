# 🐳 Руководство по запуску VPN Server Manager v4.0.0 с Docker

Это руководство описывает различные способы запуска VPN Server Manager v4.0.0 с использованием Docker и Docker Compose.

## 📋 Содержание

- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
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

## 🔨 Сборка образа

### Сборка production образа
```bash
docker build -t vpn-manager-clean:latest .
```

### Сборка с тегами версий
```bash
docker build -t vpn-manager-clean:4.0.0 .
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

### Базовый запуск
```bash
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

### Масштабирование
```bash
# Запуск нескольких экземпляров
docker-compose up --scale vpn-manager=3
```

## ⚙️ Переменные окружения

### Основные переменные
```bash
# Секретный ключ Flask (ОБЯЗАТЕЛЬНО!)
SECRET_KEY=your-secret-key-here

# Настройки приложения
APP_VERSION=4.0.0
APP_NAME=VPNServerManager-Clean

# Интернационализация
BABEL_DEFAULT_LOCALE=ru
BABEL_SUPPORTED_LOCALES=ru,en,zh

# Настройки сервера
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
# Проверка занятых портов
lsof -i :5000

# Использование другого порта
docker run -p 5001:5000 vpn-manager-clean:latest
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

**Примечание**: Это руководство актуально для VPN Server Manager v4.0.0 с новой модульной архитектурой.
