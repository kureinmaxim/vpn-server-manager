# Урок 3: Работа с Issues и Pull Requests через GitHub CLI

В этом уроке мы рассмотрим, как эффективно управлять задачами (issues) и запросами на включение изменений (pull requests) с помощью GitHub CLI.

## Работа с Issues

Issues в GitHub используются для отслеживания задач, улучшений, багов и других запросов, связанных с проектом.

### Просмотр списка Issues

```bash
# Просмотр всех открытых issues в текущем репозитории
gh issue list

# Просмотр issues с фильтрацией
gh issue list --assignee @me  # Назначенные вам
gh issue list --author @me    # Созданные вами
gh issue list --label bug     # С меткой "bug"
gh issue list --state closed  # Закрытые issues
```

### Создание нового Issue

```bash
# Интерактивное создание issue
gh issue create

# Создание issue с параметрами
gh issue create --title "Проблема с авторизацией" --body "При входе через Google возникает ошибка 403" --assignee @me --label bug
```

### Просмотр конкретного Issue

```bash
# Просмотр issue по номеру
gh issue view 42

# Просмотр в браузере
gh issue view 42 --web
```

### Закрытие и повторное открытие Issue

```bash
# Закрытие issue
gh issue close 42

# Закрытие с комментарием
gh issue close 42 --comment "Исправлено в коммите abc123"

# Повторное открытие
gh issue reopen 42
```

### Комментирование Issue

```bash
gh issue comment 42 --body "Я воспроизвел эту ошибку на Windows 11"
```

### Редактирование Issue

```bash
# Изменение заголовка
gh issue edit 42 --title "Обновленный заголовок"

# Изменение тела issue
gh issue edit 42 --body "Обновленное описание проблемы"

# Изменение меток
gh issue edit 42 --add-label "priority-high" --remove-label "priority-low"

# Изменение исполнителя
gh issue edit 42 --add-assignee username --remove-assignee another-user
```

## Работа с Pull Requests

Pull Requests (PR) позволяют вам предложить изменения, которые другие участники могут рассмотреть и включить в основную ветку проекта.

### Просмотр списка Pull Requests

```bash
# Просмотр всех открытых PR в текущем репозитории
gh pr list

# Просмотр PR с фильтрацией
gh pr list --assignee @me     # Назначенные вам
gh pr list --author @me       # Созданные вами
gh pr list --base main        # Нацеленные на ветку main
gh pr list --state closed     # Закрытые PR
gh pr list --label enhancement # С меткой "enhancement"
```

### Создание нового Pull Request

```bash
# Создание PR из текущей ветки в main
gh pr create

# Создание PR с параметрами
gh pr create --title "Добавлена функция авторизации через Apple" --body "Реализована авторизация через Apple ID согласно issue #123" --base main
```

### Просмотр конкретного Pull Request

```bash
# Просмотр PR по номеру
gh pr view 42

# Просмотр в браузере
gh pr view 42 --web

# Просмотр diff изменений
gh pr diff 42
```

### Проверка Pull Request локально

```bash
# Скачивание PR для локальной проверки
gh pr checkout 42

# Просмотр изменений в PR
gh pr diff
```

### Комментирование Pull Request

```bash
gh pr comment 42 --body "Выглядит хорошо, но нужно добавить тесты"
```

### Одобрение Pull Request

```bash
# Одобрение PR
gh pr review 42 --approve

# Одобрение с комментарием
gh pr review 42 --approve --body "Код выглядит отлично, одобряю!"
```

### Запрос изменений в Pull Request

```bash
gh pr review 42 --request-changes --body "Пожалуйста, исправьте форматирование и добавьте документацию"
```

### Слияние Pull Request

```bash
# Простое слияние
gh pr merge 42

# Слияние с опциями
gh pr merge 42 --squash --delete-branch
```

Опции слияния:
- `--merge` — стандартное слияние с сохранением всех коммитов (по умолчанию)
- `--squash` — объединение всех коммитов в один
- `--rebase` — перебазирование коммитов
- `--delete-branch` — удаление ветки после слияния

### Закрытие Pull Request без слияния

```bash
gh pr close 42
```

## Практические примеры

### Пример 1: Полный цикл работы с Issue и PR

```bash
# Создаем issue для отслеживания задачи
gh issue create --title "Добавить темную тему" --body "Необходимо реализовать поддержку темной темы для улучшения UX" --label enhancement

# Предположим, что создан issue #5
# Создаем ветку для работы над задачей
git checkout -b feature/dark-theme

# ... Вносим изменения в код ...

# Коммитим изменения
git add .
git commit -m "Добавлена поддержка темной темы"

# Отправляем изменения в удаленный репозиторий
git push -u origin feature/dark-theme

# Создаем PR, связывая его с issue #5
gh pr create --title "Реализация темной темы" --body "Closes #5" --base main

# Предположим, что создан PR #10
# После получения комментариев, вносим дополнительные изменения

# ... Вносим изменения в код ...

# Коммитим и отправляем дополнительные изменения
git add .
git commit -m "Исправления по комментариям к PR"
git push

# Проверяем статус PR
gh pr view 10

# После одобрения, сливаем PR
gh pr merge 10 --squash --delete-branch
```

### Пример 2: Управление несколькими Issues

```bash
# Создаем несколько issues для отслеживания задач в проекте
gh issue create --title "Баг в форме регистрации" --body "Форма не валидирует email" --label bug
gh issue create --title "Оптимизировать загрузку изображений" --body "Изображения загружаются слишком долго" --label performance
gh issue create --title "Добавить интеграцию с Twitter" --body "Добавить возможность шеринга в Twitter" --label enhancement

# Просматриваем все открытые issues
gh issue list

# Назначаем себе issue с багом
gh issue edit 7 --add-assignee @me

# Добавляем комментарий о прогрессе
gh issue comment 7 --body "Я работаю над этим, проблема связана с регулярным выражением"

# Закрываем issue после исправления
gh issue close 7 --comment "Исправлено в PR #12"
```

## Заключение

GitHub CLI предоставляет мощные инструменты для управления issues и pull requests, что позволяет эффективно организовать рабочий процесс разработки прямо из командной строки. Это особенно полезно для тех, кто предпочитает не переключаться между терминалом и браузером.

В следующем уроке мы рассмотрим работу с GitHub Actions и расширенные возможности GitHub CLI. 