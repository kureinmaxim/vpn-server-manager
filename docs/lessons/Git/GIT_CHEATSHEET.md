# 🚀 Git Cheatsheet для VPN Server Manager v4.0.0

Быстрая шпаргалка по основным Git командам для работы с проектом.

## 📋 Основные команды

### Инициализация и клонирование
```bash
# Инициализация репозитория
git init

# Клонирование репозитория
git clone https://github.com/username/vpn-server-manager.git
cd vpn-server-manager

# Настройка пользователя
git config user.name "Ваше Имя"
git config user.email "your.email@example.com"
```

### Основной workflow
```bash
# Проверка статуса
git status

# Добавление файлов
git add .                    # Все файлы
git add filename.py          # Конкретный файл
git add -A                   # Все изменения

# Коммит
git commit -m "feat: add new feature"
git commit -am "fix: update version"  # Добавить и закоммитить

# Push
git push                     # В текущую ветку
git push -u origin main      # Первый push
git push origin feature-branch
```

### Работа с ветками
```bash
# Создание и переключение
git checkout -b feature/new-feature
git switch -c feature/new-feature

# Переключение
git checkout main
git switch main

# Список веток
git branch                   # Локальные
git branch -a                # Все
git branch -r                # Удаленные

# Удаление
git branch -d feature-branch
```

### Отмена изменений
```bash
# Отмена в рабочей директории
git checkout -- filename.py
git restore filename.py

# Отмена индексации
git reset HEAD filename.py
git restore --staged filename.py

# Отмена коммита
git reset --soft HEAD~1      # Сохранить изменения
git reset --hard HEAD~1     # Удалить изменения
```

## 🔧 GitHub CLI (gh)

### Аутентификация
```bash
# Вход
gh auth login

# Проверка
gh auth status
```

### Репозитории
```bash
# Создание репозитория
gh repo create vpn-server-manager --public

# Клонирование
gh repo clone username/vpn-server-manager

# Список репозиториев
gh repo list
```

### Pull Requests
```bash
# Создание PR
gh pr create --title "Add feature" --body "Description"

# Список PR
gh pr list

# Просмотр PR
gh pr view 123

# Мерж PR
gh pr merge 123 --merge
```

### Релизы
```bash
# Создание релиза
gh release create v4.0.0 --title "Release v4.0.0" --latest

# С файлами
gh release create v4.0.0 \
  --title "Release v4.0.0" \
  dist/VPNServerManager-Clean_Installer.dmg \
  --latest

# Список релизов
gh release list
```

## 📁 .gitignore для проекта

Наш `.gitignore` уже настроен и включает:

```gitignore
# Python
__pycache__/
*.py[cod]
build/
dist/
*.egg-info/

# Virtual environments
.env
.venv
venv/
env/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Application specific
logs/
uploads/
data/servers.json.enc
data/hints.json
pin_block_state.json

# Security
*.key
*.pem
*.crt
```

## 🚀 Быстрый старт проекта

### 1. Клонирование и настройка
```bash
git clone https://github.com/username/vpn-server-manager.git
cd vpn-server-manager
cp env.example .env
```

### 2. Первый коммит
```bash
git add .
git commit -m "feat: initial commit v4.0.0"
```

### 3. Публикация на GitHub
```bash
# С gh CLI
gh repo create vpn-server-manager --public
git push -u origin main

# Без gh CLI
# Создать репозиторий на GitHub.com
git remote add origin https://github.com/username/vpn-server-manager.git
git push -u origin main
```

## 🏷️ Создание релиза

### С тегом
```bash
git tag -a v4.0.0 -m "Release version 4.0.0"
git push origin v4.0.0
```

### С gh CLI
```bash
gh release create v4.0.0 \
  --title "VPN Server Manager v4.0.0" \
  --notes "Major release with modular architecture" \
  dist/VPNServerManager-Clean_Installer.dmg \
  --latest
```

## 🔄 Ежедневный workflow

### Утром
```bash
git checkout main
git pull origin main
git checkout -b feature/daily-work
```

### Работа
```bash
# ... вносим изменения ...
git add .
git commit -m "feat: add improvements"
git push -u origin feature/daily-work
```

### Вечером
```bash
gh pr create --title "Daily improvements" --body "Description"
```

## 🆘 Экстренные команды

### Отмена последнего push
```bash
git reset --hard HEAD~1
git push --force-with-lease origin main
```

### Очистка репозитория
```bash
git clean -fd
git reset --hard HEAD
```

### Проверка .gitignore
```bash
git status --ignored
git check-ignore filename
```

## 📊 Полезные команды

### Информация
```bash
# История
git log --oneline
git log --graph --oneline --all

# Изменения
git diff
git diff --staged
git diff HEAD~1

# Статистика
git shortlog -sn
git ls-files | xargs wc -l
```

### Очистка
```bash
# Удаление неиспользуемых веток
git branch --merged | grep -v main | xargs -n 1 git branch -d

# Очистка удаленных веток
git remote prune origin
```

---

**💡 Совет**: Используйте `git status` перед каждой операцией для проверки состояния репозитория.

**📖 Подробное руководство**: [GIT_GITHUB_GUIDE.md](GIT_GITHUB_GUIDE.md)
