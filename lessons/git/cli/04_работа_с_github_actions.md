# Урок 4: Работа с GitHub Actions через GitHub CLI

В этом уроке мы рассмотрим, как управлять GitHub Actions с помощью GitHub CLI. GitHub Actions — это инструмент для автоматизации рабочих процессов, таких как сборка, тестирование и развертывание кода.

## Основы GitHub Actions

GitHub Actions позволяют автоматизировать различные задачи в вашем репозитории:
- Запуск тестов при каждом push или pull request
- Автоматическая сборка и публикация пакетов
- Развертывание приложений
- Проверка кода с помощью линтеров
- Отправка уведомлений

Рабочие процессы (workflows) определяются в YAML-файлах, которые хранятся в директории `.github/workflows` вашего репозитория.

## Просмотр рабочих процессов

### Просмотр всех рабочих процессов в репозитории

```bash
gh workflow list
```

### Просмотр конкретного рабочего процесса

```bash
# Просмотр по ID или имени файла
gh workflow view 12345
gh workflow view main.yml

# Просмотр в браузере
gh workflow view main.yml --web
```

## Управление рабочими процессами

### Включение и отключение рабочих процессов

```bash
# Включение рабочего процесса
gh workflow enable main.yml

# Отключение рабочего процесса
gh workflow disable main.yml
```

## Работа с запусками рабочих процессов (runs)

### Просмотр запусков рабочих процессов

```bash
# Просмотр последних запусков всех рабочих процессов
gh run list

# Просмотр запусков конкретного рабочего процесса
gh run list --workflow main.yml
```

### Просмотр конкретного запуска

```bash
# Просмотр запуска по ID
gh run view 123456789

# Просмотр логов запуска
gh run view 123456789 --log

# Просмотр запуска в браузере
gh run view 123456789 --web
```

### Ручной запуск рабочего процесса

```bash
# Запуск рабочего процесса по имени файла
gh workflow run main.yml

# Запуск с входными параметрами
gh workflow run main.yml -f environment=production -f debug=true
```

### Отмена запуска рабочего процесса

```bash
gh run cancel 123456789
```

### Повторный запуск рабочего процесса

```bash
gh run rerun 123456789

# Повторный запуск с отладкой
gh run rerun 123456789 --debug
```

### Просмотр и загрузка артефактов

```bash
# Просмотр артефактов запуска
gh run view 123456789 --log

# Загрузка всех артефактов
gh run download 123456789
```

## Создание и редактирование рабочих процессов

GitHub CLI не предоставляет прямых команд для создания или редактирования файлов рабочих процессов, но вы можете использовать стандартные команды Git или API GitHub для этого.

### Создание нового рабочего процесса с помощью Git

```bash
# Создание директории для рабочих процессов (если она не существует)
mkdir -p .github/workflows

# Создание файла рабочего процесса
cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
    - name: Install dependencies
      run: npm ci
    - name: Run tests
      run: npm test
EOF

# Добавление и коммит файла
git add .github/workflows/ci.yml
git commit -m "Add CI workflow"
git push
```

## Секреты и переменные для GitHub Actions

GitHub CLI позволяет управлять секретами и переменными, которые используются в GitHub Actions.

### Управление секретами репозитория

```bash
# Создание или обновление секрета
gh secret set API_KEY

# Создание секрета из файла
gh secret set CERTIFICATE < certificate.pem

# Просмотр списка секретов
gh secret list

# Удаление секрета
gh secret delete API_KEY
```

### Управление переменными репозитория

```bash
# Создание или обновление переменной
gh variable set APP_NAME --body "my-app"

# Просмотр списка переменных
gh variable list

# Удаление переменной
gh variable delete APP_NAME
```

## Практические примеры

### Пример 1: Настройка CI/CD для Node.js проекта

```bash
# Создаем рабочий процесс для CI/CD
mkdir -p .github/workflows

# Создаем файл для CI
cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
    - name: Install dependencies
      run: npm ci
    - name: Run linter
      run: npm run lint
    - name: Run tests
      run: npm test
    - name: Upload coverage
      uses: actions/upload-artifact@v3
      with:
        name: coverage
        path: coverage/
EOF

# Создаем файл для CD
cat > .github/workflows/cd.yml << 'EOF'
name: CD

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    needs: test
    steps:
    - uses: actions/checkout@v3
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
    - name: Install dependencies
      run: npm ci
    - name: Build
      run: npm run build
    - name: Deploy
      run: |
        echo "Deploying to production..."
        # Здесь команды для деплоя
      env:
        DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
EOF

# Добавляем секрет для деплоя
gh secret set DEPLOY_KEY

# Коммитим и отправляем файлы
git add .github/workflows/
git commit -m "Add CI/CD workflows"
git push

# Проверяем статус рабочих процессов
gh workflow list
```

### Пример 2: Отладка неудачного запуска рабочего процесса

```bash
# Просматриваем последние запуски
gh run list

# Предположим, что запуск с ID 123456789 завершился с ошибкой
# Просматриваем детали запуска
gh run view 123456789

# Просматриваем логи для отладки
gh run view 123456789 --log

# Исправляем проблему в коде или рабочем процессе
# ...

# Запускаем рабочий процесс повторно
gh run rerun 123456789
```

### Пример 3: Настройка запуска рабочего процесса по расписанию

```bash
cat > .github/workflows/scheduled.yml << 'EOF'
name: Scheduled Task

on:
  schedule:
    - cron: '0 0 * * *'  # Запуск каждый день в полночь

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Backup data
      run: |
        echo "Performing backup..."
        # Команды для резервного копирования
      env:
        BACKUP_TOKEN: ${{ secrets.BACKUP_TOKEN }}
EOF

# Добавляем секрет для резервного копирования
gh secret set BACKUP_TOKEN

# Коммитим и отправляем файл
git add .github/workflows/scheduled.yml
git commit -m "Add scheduled backup workflow"
git push

# Проверяем, что рабочий процесс добавлен
gh workflow list
```

## Расширенные возможности

### Использование GitHub API через GitHub CLI

GitHub CLI позволяет выполнять произвольные запросы к GitHub API:

```bash
# Получение информации о последних запусках рабочих процессов
gh api repos/{owner}/{repo}/actions/runs

# Получение информации о конкретном запуске
gh api repos/{owner}/{repo}/actions/runs/123456789

# Создание dispatch event для запуска рабочего процесса
gh api repos/{owner}/{repo}/dispatches -f event_type=deploy -f client_payload='{"environment":"production"}'
```

### Использование расширений GitHub CLI

GitHub CLI поддерживает расширения, которые добавляют дополнительные функции:

```bash
# Просмотр доступных расширений
gh extension list

# Установка расширения
gh extension install owner/name

# Пример: установка расширения для визуализации рабочих процессов
gh extension install nektos/gh-act
```

## Заключение

GitHub CLI предоставляет удобные инструменты для управления GitHub Actions прямо из командной строки. Это позволяет эффективно автоматизировать процессы разработки, тестирования и развертывания, а также быстро отлаживать проблемы с рабочими процессами.

В следующем уроке мы рассмотрим расширенные возможности GitHub CLI и интеграцию с другими инструментами. 