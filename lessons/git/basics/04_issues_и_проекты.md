# Урок 4: Issues и Проекты в GitHub

В этом уроке мы рассмотрим работу с Issues и Проектами в GitHub — инструментами для отслеживания задач, ошибок и организации рабочего процесса.

## Что такое GitHub Issues?

GitHub Issues — это встроенный трекер задач, который позволяет отслеживать и управлять работой над проектом. Issues могут представлять собой задачи, улучшения, ошибки или любые другие элементы, требующие внимания.

### Основные преимущества Issues:

- **Централизованное отслеживание**: все задачи хранятся в одном месте
- **Интеграция с кодом**: можно связывать issues с коммитами и pull requests
- **Совместная работа**: обсуждение задач с участниками проекта
- **Организация**: использование меток, вех и назначений
- **Автоматизация**: интеграция с GitHub Actions и другими инструментами

## Работа с Issues

### Создание нового Issue

#### Через веб-интерфейс GitHub:

1. Перейдите на страницу репозитория
2. Нажмите на вкладку "Issues"
3. Нажмите зеленую кнопку "New issue"
4. Выберите шаблон (если настроены) или "Open a blank issue"
5. Заполните форму:
   - **Заголовок**: краткое описание проблемы или задачи
   - **Описание**: подробное объяснение, включая шаги воспроизведения для ошибок
   - **Метки**, **Проекты**, **Исполнители** и т.д. (опционально)
6. Нажмите "Submit new issue"

#### Через GitHub CLI:

```bash
# Создание нового issue
gh issue create --title "Bug in login form" --body "The login form doesn't validate email addresses correctly"

# Создание issue с метками и назначением
gh issue create --title "Add dark mode" --body "Implement dark mode for better UX" --label "enhancement,ui" --assignee "@me"
```

### Просмотр и поиск Issues

#### Через веб-интерфейс:

1. Перейдите на вкладку "Issues" в репозитории
2. Используйте фильтры в верхней части страницы:
   - **Open/Closed**: статус issue
   - **Author**: создатель issue
   - **Label**: метки
   - **Projects**: связанные проекты
   - **Milestones**: связанные вехи
   - **Assignee**: назначенные исполнители

#### Через GitHub CLI:

```bash
# Просмотр всех открытых issues
gh issue list

# Поиск issues с фильтрацией
gh issue list --label bug --assignee "@me"
gh issue list --author octocat --state closed
gh issue list --milestone "v1.0"

# Просмотр конкретного issue
gh issue view 42
gh issue view 42 --web  # Открыть в браузере
```

### Управление Issues

#### Редактирование Issue

```bash
# Через GitHub CLI
gh issue edit 42 --title "Updated title" --body "Updated description"
gh issue edit 42 --add-label "priority-high" --remove-label "priority-low"
gh issue edit 42 --add-assignee "@me" --remove-assignee octocat

# Через веб-интерфейс
# Нажмите на "..." в правом верхнем углу issue и выберите "Edit"
```

#### Закрытие и повторное открытие Issue

```bash
# Закрытие issue
gh issue close 42
gh issue close 42 --comment "Fixed in PR #123"

# Повторное открытие issue
gh issue reopen 42
```

#### Связывание Issues с Pull Requests

Issues можно автоматически закрывать при слиянии Pull Request, используя специальные ключевые слова в сообщении коммита или описании PR:

- `close`, `closes`, `closed`
- `fix`, `fixes`, `fixed`
- `resolve`, `resolves`, `resolved`

Примеры:
- `Fixes #42` — закроет issue #42 при слиянии
- `Resolves #24, fixes #33` — закроет оба issue

```bash
# Создание PR, который закроет issue при слиянии
gh pr create --title "Add search feature" --body "Implements search functionality. Closes #42"
```

### Шаблоны Issues

Шаблоны помогают стандартизировать формат создаваемых issues и собирать нужную информацию.

#### Создание шаблонов Issues:

1. Создайте директорию `.github/ISSUE_TEMPLATE/` в корне репозитория
2. Создайте файлы шаблонов в формате Markdown или YAML

Пример шаблона bug_report.md:

```markdown
---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Описание ошибки**
Четкое и краткое описание ошибки.

**Шаги воспроизведения**
1. Перейти к '...'
2. Нажать на '....'
3. Прокрутить до '....'
4. Увидеть ошибку

**Ожидаемое поведение**
Четкое и краткое описание того, что вы ожидали.

**Скриншоты**
Если применимо, добавьте скриншоты для объяснения проблемы.

**Окружение:**
 - ОС: [например, iOS]
 - Браузер: [например, chrome, safari]
 - Версия: [например, 22]

**Дополнительная информация**
Добавьте любую другую информацию о проблеме здесь.
```

## Организация Issues с помощью меток и вех

### Метки (Labels)

Метки помогают категоризировать issues и pull requests.

#### Стандартные метки GitHub:

- `bug`: ошибка в коде
- `documentation`: улучшение документации
- `duplicate`: дубликат другого issue
- `enhancement`: новая функция или улучшение
- `good first issue`: хорошая задача для новичков
- `help wanted`: нужна дополнительная помощь
- `invalid`: issue не является валидным
- `question`: вопрос или запрос информации
- `wontfix`: работа не будет продолжена

#### Управление метками:

```bash
# Создание новой метки
gh api repos/{owner}/{repo}/labels -X POST -f name="priority-high" -f color="d73a4a" -f description="High priority issue"

# Добавление метки к issue
gh issue edit 42 --add-label "priority-high"

# Удаление метки с issue
gh issue edit 42 --remove-label "priority-high"
```

### Вехи (Milestones)

Вехи группируют issues и pull requests в рамках определенного проекта, функции или периода времени.

#### Создание вехи:

1. Перейдите на вкладку "Issues"
2. Нажмите "Milestones"
3. Нажмите "New milestone"
4. Заполните форму:
   - **Title**: название вехи (например, "v1.0")
   - **Due date**: дата завершения (опционально)
   - **Description**: описание вехи (опционально)

#### Управление вехами через API:

```bash
# Создание новой вехи
gh api repos/{owner}/{repo}/milestones -X POST -f title="v1.0" -f due_on="2023-12-31T00:00:00Z" -f description="First stable release"

# Добавление issue к вехе
gh issue edit 42 --milestone "v1.0"
```

## Проекты GitHub

GitHub Projects — это инструмент для организации и приоритизации работы. Проекты используют доски в стиле канбан для визуализации рабочего процесса.

### Типы проектов в GitHub

1. **Классические проекты** (Classic Projects):
   - Привязаны к конкретному репозиторию
   - Базовая функциональность

2. **Проекты (бета)** (Projects Beta):
   - Новый опыт работы с проектами
   - Могут охватывать несколько репозиториев
   - Расширенная настройка представлений и полей

### Создание проекта

#### Классический проект:

1. Перейдите на страницу репозитория
2. Нажмите на вкладку "Projects"
3. Нажмите "Create a project"
4. Выберите шаблон (None, Basic kanban, Automated kanban)
5. Введите название и описание
6. Нажмите "Create project"

#### Проект (бета):

1. Перейдите на страницу профиля или организации
2. Нажмите на вкладку "Projects"
3. Нажмите "New project"
4. Выберите шаблон
5. Введите название
6. Нажмите "Create"

### Настройка доски проекта

#### Колонки и статусы:

Для классических проектов:
1. Нажмите "+ Add column"
2. Введите название колонки (например, "To Do", "In Progress", "Done")
3. Настройте автоматизацию (опционально)

Для проектов (бета):
1. Нажмите "+" в верхнем правом углу
2. Выберите "Single select field"
3. Введите название поля (например, "Status")
4. Добавьте значения (например, "To Do", "In Progress", "Done")

### Добавление Issues в проект

#### Через веб-интерфейс:

1. Откройте issue
2. В правой панели нажмите на "Projects"
3. Выберите проект из выпадающего списка

Или:

1. Откройте проект
2. Нажмите "+ Add item"
3. Выберите issue из списка или создайте новый

#### Через GitHub CLI (для классических проектов):

```bash
# Добавление issue в проект
gh api repos/{owner}/{repo}/projects/cards -X POST -f column_id=column_id -f content_id=issue_id -f content_type="Issue"
```

### Управление проектом

#### Перемещение карточек:

- Перетащите карточку из одной колонки в другую
- Используйте автоматизацию для автоматического перемещения карточек

#### Фильтрация и сортировка:

1. Нажмите на иконку фильтра
2. Выберите критерии фильтрации (метки, исполнители и т.д.)
3. Нажмите "Apply"

#### Представления (для проектов бета):

1. Нажмите "+ New view"
2. Выберите тип представления (Board, Table, Roadmap)
3. Настройте представление по своему усмотрению

## Автоматизация рабочего процесса

### Автоматизация в классических проектах

1. Нажмите на "..." в заголовке колонки
2. Выберите "Manage automation"
3. Настройте правила:
   - Автоматически перемещать новые issues в колонку
   - Автоматически перемещать закрытые issues в колонку
   - Автоматически перемещать новые pull requests в колонку
   - Автоматически перемещать слитые pull requests в колонку

### Автоматизация с GitHub Actions

Пример рабочего процесса для автоматического добавления меток к issues:

```yaml
# .github/workflows/issue-labeler.yml
name: Issue Labeler

on:
  issues:
    types: [opened, edited]

jobs:
  label-issues:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v6
        with:
          script: |
            const issue = context.payload.issue;
            const title = issue.title.toLowerCase();
            
            if (title.includes('bug') || title.includes('error') || title.includes('problem')) {
              github.rest.issues.addLabels({
                issue_number: issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                labels: ['bug']
              });
            }
            
            if (title.includes('feature') || title.includes('enhancement')) {
              github.rest.issues.addLabels({
                issue_number: issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                labels: ['enhancement']
              });
            }
```

## Практические примеры

### Пример 1: Настройка рабочего процесса для нового проекта

```bash
# 1. Создание шаблонов issues
mkdir -p .github/ISSUE_TEMPLATE
cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOF'
---
name: Bug Report
about: Report a bug to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Описание ошибки**
Четкое и краткое описание ошибки.

**Шаги воспроизведения**
1. ...
2. ...
3. ...

**Ожидаемое поведение**
Что должно происходить.

**Скриншоты**
Если применимо, добавьте скриншоты.
EOF

cat > .github/ISSUE_TEMPLATE/feature_request.md << 'EOF'
---
name: Feature Request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Описание функции**
Четкое и краткое описание того, что вы хотите добавить.

**Причина**
Почему эта функция нужна.

**Альтернативы**
Описание альтернативных решений, которые вы рассмотрели.
EOF

# 2. Создание пользовательских меток
gh api repos/{owner}/{repo}/labels -X POST -f name="priority-high" -f color="d73a4a" -f description="High priority issue"
gh api repos/{owner}/{repo}/labels -X POST -f name="priority-medium" -f color="fbca04" -f description="Medium priority issue"
gh api repos/{owner}/{repo}/labels -X POST -f name="priority-low" -f color="0e8a16" -f description="Low priority issue"
gh api repos/{owner}/{repo}/labels -X POST -f name="documentation" -f color="0075ca" -f description="Documentation updates"
gh api repos/{owner}/{repo}/labels -X POST -f name="good-first-issue" -f color="7057ff" -f description="Good for newcomers"

# 3. Создание вехи для первого релиза
gh api repos/{owner}/{repo}/milestones -X POST -f title="v1.0" -f due_on="2023-12-31T00:00:00Z" -f description="First stable release"

# 4. Создание первых issues
gh issue create --title "Set up project structure" --body "Create initial directory structure and configuration files" --label "priority-high" --milestone "v1.0"
gh issue create --title "Write README.md" --body "Create comprehensive README with installation and usage instructions" --label "documentation,good-first-issue" --milestone "v1.0"
gh issue create --title "Implement user authentication" --body "Add user login and registration functionality" --label "enhancement,priority-high" --milestone "v1.0"
```

### Пример 2: Управление ошибкой через issue

```bash
# 1. Создание issue для ошибки
gh issue create --title "[BUG] Login form validation fails" --body "When entering an invalid email format, the form submits without showing an error message. Expected behavior: form should validate email and show error message." --label "bug,priority-high"

# 2. Назначение issue себе
gh issue edit 42 --add-assignee "@me"

# 3. Создание ветки для исправления
git checkout -b fix/login-validation

# 4. Внесение исправлений и коммит
# ... внесение изменений ...
git commit -am "Fix login form validation. Fixes #42"

# 5. Создание PR
gh pr create --title "Fix login form validation" --body "Adds proper email validation to login form. Fixes #42"

# 6. После слияния PR issue будет автоматически закрыт
```

## Лучшие практики для работы с Issues и Проектами

### Для Issues:

1. **Используйте шаблоны**: создавайте шаблоны для различных типов issues
2. **Будьте конкретны**: четко описывайте проблему или задачу
3. **Используйте метки**: категоризируйте issues для легкого поиска
4. **Устанавливайте приоритеты**: используйте метки приоритета или вехи
5. **Связывайте с кодом**: упоминайте коммиты и PR, связанные с issue
6. **Закрывайте неактуальные issues**: поддерживайте список issues в актуальном состоянии

### Для Проектов:

1. **Выбирайте правильный уровень детализации**: не создавайте слишком много или слишком мало колонок
2. **Регулярно обновляйте**: поддерживайте доску проекта в актуальном состоянии
3. **Используйте автоматизацию**: настраивайте автоматические правила для экономии времени
4. **Настраивайте представления**: создавайте разные представления для разных целей
5. **Документируйте процесс**: опишите, как команда должна использовать проект

## Заключение

Issues и Проекты в GitHub — это мощные инструменты для отслеживания задач и организации рабочего процесса. Они позволяют структурировать работу, обеспечивают прозрачность и способствуют эффективному сотрудничеству в команде. Правильное использование этих инструментов значительно повышает продуктивность разработки и качество проекта.

В следующем уроке мы рассмотрим GitHub Actions — инструмент для автоматизации рабочих процессов в репозитории.

## Дополнительные ресурсы

- [GitHub Docs: About Issues](https://docs.github.com/en/github/managing-your-work-on-github/about-issues)
- [GitHub Docs: About Projects](https://docs.github.com/en/github/managing-your-work-on-github/about-project-boards)
- [GitHub Docs: Tracking Issues and Pull Requests](https://docs.github.com/en/github/managing-your-work-on-github/tracking-the-progress-of-your-work-with-project-boards)
- [GitHub Docs: Issue Templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository) 