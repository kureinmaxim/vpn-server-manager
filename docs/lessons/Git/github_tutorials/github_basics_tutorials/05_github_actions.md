# Урок 5: GitHub Actions

В этом уроке мы рассмотрим GitHub Actions — мощный инструмент для автоматизации рабочих процессов в репозиториях GitHub.

## Что такое GitHub Actions?

GitHub Actions — это платформа непрерывной интеграции и непрерывной доставки (CI/CD), которая позволяет автоматизировать различные задачи в вашем репозитории: от сборки и тестирования до развертывания и публикации.

### Основные преимущества GitHub Actions:

- **Интеграция с GitHub**: тесная интеграция с репозиториями, issues и pull requests
- **Гибкость**: поддержка различных языков программирования и платформ
- **Расширяемость**: огромная библиотека готовых действий (actions)
- **Бесплатное использование**: определенное количество минут выполнения бесплатно
- **Настраиваемые рабочие процессы**: полный контроль над автоматизацией

## Основные концепции GitHub Actions

### Рабочий процесс (Workflow)

Рабочий процесс — это автоматизированный процесс, который вы настраиваете в репозитории. Рабочие процессы определяются в YAML-файлах в директории `.github/workflows/`.

### События (Events)

События — это специфические действия, которые запускают рабочий процесс. Примеры:
- Push в репозиторий
- Создание Pull Request
- Создание Issue
- Запланированное время (cron)
- Ручной запуск

### Задания (Jobs)

Задания — это набор шагов, которые выполняются на одном и том же раннере (виртуальной машине). Задания могут выполняться параллельно или последовательно.

### Шаги (Steps)

Шаги — это отдельные задачи, которые выполняются в рамках задания. Шаги могут быть командами оболочки или действиями.

### Действия (Actions)

Действия — это повторно используемые блоки кода, которые выполняют определенную задачу. Действия могут быть созданы вами или сообществом.

### Раннеры (Runners)

Раннеры — это серверы, на которых выполняются рабочие процессы. GitHub предоставляет раннеры с различными операционными системами, или вы можете использовать свои собственные.

## Создание первого рабочего процесса

### Структура директории

```
repository/
  ├── .github/
  │   └── workflows/
  │       └── main.yml
  └── ...
```

### Базовый рабочий процесс

Создайте файл `.github/workflows/main.yml`:

```yaml
name: CI

# Определяем события, которые запускают рабочий процесс
on:
  # Запускается при push в ветку main
  push:
    branches: [ main ]
  # Запускается при создании pull request в ветку main
  pull_request:
    branches: [ main ]
  # Возможность запуска вручную из интерфейса GitHub
  workflow_dispatch:

# Рабочий процесс состоит из одного или нескольких заданий
jobs:
  # Задание с ID "build"
  build:
    # Тип раннера, на котором будет выполняться задание
    runs-on: ubuntu-latest

    # Шаги представляют собой последовательность задач
    steps:
      # Проверяем код из репозитория
      - uses: actions/checkout@v3

      # Выполняем команду в оболочке
      - name: Run a one-line script
        run: echo Hello, world!

      # Выполняем многострочный скрипт
      - name: Run a multi-line script
        run: |
          echo Add other actions to build,
          echo test, and deploy your project.
```

## Синтаксис рабочих процессов

### Определение событий

```yaml
on:
  push:
    branches: [ main, develop ]
    paths:
      - 'src/**'
      - '!**.md'
    tags:
      - 'v*'
  pull_request:
    types: [opened, synchronize, reopened]
  schedule:
    - cron: '0 0 * * *'  # Запуск каждый день в полночь
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
        type: choice
        options:
          - development
          - staging
          - production
```

### Настройка заданий

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    
    # Определение переменных окружения
    env:
      NODE_ENV: production
    
    # Определение стратегии матрицы для тестирования на разных платформах
    strategy:
      matrix:
        node-version: [14.x, 16.x, 18.x]
        os: [ubuntu-latest, windows-latest, macos-latest]
      
    # Условное выполнение задания
    if: github.event_name == 'push'
    
    # Зависимости между заданиями
    needs: [test]
    
    # Таймаут задания
    timeout-minutes: 10
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: npm run build
```

### Использование контекстов и выражений

GitHub Actions предоставляет различные контексты для доступа к информации о рабочем процессе:

```yaml
steps:
  - name: Print context information
    run: |
      echo "Repository: ${{ github.repository }}"
      echo "Branch: ${{ github.ref }}"
      echo "Commit SHA: ${{ github.sha }}"
      echo "Actor: ${{ github.actor }}"
      echo "Event name: ${{ github.event_name }}"
```

### Условные выражения

```yaml
steps:
  - name: Step that runs only on main branch
    if: github.ref == 'refs/heads/main'
    run: echo "This is the main branch"
  
  - name: Step that runs only on pull requests
    if: github.event_name == 'pull_request'
    run: echo "This is a pull request"
```

## Популярные действия и их использование

### Проверка кода (Checkout)

```yaml
- uses: actions/checkout@v3
  with:
    # Количество коммитов для извлечения
    fetch-depth: 0
    # Токен для аутентификации
    token: ${{ secrets.GITHUB_TOKEN }}
```

### Настройка Node.js

```yaml
- uses: actions/setup-node@v3
  with:
    node-version: '16'
    cache: 'npm'
```

### Настройка Python

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.10'
    cache: 'pip'
```

### Кэширование зависимостей

```yaml
- uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Загрузка и выгрузка артефактов

```yaml
- uses: actions/upload-artifact@v3
  with:
    name: build-artifacts
    path: dist/

- uses: actions/download-artifact@v3
  with:
    name: build-artifacts
    path: dist/
```

## Секреты и переменные окружения

### Использование секретов

Секреты хранятся в репозитории или организации и могут быть использованы в рабочих процессах:

```yaml
steps:
  - name: Deploy to production
    run: |
      echo "Deploying to production server"
      scp -r dist/ user@${{ secrets.PRODUCTION_SERVER }}:/var/www/html/
    env:
      SSH_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
```

### Настройка секретов

1. Перейдите в репозиторий → Settings → Secrets and variables → Actions
2. Нажмите "New repository secret"
3. Введите имя и значение секрета
4. Нажмите "Add secret"

### Переменные окружения

```yaml
env:
  # Глобальные переменные для всего рабочего процесса
  GLOBAL_VAR: "global value"

jobs:
  build:
    env:
      # Переменные для конкретного задания
      JOB_VAR: "job value"
    
    steps:
      - name: Use environment variables
        env:
          # Переменные для конкретного шага
          STEP_VAR: "step value"
        run: |
          echo "Global: $GLOBAL_VAR"
          echo "Job: $JOB_VAR"
          echo "Step: $STEP_VAR"
```

## Примеры типичных рабочих процессов

### CI для JavaScript/Node.js проекта

```yaml
name: Node.js CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        node-version: [14.x, 16.x, 18.x]

    steps:
    - uses: actions/checkout@v3
    
    - name: Use Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v3
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Lint
      run: npm run lint
    
    - name: Test
      run: npm test
    
    - name: Build
      run: npm run build
```

### CI/CD для Python проекта

```yaml
name: Python CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flake8 pytest
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    
    - name: Test with pytest
      run: |
        pytest
  
  deploy:
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build and publish
      env:
        TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
        TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
      run: |
        python -m build
        twine upload dist/*
```

### Развертывание статического сайта на GitHub Pages

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Build
      run: npm run build
    
    - name: Deploy
      uses: JamesIves/github-pages-deploy-action@v4
      with:
        folder: dist
        branch: gh-pages
```

## Создание собственных действий

### Типы действий

1. **Docker-действия**: запускаются в контейнере Docker
2. **JavaScript-действия**: запускаются непосредственно на раннере
3. **Composite-действия**: комбинируют несколько шагов

### Структура действия

```
my-action/
  ├── action.yml
  ├── Dockerfile (для Docker-действий)
  ├── index.js (для JavaScript-действий)
  └── README.md
```

### Пример action.yml для JavaScript-действия

```yaml
name: 'Hello World'
description: 'Greet someone and record the time'
inputs:
  who-to-greet:
    description: 'Who to greet'
    required: true
    default: 'World'
outputs:
  time:
    description: 'The time we greeted you'
runs:
  using: 'node16'
  main: 'index.js'
```

### Пример index.js для JavaScript-действия

```javascript
const core = require('@actions/core');
const github = require('@actions/github');

try {
  // Получаем входные параметры
  const nameToGreet = core.getInput('who-to-greet');
  console.log(`Hello ${nameToGreet}!`);
  
  // Получаем текущее время
  const time = new Date().toTimeString();
  
  // Устанавливаем выходные параметры
  core.setOutput("time", time);
  
  // Получаем контекст события
  const payload = JSON.stringify(github.context.payload, null, 2);
  console.log(`The event payload: ${payload}`);
} catch (error) {
  core.setFailed(error.message);
}
```

### Использование собственного действия

```yaml
jobs:
  hello_world_job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: ./my-action
        with:
          who-to-greet: 'Mona the Octocat'
      - run: echo "The time was ${{ steps.hello.outputs.time }}"
```

## Лучшие практики для GitHub Actions

1. **Используйте минимальные права доступа**:
   - Используйте `permissions` для ограничения прав токена GITHUB_TOKEN
   - Создавайте и используйте специальные токены для конкретных задач

2. **Оптимизируйте рабочие процессы**:
   - Используйте кэширование для ускорения сборок
   - Разделяйте задания для параллельного выполнения
   - Используйте матрицы для тестирования на разных платформах

3. **Обеспечивайте безопасность**:
   - Не храните секреты в коде
   - Проверяйте зависимости на уязвимости
   - Используйте закрепленные версии действий (например, `actions/checkout@v3` вместо `actions/checkout@main`)

4. **Документируйте рабочие процессы**:
   - Добавляйте комментарии к сложным частям рабочих процессов
   - Создавайте README с описанием рабочих процессов
   - Используйте понятные имена для заданий и шагов

5. **Используйте повторно используемые рабочие процессы**:
   - Создавайте общие рабочие процессы для повторяющихся задач
   - Используйте `workflow_call` для вызова рабочих процессов из других рабочих процессов

## Отладка рабочих процессов

### Включение отладочного журнала

```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

### Использование tmate для интерактивной отладки

```yaml
steps:
  - uses: actions/checkout@v3
  - name: Setup tmate session
    uses: mxschmitt/action-tmate@v3
```

### Просмотр журналов

1. Перейдите на страницу Actions в репозитории
2. Выберите рабочий процесс
3. Выберите конкретный запуск
4. Нажмите на задание для просмотра журналов

## Заключение

GitHub Actions — это мощный инструмент для автоматизации различных аспектов разработки программного обеспечения. Он позволяет настраивать сложные рабочие процессы для сборки, тестирования и развертывания приложений, а также автоматизировать рутинные задачи, такие как проверка кода, обновление зависимостей и многое другое.

В этом уроке мы рассмотрели основные концепции GitHub Actions, научились создавать и настраивать рабочие процессы, использовать популярные действия и создавать собственные. Мы также рассмотрели лучшие практики и методы отладки рабочих процессов.

Продолжайте изучать возможности GitHub Actions и экспериментировать с различными рабочими процессами для оптимизации вашего процесса разработки.

## Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Marketplace for Actions](https://github.com/marketplace?type=actions)
- [Awesome Actions](https://github.com/sdras/awesome-actions) - коллекция полезных действий
- [GitHub Actions Toolkit](https://github.com/actions/toolkit) - набор библиотек для создания JavaScript-действий 