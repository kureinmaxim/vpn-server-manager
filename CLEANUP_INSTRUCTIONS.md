# 🧹 Инструкция по очистке старых ошибок GitHub Actions

## Быстрая очистка через веб-интерфейс

### 1. **Ручная очистка (рекомендуется)**
1. Перейдите на: https://github.com/kureinmaxim/vpn-server-manager/actions
2. Для каждой ошибки:
   - Нажмите на "..." (три точки) справа
   - Выберите "Delete workflow run"
3. Или массово:
   - Поставьте галочки рядом с ошибками
   - Нажмите "Delete selected" внизу

### 2. **Настройка автоматической очистки**
1. Перейдите в **Settings** репозитория
2. Выберите **Actions → General**
3. В разделе **"Artifact and log retention"**:
   - **Days to keep artifacts**: `1`
   - **Days to keep logs**: `1`
4. Нажмите **"Save"**

## Автоматическая очистка через скрипты

### Подготовка
1. **Создайте GitHub Token**:
   - Перейдите в GitHub → Settings → Developer settings → Personal access tokens
   - Создайте новый token с правами `repo`
   - Скопируйте token

2. **Установите переменную окружения**:
```bash
export GITHUB_TOKEN=your_token_here
```

### Использование скриптов

#### Очистка старых ошибок:
```bash
python clean_workflows.py
```

#### Настройка автоматической очистки:
```bash
python setup_workflow_cleanup.py
```

## Альтернативные способы

### Через GitHub CLI:
```bash
# Авторизация
gh auth login

# Просмотр workflow runs
gh run list

# Удаление конкретного run
gh run delete <run_id>

# Удаление всех неудачных runs
gh run list --status failure --json databaseId | jq -r '.[].databaseId' | xargs -I {} gh run delete {}
```

### Через API напрямую:
```bash
# Получить список runs
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/kureinmaxim/vpn-server-manager/actions/runs

# Удалить конкретный run
curl -X DELETE -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/kureinmaxim/vpn-server-manager/actions/runs/{run_id}
```

## Настройки для предотвращения накопления ошибок

### 1. **Ограничение количества runs**
В файле `.github/workflows/ci.yml` добавьте:
```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  # Ограничиваем количество одновременных runs
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### 2. **Улучшение стабильности CI**
- Используйте только стабильные версии Python
- Избегайте Windows в CI (если есть проблемы с кодировкой)
- Добавьте таймауты для тестов

### 3. **Мониторинг**
- Настройте уведомления о неудачных builds
- Регулярно проверяйте логи CI/CD
- Используйте badges в README для отображения статуса

## Полезные команды

```bash
# Проверка статуса последних runs
gh run list --limit 10

# Просмотр логов конкретного run
gh run view <run_id>

# Перезапуск неудачного run
gh run rerun <run_id>
```

## Примечания

- **Безопасность**: Никогда не коммитьте токены в код
- **Ограничения**: GitHub API имеет лимиты на количество запросов
- **Резервное копирование**: Важные логи лучше сохранять локально
- **Автоматизация**: Настройте регулярную очистку через GitHub Actions 