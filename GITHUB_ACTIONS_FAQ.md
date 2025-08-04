# ❓ GitHub Actions: Часто задаваемые вопросы (FAQ)

## 🔧 Базовые вопросы

### Q: Что такое GitHub Actions?
**A:** GitHub Actions - это система автоматизации, которая позволяет автоматически выполнять задачи при изменениях в коде. Это как робот-помощник, который тестирует, собирает и развертывает ваш код.

### Q: Где создавать файлы GitHub Actions?
**A:** В папке `.github/workflows/` вашего репозитория. Например: `.github/workflows/ci.yml`

### Q: Какой синтаксис используется?
**A:** YAML (YAML Ain't Markup Language). Это простой формат для структурированных данных.

### Q: Как запустить workflow вручную?
**A:** Добавьте `workflow_dispatch:` в секцию `on:` и используйте кнопку "Run workflow" в веб-интерфейсе.

---

## 🚀 Запуск и выполнение

### Q: Почему мой workflow не запускается?
**A:** Проверьте:
1. Правильность синтаксиса YAML
2. Наличие файла в `.github/workflows/`
3. Настройки триггеров в секции `on:`
4. Права доступа к репозиторию

### Q: Как посмотреть логи выполнения?
**A:** 
1. GitHub → Actions
2. Нажмите на конкретный run
3. Нажмите на job
4. Нажмите на step

### Q: Что означают цвета значков?
**A:**
- 🟢 **Зеленый** - успешное выполнение
- 🔴 **Красный** - ошибка
- 🟡 **Желтый** - выполняется
- ⚪ **Серый** - пропущен

### Q: Как отменить выполняющийся workflow?
**A:** В веб-интерфейсе Actions нажмите "Cancel workflow" рядом с выполняющимся run.

---

## 🐍 Python и зависимости

### Q: Как установить Python в workflow?
**A:** Используйте action `actions/setup-python@v5`:
```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: 3.11
```

### Q: Какие версии Python поддерживаются?
**A:** 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13. Используйте стабильные версии (3.10, 3.11, 3.12).

### Q: Как установить зависимости из requirements.txt?
**A:**
```yaml
- name: Install dependencies
  run: pip install -r requirements.txt
```

### Q: Как ускорить установку зависимостей?
**A:** Используйте кэширование:
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

---

## 🔄 Матрицы и стратегии

### Q: Что такое матрица в GitHub Actions?
**A:** Матрица позволяет запустить один job несколько раз с разными параметрами (например, разные версии Python).

### Q: Как создать матрицу Python версий?
**A:**
```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11, 3.12]
```

### Q: Как использовать переменные матрицы?
**A:** Используйте `${{ matrix.python-version }}`:
```yaml
- name: Setup Python ${{ matrix.python-version }}
  uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
```

### Q: Сколько jobs создаст матрица?
**A:** Количество элементов в каждом измерении матрицы. Например, `[3.9, 3.10, 3.11]` создаст 3 jobs.

---

## 🧹 Управление и очистка

### Q: Как удалить старые workflow runs?
**A:** 
1. GitHub → Actions
2. Нажмите "..." рядом с run
3. Выберите "Delete workflow run"

### Q: Как настроить автоматическую очистку?
**A:**
1. Settings → Actions → General
2. Artifact and log retention:
   - Days to keep artifacts: 1
   - Days to keep logs: 1

### Q: Как ограничить количество одновременных runs?
**A:**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Q: Как добавить таймаут для job?
**A:**
```yaml
jobs:
  test:
    timeout-minutes: 10
```

---

## 🔐 Безопасность и секреты

### Q: Что такое GitHub Secrets?
**A:** Безопасное хранилище для чувствительных данных (пароли, токены, ключи API).

### Q: Как создать секрет?
**A:**
1. Settings → Secrets and variables → Actions
2. New repository secret
3. Введите имя и значение

### Q: Как использовать секрет в workflow?
**A:**
```yaml
- name: Use secret
  env:
    API_KEY: ${{ secrets.API_KEY }}
  run: echo "Using API key"
```

### Q: Можно ли видеть секреты в логах?
**A:** Нет, GitHub автоматически скрывает секреты в логах.

---

## 🐛 Отладка и проблемы

### Q: Как найти ошибку в логах?
**A:**
1. Найдите красный значок ❌
2. Нажмите на failed step
3. Ищите строки с "Error:" или "Failed:"

### Q: Что делать при ошибке "Python version not found"?
**A:** Используйте существующую версию Python (3.10, 3.11, 3.12). Не используйте 3.1 или другие несуществующие версии.

### Q: Что делать при ошибке "Permission denied"?
**A:** Добавьте права в workflow:
```yaml
permissions:
  contents: read
  actions: write
```

### Q: Как добавить отладочную информацию?
**A:**
```yaml
- name: Debug info
  run: |
    echo "OS: $RUNNER_OS"
    echo "Python: $(python --version)"
    echo "Directory: $(pwd)"
    ls -la
```

---

## ⚡ Оптимизация

### Q: Как ускорить выполнение workflow?
**A:**
1. Используйте кэширование зависимостей
2. Уменьшите количество шагов
3. Используйте параллельные jobs
4. Оптимизируйте размер кода

### Q: Как измерить время выполнения?
**A:**
```yaml
- name: Start timer
  run: echo "::set-output name=start_time::$(date +%s)"
  id: timer_start

# ... ваши steps ...

- name: End timer
  run: |
    end_time=$(date +%s)
    duration=$((end_time - ${{ steps.timer_start.outputs.start_time }}))
    echo "Completed in $duration seconds"
```

### Q: Как кэшировать pip зависимости?
**A:**
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

---

## 🔗 Интеграции

### Q: Как отправить уведомление в Slack?
**A:**
```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: "Workflow ${{ job.status }}"
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Q: Как отправить уведомление в Telegram?
**A:**
```yaml
- name: Notify Telegram
  run: |
    curl -X POST \
      -H "Content-Type: application/json" \
      -d "{\"chat_id\":\"${{ secrets.TELEGRAM_CHAT_ID }}\",\"text\":\"GitHub Actions: ${{ job.status }}\"}" \
      https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage
```

### Q: Как загрузить артефакты?
**A:**
```yaml
- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: my-app
    path: dist/
```

---

## 📊 Мониторинг

### Q: Как добавить badge в README?
**A:** Добавьте в README.md:
```markdown
![CI](https://github.com/username/repo/workflows/CI/badge.svg)
```

### Q: Как настроить уведомления?
**A:**
1. Settings → Notifications
2. Настройте email уведомления
3. Или используйте интеграции с внешними сервисами

### Q: Как посмотреть статистику workflow?
**A:** В веб-интерфейсе Actions есть вкладка "Insights" с графиками и статистикой.

---

## 🎯 Лучшие практики

### Q: Какие версии Python использовать?
**A:** Используйте стабильные версии: 3.10, 3.11, 3.12. Избегайте 3.1, 3.2 и других несуществующих версий.

### Q: Как структурировать workflow?
**A:**
1. Начните с простых примеров
2. Добавляйте сложность постепенно
3. Используйте понятные названия
4. Добавляйте комментарии

### Q: Когда использовать матрицы?
**A:** Когда нужно протестировать код на:
- Разных версиях Python
- Разных операционных системах
- Разных конфигурациях

### Q: Как избежать дублирования кода?
**A:**
1. Используйте переиспользуемые actions
2. Создавайте собственные actions
3. Используйте шаблоны workflow

---

## 🔧 Продвинутые вопросы

### Q: Как создать собственный Action?
**A:** Создайте файл `action.yml`:
```yaml
name: 'My Action'
description: 'Description'
inputs:
  name:
    description: 'Input name'
    required: true
runs:
  using: 'composite'
  steps:
    - name: Do something
      shell: bash
      run: echo "Hello ${{ inputs.name }}"
```

### Q: Как использовать Docker в workflow?
**A:**
```yaml
- name: Run Docker container
  run: |
    docker build -t my-app .
    docker run my-app
```

### Q: Как передать данные между jobs?
**A:** Используйте артефакты или outputs:
```yaml
- name: Set output
  run: echo "::set-output name=result::success"
  id: my_step

- name: Use output
  run: echo "Result: ${{ steps.my_step.outputs.result }}"
```

---

## 📚 Полезные ресурсы

### Q: Где найти примеры workflow?
**A:**
- [GitHub Actions Examples](https://github.com/actions/starter-workflows)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Q: Как получить помощь?
**A:**
1. GitHub Discussions
2. Stack Overflow
3. GitHub Community
4. GitHub Actions Documentation

### Q: Какие инструменты для тестирования workflow?
**A:**
- [act](https://github.com/nektos/act) - локальное тестирование
- [GitHub Actions VS Code extension](https://marketplace.visualstudio.com/items?itemName=cschleiden.vscode-github-actions)

---

## 🎉 Заключение

Этот FAQ покрывает основные вопросы по GitHub Actions. Помните:

- **Начинайте с простого** - не усложняйте workflow сразу
- **Тестируйте локально** - используйте act для отладки
- **Документируйте** - добавляйте комментарии к сложным частям
- **Мониторьте** - следите за производительностью и ошибками
- **Безопасность** - используйте secrets для чувствительных данных

**Удачи в изучении GitHub Actions!** 🚀 