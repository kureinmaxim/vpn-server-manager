# 🔀 Git & GitHub Guide

> Руководство по работе с Git, GitHub и Pull Requests

---



<!-- ====================================================================== -->
<!-- github_push_guide.md -->
<!-- ====================================================================== -->

# Руководство: как запушить изменения и создать релиз (Git + GitHub CLI)

Ниже — минимальный чек‑лист команд. Команды для macOS (zsh). Для команд с длинным выводом используйте `| cat`.

## Предусловия
- Git и GitHub CLI (`gh`) установлены
- `origin` настроен на SSH:
  ```bash
  git remote -v | cat
  # при необходимости
  git remote set-url origin git@github.com:<user>/<repo>.git
  ```
- Авторизация в gh:
  ```bash
  gh auth status | cat
  # если не авторизованы
  gh auth login
  ```

## 1) Проверить изменения и ветку
```bash
git status --porcelain -b | cat
```

## 2) Коммит
```bash
git add -A && git commit -m "feat(status): SSH stats modal, Docker table, OS display, PNG save, UX" | cat
```

## 3) Пуш
```bash
git push | cat
```
Если репозиторий требует PR — оформите PR через GitHub UI/CLI.

## 4) Релиз c версией из config.json
Версия хранится в `config.json -> app_info.version`.
```bash
VERSION=$(jq -r .app_info.version config.json)
TAG=v$VERSION

# создать релиз (если такого тега ещё нет)
gh release view "$TAG" >/dev/null 2>&1 || \
  gh release create "$TAG" \
    --title "VPN Server Manager v$VERSION" \
    --notes "Release v$VERSION\n\n- SSH Status modal with auto-refresh\n- Docker containers table (robust parsing)\n- OS next to Kernel; tooltips\n- Full-panel PNG save via /snapshot/save\n- html2canvas vendor route\n- Inodes parsing fallback (df -iP)\n- UI/UX improvements" | cat
```
Если `jq` не установлен — задайте тег вручную: `TAG=v3.7.x`.

## 5) Прикрепить артефакт (опционально)
```bash
ASSET_PATH="dist/VPNServerManager-Clean_Installer.dmg"
[ -f "$ASSET_PATH" ] && gh release upload "$TAG" "$ASSET_PATH" --clobber | cat
```

## 6) Проверить релиз
```bash
gh release list --limit 10 | cat
open "https://github.com/<user>/<repo>/releases/tag/$TAG"
```

## Откат релиза/тега
```bash
# удалить релиз
gh release delete "$TAG" --yes | cat
# удалить тег локально и в origin
git tag -d "$TAG" 2>/dev/null || true
git push origin :refs/tags/"$TAG" | cat
```

### One‑liner (если всё настроено)
```bash
VERSION=$(jq -r .app_info.version config.json); TAG=v$VERSION; \
 git add -A && git commit -m "chore(release): v$VERSION" && git push && \
 gh release create "$TAG" --title "VPN Server Manager v$VERSION" --notes "Release v$VERSION" | cat
```


<!-- ====================================================================== -->
<!-- PR_WORKFLOW.md -->
<!-- ====================================================================== -->

# Git Workflow: Полный цикл разработки через Pull Requests

## 📋 Содержание

- [Введение](#введение)
- [Общая схема работы](#общая-схема-работы)
- [Шаг 1: Подготовка к работе](#шаг-1-подготовка-к-работе)
- [Шаг 2: Создание feature-ветки](#шаг-2-создание-feature-ветки)
- [Шаг 3: Разработка и коммиты](#шаг-3-разработка-и-коммиты)
- [Шаг 4: Push изменений](#шаг-4-push-изменений)
- [Шаг 5: Создание Pull Request](#шаг-5-создание-pull-request)
- [Шаг 6: Code Review](#шаг-6-code-review)
- [Шаг 7: Merge Pull Request](#шаг-7-merge-pull-request)
- [Шаг 8: Обновление локальной ветки main](#шаг-8-обновление-локальной-ветки-main)
- [Шаг 9: Очистка](#шаг-9-очистка)
- [Полезные команды](#полезные-команды)
- [Troubleshooting](#troubleshooting)

---

## Введение

Этот документ описывает стандартный workflow разработки через **Pull Requests** (PR) на примере реального проекта **VPN Server Manager**.

**Pull Request** - это запрос на слияние изменений из feature-ветки в основную ветку (main/master). Этот подход позволяет:
- 👀 Просматривать изменения перед их добавлением в основную ветку
- 💬 Обсуждать код с командой (code review)
- ✅ Запускать автоматические проверки (CI/CD)
- 📝 Документировать историю изменений
- 🛡️ Защищать основную ветку от случайных ошибок

---

## Общая схема работы

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN BRANCH (main)                       │
│                  Защищенная основная ветка                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 1. git checkout -b feature/my-feature
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FEATURE BRANCH (feature/my-feature)            │
│                  Ваша рабочая ветка                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 2. Разработка + коммиты
                         │ 3. git push origin feature/my-feature
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   PULL REQUEST на GitHub                    │
│              Запрос на слияние изменений                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 4. Code Review + Approve
                         │ 5. Merge PR
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              MAIN BRANCH (обновленная)                      │
│            Изменения добавлены в main                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Шаг 1: Подготовка к работе

### 1.1. Проверьте текущую ветку

```bash
git branch
```

**Ожидаемый результат:**
```
* main
  feature/old-feature
```

### 1.2. Убедитесь, что main актуальна

```bash
git checkout main
git pull origin main
```

**Ожидаемый результат:**
```
Already on 'main'
Your branch is up to date with 'origin/main'.
```

### 1.3. Проверьте статус

```bash
git status
```

**Ожидаемый результат:**
```
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## Шаг 2: Создание feature-ветки

### 2.1. Создайте новую ветку

**Синтаксис:**
```bash
git checkout -b <имя-ветки>
```

**Пример из нашего проекта:**
```bash
git checkout -b claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

**Результат:**
```
Switched to a new branch 'claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM'
```

### 2.2. Naming conventions для веток

**Хорошие примеры:**
- ✅ `feature/add-user-authentication`
- ✅ `fix/connection-timeout-issue`
- ✅ `docs/update-installation-guide`
- ✅ `refactor/improve-ssh-service`
- ✅ `chore/bump-version-4.0.9`

**Плохие примеры:**
- ❌ `my-branch`
- ❌ `test`
- ❌ `fix`
- ❌ `branch-1`

**Префиксы:**
- `feature/` - новая функциональность
- `fix/` - исправление бага
- `docs/` - документация
- `refactor/` - рефакторинг кода
- `test/` - добавление тестов
- `chore/` - рутинные задачи (обновление версий, зависимостей)

---

## Шаг 3: Разработка и коммиты

### 3.1. Внесите изменения

**Пример из нашего проекта:**

Мы обновили версию до 4.0.9 и создали документацию:

```bash
# Редактируем файлы
vim config.json.example  # Обновили версию
vim app/config.py        # Обновили APP_VERSION
vim app/__init__.py      # Обновили fallback версии
vim README.md            # Добавили release notes
```

Создали новый файл:
```bash
# Создали Структура.md с полной документацией проекта
touch Структура.md
vim Структура.md
```

### 3.2. Проверьте изменения

```bash
git status
```

**Результат:**
```
On branch claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
Changes not staged for commit:
  modified:   README.md
  modified:   app/__init__.py
  modified:   app/config.py
  modified:   config.json.example

Untracked files:
  Структура.md
```

### 3.3. Посмотрите diff

```bash
git diff config.json.example
```

**Результат:**
```diff
-    "version": "4.0.7",
+    "version": "4.0.9",
-    "release_date": "14.10.2025",
+    "release_date": "25.10.2025",
```

### 3.4. Создайте коммит

**Первый коммит (версия):**

```bash
git add README.md app/__init__.py app/config.py config.json.example
git commit -m "chore: bump version to 4.0.9

- Update version in config.json.example to 4.0.9
- Update APP_VERSION in app/config.py to 4.0.9
- Update fallback versions in app/__init__.py to 4.0.9
- Update README.md with v4.0.9 release notes"
```

**Результат:**
```
[claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM dd7b32e] chore: bump version to 4.0.9
 4 files changed, 14 insertions(+), 10 deletions(-)
```

**Второй коммит (документация):**

```bash
git add Структура.md
git commit -m "docs: add comprehensive project structure documentation

- Created Структура.md with full project overview
- Documented all main directories and files
- Described key functions and their implementation
- Added code examples for critical components"
```

**Результат:**
```
[claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM 239a539] docs: add comprehensive project structure documentation
 1 file changed, 1273 insertions(+)
 create mode 100644 Структура.md
```

### 3.5. Best practices для коммитов

#### Структура хорошего commit message:

```
<type>: <краткое описание>

<детальное описание (опционально)>

<footer: ссылки на issues, breaking changes (опционально)>
```

#### Типы коммитов (Conventional Commits):

- `feat:` - новая функциональность
- `fix:` - исправление бага
- `docs:` - изменения в документации
- `style:` - форматирование, пробелы (не влияет на код)
- `refactor:` - рефакторинг кода
- `test:` - добавление тестов
- `chore:` - рутинные задачи (сборка, зависимости)
- `perf:` - улучшение производительности
- `ci:` - изменения в CI/CD

#### Примеры хороших коммитов:

✅ **Хорошие:**
```bash
git commit -m "feat: add user authentication with JWT"
git commit -m "fix: resolve SSH connection timeout issue"
git commit -m "docs: update installation guide for Windows"
git commit -m "refactor: improve SSH connection pooling"
git commit -m "chore: bump version to 4.0.9"
```

❌ **Плохие:**
```bash
git commit -m "updates"
git commit -m "fix"
git commit -m "wip"
git commit -m "changes made"
```

---

## Шаг 4: Push изменений

### 4.1. Push в первый раз

```bash
git push -u origin claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

**Флаги:**
- `-u` (или `--set-upstream`) - устанавливает связь между локальной и удаленной веткой
- Нужен только при первом push

**Результат:**
```
Enumerating objects: 15, done.
Counting objects: 100% (15/15), done.
Delta compression using up to 8 threads
Compressing objects: 100% (9/9), done.
Writing objects: 100% (9/9), 42.50 KiB | 8.50 MiB/s, done.
Total 9 (delta 6), reused 0 (delta 0), pack-reused 0
remote:
remote: Create a pull request for 'claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM' on GitHub by visiting:
remote:      https://github.com/kureinmaxim/vpn-server-manager/pull/new/claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
remote:
To https://github.com/kureinmaxim/vpn-server-manager.git
 * [new branch]      claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM -> claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
branch 'claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM' set up to track 'origin/claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM'.
```

**⚠️ Важно:** GitHub показывает прямую ссылку для создания PR!

### 4.2. Push дополнительных изменений

После первого push с `-u`, для последующих коммитов можно использовать:

```bash
git push
```

Это автоматически запушит в связанную удаленную ветку.

### 4.3. Проверка push

```bash
git log --oneline -3
```

**Результат:**
```
239a539 docs: add comprehensive project structure documentation
dd7b32e chore: bump version to 4.0.9
21c9625 Release v4.0.5: Bug fixes and improvements
```

---

## Шаг 5: Создание Pull Request

### 5.1. Способ 1: Через прямую ссылку (самый простой)

GitHub показывает ссылку после push:

```
https://github.com/kureinmaxim/vpn-server-manager/pull/new/claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

**Или используйте шаблон:**
```
https://github.com/<username>/<repo>/compare/main...<branch-name>
```

**Наш пример:**
```
https://github.com/kureinmaxim/vpn-server-manager/compare/main...claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

### 5.2. Способ 2: Через веб-интерфейс GitHub

1. Откройте репозиторий: `https://github.com/kureinmaxim/vpn-server-manager`
2. Нажмите на вкладку **"Pull requests"**
3. Нажмите **"New pull request"**
4. Выберите ветки:
   - **base:** `main` ← куда сливаем
   - **compare:** `claude/project-structure-overview-...` ← откуда сливаем
5. Нажмите **"Create pull request"**

### 5.3. Заполнение формы PR

#### **Title (Заголовок)**

Следуйте тому же формату, что и commit messages:

**Наш пример:**
```
feat: update to version 4.0.9 and add project structure documentation
```

#### **Description (Описание)**

Подробное описание изменений:

**Наш пример:**
```markdown
## 📋 Изменения

### Version Bump to 4.0.9
- Обновлена версия в `config.json.example` до 4.0.9
- Обновлен `APP_VERSION` в `app/config.py`
- Обновлены fallback версии в `app/__init__.py`
- Добавлены release notes в `README.md`

### Новая документация
- ✨ Создан файл `Структура.md` с полным описанием проекта (1273 строки)
- 📁 Документированы все основные директории
- 💻 Описаны ключевые функции с примерами кода
- 🔧 Задокументированы Service Layer, Routes, Models
- 🛡️ Описаны механизмы безопасности
- 🧪 Добавлена информация о тестировании

## 📊 Статистика
- **Файлов изменено:** 5
- **Добавлено:** 1287 строк
- **Удалено:** 10 строк
- **Коммитов:** 2

## ✅ Чеклист
- [x] Версия обновлена во всех файлах
- [x] Документация полная и актуальная
- [x] Все файлы закоммичены
- [x] Ветка запушена

## 🎯 Тип изменений
- [ ] Bug fix
- [x] New feature
- [x] Documentation
- [ ] Breaking change

## 🔗 Связанные issues
Closes #123 (если применимо)
```

**Шаблон для описания PR:**
```markdown
## Описание
Краткое описание изменений

## Изменения
- Изменение 1
- Изменение 2
- Изменение 3

## Тип PR
- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Refactoring

## Чеклист
- [ ] Код протестирован
- [ ] Документация обновлена
- [ ] Нет конфликтов с main
- [ ] CI/CD проходит
```

### 5.4. Создание PR

Нажмите кнопку **"Create pull request"**

**Результат:** PR создан! Вы увидите страницу с:
- Номером PR (например, #8)
- Статусом (Open)
- Вкладками: Conversation, Commits, Files changed, Checks

---

## Шаг 6: Code Review

### 6.1. Просмотр изменений

Перейдите на вкладку **"Files changed"**

**Что вы увидите:**

```diff
config.json.example
+    "version": "4.0.9",      (зеленым - добавлено)
-    "version": "4.0.7",      (красным - удалено)

Структура.md (новый файл)
+ # Структура проекта VPN Server Manager v4.0.9
+ ...
+ (1273 строки добавлены)
```

### 6.2. Одобрение PR (Approve)

Если у вас включена защита ветки (branch protection), требующая review:

**Шаги:**
1. На вкладке **"Files changed"**
2. Справа вверху нажмите **"Review changes"**
3. Выберите **"Approve"** ⭐
4. Добавьте комментарий: "LGTM (Looks Good To Me) - готово к мерджу"
5. Нажмите **"Submit review"**

**Результат:**
```
✓ Review approved by kureinmaxim
```

### 6.3. Типы review

- **Comment** - просто комментарий без одобрения
- **Approve** - одобрение изменений ✅
- **Request changes** - запрос на изменения ❌

### 6.4. Добавление комментариев к коду

Можно оставлять комментарии к конкретным строкам:
1. Наведите курсор на номер строки
2. Нажмите на появившийся значок "+"
3. Напишите комментарий
4. Нажмите **"Add single comment"** или **"Start a review"**

---

## Шаг 7: Merge Pull Request

### 7.1. Проверка перед мерджем

Убедитесь, что:
- ✅ Все проверки (checks) прошли успешно
- ✅ Нет конфликтов (conflicts)
- ✅ PR одобрен (approved)
- ✅ Ветка актуальна с main

**Статус должен быть:**
```
✓ All checks have passed
✓ This branch has no conflicts with the base branch
✓ Review approved
```

### 7.2. Типы мерджа

GitHub предлагает 3 варианта:

#### **1. Merge commit (рекомендуется)**
```
Создает merge commit в main
История сохраняется полностью
```

**Результат в истории:**
```
* 78464a7 Merge pull request #8 from kureinmaxim/claude/project-structure...
|\
| * 239a539 docs: add comprehensive project structure documentation
| * dd7b32e chore: bump version to 4.0.9
|/
* 21c9625 Release v4.0.5: Bug fixes and improvements
```

#### **2. Squash and merge**
```
Объединяет все коммиты в один
История упрощается
```

**Результат:**
```
* abc1234 feat: update to version 4.0.9 and add project structure documentation
* 21c9625 Release v4.0.5: Bug fixes and improvements
```

#### **3. Rebase and merge**
```
Перебазирует коммиты на main
Линейная история без merge commit
```

**Результат:**
```
* 239a539 docs: add comprehensive project structure documentation
* dd7b32e chore: bump version to 4.0.9
* 21c9625 Release v4.0.5: Bug fixes and improvements
```

### 7.3. Выполнение мерджа

**Наш пример (Merge commit):**

1. Нажмите **"Merge pull request"**
2. Подтвердите: **"Confirm merge"**
3. Опционально: добавьте комментарий к merge commit

**Результат:**
```
Pull request successfully merged and closed

You're all set—the claude/project-structure-overview branch
can be safely deleted.

[Delete branch]
```

### 7.4. Статус после мерджа

- **PR статус:** Merged (фиолетовый бейдж)
- **Ветка:** Может быть удалена
- **Main:** Обновлена с новыми изменениями

**Merge commit в нашем проекте:**
```
78464a7 Merge pull request #8 from kureinmaxim/claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

---

## Шаг 8: Обновление локальной ветки main

### 8.1. Переключитесь на main

```bash
git checkout main
```

**Результат:**
```
Switched to branch 'main'
Your branch is behind 'origin/main' by 3 commits.
```

### 8.2. Подтяните изменения

```bash
git pull origin main
```

**Результат:**
```
Updating 21c9625..78464a7
Fast-forward
 README.md           |    6 +-
 app/__init__.py     |    8 +-
 app/config.py       |    4 +-
 config.json.example |    6 +-
 Структура.md        | 1273 ++++++++++++++++++++++++++++++++++
 5 files changed, 1287 insertions(+), 10 deletions(-)
 create mode 100644 Структура.md
```

### 8.3. Проверка

```bash
git log --oneline -3
```

**Результат:**
```
78464a7 Merge pull request #8 from kureinmaxim/claude/project-structure...
239a539 docs: add comprehensive project structure documentation
dd7b32e chore: bump version to 4.0.9
```

Проверьте, что файлы обновлены:

```bash
ls -la | grep Структура
```

**Результат:**
```
-rw-r--r-- 1 user user 43493 Oct 25 17:38 Структура.md
```

```bash
grep "v4.0.9" README.md | head -2
```

**Результат:**
```
# VPN Server Manager v4.0.9
### v4.0.9 (25 октября 2025)
```

✅ Отлично! Все изменения теперь в вашей локальной main.

---

## Шаг 9: Очистка

### 9.1. Удаление локальной ветки

После успешного мерджа feature-ветка больше не нужна:

```bash
git branch -d claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

**Результат:**
```
Deleted branch claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM (was 239a539).
```

**⚠️ Важно:** Используйте `-d` (не `-D`), чтобы Git проверил, что ветка смержена.

### 9.2. Удаление удаленной ветки (опционально)

GitHub обычно предлагает удалить ветку автоматически после мерджа.

Вручную через Git:
```bash
git push origin --delete claude/project-structure-overview-011CUUGry576hqpqMdvYJfnM
```

Или через GitHub веб-интерфейс:
1. Откройте закрытый PR
2. Нажмите **"Delete branch"**

### 9.3. Проверка чистоты

```bash
git branch -a
```

**Результат:**
```
* main
  remotes/origin/main
```

### 9.4. Синхронизация списка веток

Удалите ссылки на удаленные ветки:

```bash
git fetch --prune
```

или короче:

```bash
git fetch -p
```

---

## Полезные команды

### Просмотр информации

```bash
# Текущая ветка
git branch

# Все ветки (включая удаленные)
git branch -a

# Статус
git status

# История коммитов (кратко)
git log --oneline -10

# График веток
git log --oneline --graph --all --decorate

# Изменения в конкретном файле
git diff README.md

# Сравнение веток
git diff main...feature/my-branch

# Файлы, измененные между ветками
git diff --stat main...feature/my-branch
```

### Работа с ветками

```bash
# Создать и переключиться
git checkout -b feature/new-feature

# Просто переключиться
git checkout main

# Переименовать текущую ветку
git branch -m new-branch-name

# Удалить локальную ветку
git branch -d feature/old-feature

# Принудительно удалить (если не смержена)
git branch -D feature/old-feature
```

### Работа с коммитами

```bash
# Добавить файлы
git add file.txt
git add .  # все файлы
git add *.md  # все .md файлы

# Коммит
git commit -m "feat: add new feature"

# Коммит всех измененных файлов (без новых)
git commit -am "fix: resolve issue"

# Изменить последний коммит
git commit --amend -m "new message"

# Отменить последний коммит (но сохранить изменения)
git reset --soft HEAD~1

# Посмотреть конкретный коммит
git show 239a539
```

### Синхронизация с удаленным репозиторием

```bash
# Загрузить изменения (не применяя)
git fetch origin

# Загрузить и применить
git pull origin main

# Запушить
git push origin feature/my-branch

# Запушить с установкой upstream
git push -u origin feature/my-branch

# Форс-пуш (ОСТОРОЖНО!)
git push --force origin feature/my-branch
```

### Отмена изменений

```bash
# Отменить изменения в файле (до add)
git checkout -- file.txt

# Убрать файл из staging (после add)
git reset HEAD file.txt

# Отменить последний коммит (удалив изменения)
git reset --hard HEAD~1

# Вернуться к конкретному коммиту
git reset --hard abc1234
```

### Работа с удаленными ветками

```bash
# Список удаленных веток
git branch -r

# Обновить список удаленных веток
git fetch --prune

# Получить удаленную ветку
git checkout -b feature/test origin/feature/test

# Удалить удаленную ветку
git push origin --delete feature/old-branch
```

### Полезные alias

Добавьте в `~/.gitconfig`:

```ini
[alias]
    st = status
    co = checkout
    br = branch
    ci = commit
    last = log -1 HEAD
    unstage = reset HEAD --
    visual = log --oneline --graph --all --decorate
    amend = commit --amend --no-edit
```

Использование:
```bash
git st  # вместо git status
git co main  # вместо git checkout main
git visual  # красивый граф веток
```

---

## Troubleshooting

### Проблема: Конфликты при мердже

**Симптомы:**
```
CONFLICT (content): Merge conflict in README.md
Automatic merge failed; fix conflicts and then commit the result.
```

**Решение:**

1. Откройте файл с конфликтом:
```bash
vim README.md
```

2. Найдите маркеры конфликта:
```
<<<<<<< HEAD
Версия из main
=======
Версия из вашей ветки
>>>>>>> feature/my-branch
```

3. Исправьте конфликт вручную, оставив нужную версию

4. Удалите маркеры `<<<<<<<`, `=======`, `>>>>>>>`

5. Добавьте разрешенный файл:
```bash
git add README.md
git commit -m "fix: resolve merge conflict in README.md"
```

### Проблема: Branch protection rules

**Симптомы:**
```
Unable to merge. A review is required.
```

**Решение:**

**Вариант 1:** Одобрите PR через "Review changes" → "Approve"

**Вариант 2:** Используйте admin override (если вы админ):
- Поставьте галочку "Use your administrator privileges to merge"

**Вариант 3:** Временно отключите branch protection:
- Settings → Branches → Edit rule → Снимите "Require approvals"

### Проблема: Ошибка при push

**Симптомы:**
```
error: failed to push some refs to 'origin'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

**Решение:**

1. Подтяните изменения:
```bash
git pull --rebase origin feature/my-branch
```

2. Разрешите конфликты (если есть)

3. Запуште снова:
```bash
git push origin feature/my-branch
```

### Проблема: Случайно закоммитили в main

**Решение:**

1. Создайте новую ветку из текущего состояния:
```bash
git branch feature/emergency-save
```

2. Откатите main:
```bash
git reset --hard origin/main
```

3. Переключитесь на новую ветку:
```bash
git checkout feature/emergency-save
```

4. Запуште и создайте PR:
```bash
git push -u origin feature/emergency-save
```

### Проблема: Нужно изменить commit message

**Последний коммит:**
```bash
git commit --amend -m "новое сообщение"
```

**Коммит уже запушен:**
```bash
git commit --amend -m "новое сообщение"
git push --force origin feature/my-branch
```

⚠️ **Осторожно с --force!** Используйте только на своих feature-ветках!

### Проблема: Забыли добавить файлы в коммит

**Решение:**

1. Добавьте файлы:
```bash
git add forgotten-file.txt
```

2. Измените последний коммит:
```bash
git commit --amend --no-edit
```

3. Форс-пуш (если уже запушили):
```bash
git push --force origin feature/my-branch
```

### Проблема: Нужно удалить чувствительные данные

**Решение:**

⚠️ Если данные уже в истории, используйте:

```bash
# Установите BFG Repo-Cleaner
brew install bfg  # macOS

# Удалите файл из истории
bfg --delete-files passwords.txt

# Или замените строки
bfg --replace-text passwords.txt

# Принудительно запуште
git push --force origin main
```

**Альтернатива:** `git filter-branch` (более сложный)

**Лучше:** Сразу сбросьте ключи/пароли и обновите `.gitignore`!

---

## Заключение

Теперь вы знаете полный цикл разработки через Pull Requests:

```
1. git checkout main
2. git pull origin main
3. git checkout -b feature/new-feature
4. (внесение изменений)
5. git add .
6. git commit -m "feat: add new feature"
7. git push -u origin feature/new-feature
8. (создание PR на GitHub)
9. (review и approve)
10. (merge PR)
11. git checkout main
12. git pull origin main
13. git branch -d feature/new-feature
```

### Ключевые принципы:

✅ **Всегда работайте в feature-ветках**
✅ **Пишите осмысленные commit messages**
✅ **Делайте небольшие, атомарные коммиты**
✅ **Описывайте PR подробно**
✅ **Проводите code review**
✅ **Держите main чистой и защищенной**
✅ **Синхронизируйтесь с main регулярно**
✅ **Удаляйте смерженные ветки**

### Полезные ресурсы:

- [GitHub Docs: Pull Requests](https://docs.github.com/en/pull-requests)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Book](https://git-scm.com/book/en/v2)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

---

**Документ создан на основе реального опыта работы с проектом VPN Server Manager v4.0.9**

*Последнее обновление: 25 октября 2025*
