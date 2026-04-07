# 📚 GitHub Actions: Практические уроки

## 🎯 Урок 1: Первые шаги

### Цель урока:
Создать простой GitHub Actions workflow для тестирования Python приложения.

### Что вы изучите:
- Создание файла workflow
- Базовую структуру YAML
- Запуск и мониторинг

### Практическое задание:

#### Шаг 1: Создайте файл workflow
Создайте файл `.github/workflows/lesson1.yml`:

```yaml
name: Lesson 1 - Basic Test

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run basic test
      run: |
        python test_basic.py
```

#### Шаг 2: Запустите workflow
1. Сохраните файл и отправьте в GitHub
2. Перейдите в **Actions** в вашем репозитории
3. Найдите ваш workflow и нажмите на него
4. Изучите логи выполнения

#### Шаг 3: Анализ результатов
- ✅ **Успех**: Зеленый значок - все работает
- ❌ **Ошибка**: Красный значок - нужно исправить
- ⏳ **В процессе**: Желтый значок - выполняется

### Вопросы для самопроверки:
1. Что означает `runs-on: ubuntu-latest`?
2. Зачем нужен `actions/checkout@v4`?
3. Что делает `actions/setup-python@v5`?

---

## 🎯 Урок 2: Матрицы и стратегии

### Цель урока:
Научиться тестировать код на разных версиях Python и операционных системах.

### Что вы изучите:
- Использование матриц
- Тестирование на разных платформах
- Оптимизация времени выполнения

### Практическое задание:

#### Шаг 1: Создайте матрицу Python версий
Создайте файл `.github/workflows/lesson2.yml`:

```yaml
name: Lesson 2 - Matrix Testing

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python test_basic.py
```

#### Шаг 2: Добавьте тестирование на разных ОС
```yaml
name: Lesson 2 - Multi-Platform Testing

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.11]
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python test_basic.py
```

### Вопросы для самопроверки:
1. Сколько jobs создастся при использовании матрицы?
2. Как избежать дублирования кода в матрице?
3. Когда использовать матрицы, а когда нет?

---

## 🎯 Урок 3: Кэширование и оптимизация

### Цель урока:
Научиться ускорять выполнение workflow с помощью кэширования.

### Что вы изучите:
- Кэширование зависимостей
- Кэширование артефактов
- Измерение производительности

### Практическое задание:

#### Шаг 1: Добавьте кэширование pip
```yaml
name: Lesson 3 - Caching

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python test_basic.py
```

#### Шаг 2: Измерьте время выполнения
Добавьте в начало и конец workflow:

```yaml
    - name: Start timer
      run: echo "::set-output name=start_time::$(date +%s)"
      id: timer_start
    
    # ... ваши steps ...
    
    - name: End timer
      run: |
        end_time=$(date +%s)
        duration=$((end_time - ${{ steps.timer_start.outputs.start_time }}))
        echo "Workflow completed in $duration seconds"
```

### Вопросы для самопроверки:
1. Что такое `hashFiles()` и зачем он нужен?
2. Как работает `restore-keys`?
3. Когда кэширование не помогает?

---

## 🎯 Урок 4: Условное выполнение

### Цель урока:
Научиться выполнять шаги только при определенных условиях.

### Что вы изучите:
- Условные операторы
- Переменные окружения
- Контекст GitHub

### Практическое задание:

#### Шаг 1: Создайте условные шаги
```yaml
name: Lesson 4 - Conditional Execution

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests (always)
      run: |
        python test_basic.py
    
    - name: Run advanced tests (only on main)
      if: github.ref == 'refs/heads/main'
      run: |
        python advanced_tests.py
    
    - name: Send notification (only on failure)
      if: failure()
      run: |
        echo "Tests failed on ${{ github.ref }}"
```

#### Шаг 2: Используйте переменные окружения
```yaml
    - name: Run with environment
      env:
        TEST_MODE: ${{ github.ref == 'refs/heads/main' && 'production' || 'development' }}
        BRANCH_NAME: ${{ github.ref_name }}
      run: |
        echo "Running in $TEST_MODE mode on branch $BRANCH_NAME"
        python test_basic.py
```

### Вопросы для самопроверки:
1. Какие переменные доступны в `github.*`?
2. Как проверить, что код выполняется в Pull Request?
3. Когда использовать `if: success()` и `if: failure()`?

---

## 🎯 Урок 5: Артефакты и результаты

### Цель урока:
Научиться сохранять и использовать результаты выполнения workflow.

### Что вы изучите:
- Загрузка артефактов
- Скачивание артефактов
- Сохранение результатов тестов

### Практическое задание:

#### Шаг 1: Создайте артефакты
```yaml
name: Lesson 5 - Artifacts

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Run tests
      run: |
        python test_basic.py
    
    - name: Build application
      run: |
        pyinstaller --onefile app.py
    
    - name: Upload build artifact
      uses: actions/upload-artifact@v3
      with:
        name: my-app
        path: dist/
        retention-days: 7
```

#### Шаг 2: Используйте артефакты в другом job
```yaml
  deploy:
    needs: build
    runs-on: ubuntu-latest
    
    steps:
    - name: Download artifact
      uses: actions/download-artifact@v3
      with:
        name: my-app
        path: ./downloads
    
    - name: List downloaded files
      run: |
        ls -la ./downloads
```

### Вопросы для самопроверки:
1. Что такое `needs:` и зачем оно нужно?
2. Как долго хранятся артефакты?
3. Можно ли передать артефакты между разными workflow?

---

## 🎯 Урок 6: Безопасность и секреты

### Цель урока:
Научиться безопасно работать с чувствительными данными.

### Что вы изучите:
- GitHub Secrets
- Переменные окружения
- Безопасные практики

### Практическое задание:

#### Шаг 1: Настройте секреты
1. Перейдите в **Settings → Secrets and variables → Actions**
2. Создайте секрет `DATABASE_URL`
3. Создайте секрет `API_KEY`

#### Шаг 2: Используйте секреты в workflow
```yaml
name: Lesson 6 - Security

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests with secrets
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        API_KEY: ${{ secrets.API_KEY }}
        PUBLIC_VAR: "This is public"
      run: |
        echo "Database URL: $DATABASE_URL"
        echo "API Key: $API_KEY"
        echo "Public var: $PUBLIC_VAR"
        python test_basic.py
```

### Вопросы для самопроверки:
1. Как отличить секреты от обычных переменных?
2. Можно ли использовать секреты в логи?
3. Как безопасно передать секреты между jobs?

---

## 🎯 Урок 7: Отладка и мониторинг

### Цель урока:
Научиться эффективно отлаживать проблемы в workflow.

### Что вы изучите:
- Чтение логов
- Отладка ошибок
- Мониторинг производительности

### Практическое задание:

#### Шаг 1: Добавьте подробное логирование
```yaml
name: Lesson 7 - Debugging

on:
  push:
    branches: [main]

jobs:
  debug:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Debug information
      run: |
        echo "=== System Information ==="
        echo "OS: $RUNNER_OS"
        echo "Architecture: $RUNNER_ARCH"
        echo "Python version: $(python --version)"
        echo "Current directory: $(pwd)"
        echo "Files in directory:"
        ls -la
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies with verbose output
      run: |
        pip install -r requirements.txt -v
    
    - name: Run tests with debug info
      run: |
        echo "=== Running tests ==="
        python test_basic.py
        echo "=== Tests completed ==="
```

#### Шаг 2: Создайте отладочный workflow
```yaml
name: Debug Workflow

on:
  workflow_dispatch:
    inputs:
      debug_level:
        description: 'Debug level'
        required: true
        default: 'info'
        type: choice
        options:
        - debug
        - info
        - warning
        - error

jobs:
  debug:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Debug with input
      run: |
        echo "Debug level: ${{ github.event.inputs.debug_level }}"
        echo "Repository: ${{ github.repository }}"
        echo "Event: ${{ github.event_name }}"
```

### Вопросы для самопроверки:
1. Как найти конкретную ошибку в логах?
2. Что такое `workflow_dispatch`?
3. Как добавить отладочную информацию в существующий workflow?

---

## 🎯 Урок 8: Интеграция с внешними сервисами

### Цель урока:
Научиться интегрировать GitHub Actions с внешними сервисами.

### Что вы изучите:
- Уведомления в Slack/Discord
- Интеграция с Telegram
- Отправка email

### Практическое задание:

#### Шаг 1: Настройте уведомления в Slack
```yaml
name: Lesson 8 - Notifications

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python test_basic.py
    
    - name: Notify success
      if: success()
      uses: 8398a7/action-slack@v3
      with:
        status: success
        text: "✅ Tests passed for ${{ github.repository }}"
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    
    - name: Notify failure
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        text: "❌ Tests failed for ${{ github.repository }}"
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

#### Шаг 2: Добавьте уведомления в Telegram
```yaml
    - name: Notify Telegram
      if: always()
      run: |
        curl -X POST \
          -H "Content-Type: application/json" \
          -d "{\"chat_id\":\"${{ secrets.TELEGRAM_CHAT_ID }}\",\"text\":\"GitHub Actions: ${{ job.status }}\"}" \
          https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage
```

### Вопросы для самопроверки:
1. Как настроить webhook для Slack?
2. Какие секреты нужны для Telegram?
3. Когда использовать `if: always()`?

---

## 🎯 Урок 9: Оптимизация и лучшие практики

### Цель урока:
Научиться создавать эффективные и надежные workflow.

### Что вы изучите:
- Оптимизация времени выполнения
- Лучшие практики
- Мониторинг производительности

### Практическое задание:

#### Шаг 1: Создайте оптимизированный workflow
```yaml
name: Lesson 9 - Optimized Workflow

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

# Ограничиваем одновременные runs
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: 3.11
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python test_basic.py
    
    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: test-results/
        retention-days: 7
```

#### Шаг 2: Добавьте мониторинг
```yaml
    - name: Performance report
      if: always()
      run: |
        echo "=== Performance Report ==="
        echo "Job duration: ${{ job.steps.*.conclusion }}"
        echo "Steps completed: ${{ job.steps.*.conclusion == 'success' }}"
        echo "Steps failed: ${{ job.steps.*.conclusion == 'failure' }}"
```

### Вопросы для самопроверки:
1. Что такое `concurrency` и зачем оно нужно?
2. Как измерить время выполнения workflow?
3. Какие метрики важны для мониторинга?

---

## 🎯 Урок 10: Создание собственных Actions

### Цель урока:
Научиться создавать переиспользуемые GitHub Actions.

### Что вы изучите:
- Структура Action
- Docker containers
- JavaScript Actions

### Практическое задание:

#### Шаг 1: Создайте простой Action
Создайте файл `action.yml`:

```yaml
name: 'My Custom Action'
description: 'A simple custom action'
inputs:
  name:
    description: 'Name to greet'
    required: true
    default: 'World'
runs:
  using: 'composite'
  steps:
    - name: Greet
      shell: bash
      run: echo "Hello, ${{ inputs.name }}!"
```

#### Шаг 2: Используйте ваш Action
```yaml
name: Lesson 10 - Custom Action

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Get code
      uses: actions/checkout@v4
    
    - name: Use custom action
      uses: ./
      with:
        name: 'GitHub Actions Student'
```

### Вопросы для самопроверки:
1. Какие типы Actions существуют?
2. Как передать параметры в Action?
3. Как опубликовать Action в Marketplace?

---

## 🎉 Заключение

Поздравляем! Вы прошли полный курс по GitHub Actions. Теперь вы можете:

- ✅ Создавать простые и сложные workflow
- ✅ Оптимизировать производительность
- ✅ Интегрировать с внешними сервисами
- ✅ Отлаживать проблемы
- ✅ Создавать собственные Actions

### 🎯 Следующие шаги:

1. **Практикуйтесь** - создавайте workflow для своих проектов
2. **Изучайте** - читайте документацию и примеры
3. **Экспериментируйте** - пробуйте новые возможности
4. **Делитесь** - помогайте другим изучать GitHub Actions

### 📚 Дополнительные ресурсы:

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Examples](https://github.com/actions/starter-workflows)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [GitHub Actions Cheat Sheet](https://github.com/actions/cheat-sheet)

**Удачи в изучении GitHub Actions!** 🚀 