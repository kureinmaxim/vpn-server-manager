#!/bin/bash

# Скрипт для отката к резервному состоянию
# Использование:
#   ./rollback.sh [backup-branch-name]
#   ./rollback.sh -y [backup-branch-name]   # не задавать вопросы (non-interactive)

set -euo pipefail

echo "🔄 Скрипт отката к резервному состоянию"
echo "========================================"

# Параметры
AUTO_YES=false
BACKUP_BRANCH_DEFAULT="backup/current-state-20250805-103439"
USER_BRANCH=""

# Разбор аргументов
for arg in "$@"; do
  case "$arg" in
    -y|--yes)
      AUTO_YES=true
      shift
      ;;
    *)
      USER_BRANCH="$arg"
      shift || true
      ;;
  esac
done

# Определяем резервную ветку
BACKUP_BRANCH="${USER_BRANCH:-$BACKUP_BRANCH_DEFAULT}"

echo "📋 Резервная ветка: $BACKUP_BRANCH"

# Проверка, что мы в git-репозитории
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ Ошибка: Текущая директория не является git-репозиторием"
  exit 1
fi

# Обновляем ссылки на удалённые ветки
echo "🌐 Обновляем ссылки на удалённые ветки..."
git fetch --all --prune

# Проверяем существование ветки
if ! git show-ref --verify --quiet "refs/remotes/origin/${BACKUP_BRANCH}"; then
    echo "❌ Ошибка: Резервная ветка ${BACKUP_BRANCH} не найдена на origin"
    echo "Доступные резервные ветки:" && git branch -r | grep backup/ || echo "Нет резервных веток"
    exit 1
fi

# Предупреждение
echo "⚠️  ВНИМАНИЕ: Это действие откатит все локальные изменения!"
echo "Текущие незафиксированные правки будут сохранены в stash."

if [ "$AUTO_YES" = false ]; then
  read -p "Продолжить? (y/N): " -n 1 -r || true
  echo
  if [[ ! ${REPLY:-} =~ ^[Yy]$ ]]; then
      echo "❌ Откат отменен"
      exit 1
  fi
fi

# Сохранение текущих незакоммиченных изменений
if ! git diff-index --quiet HEAD --; then
    echo "💾 Сохраняем текущие изменения в stash..."
    git stash push -m "Auto-stash before rollback $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Переключение и обновление
echo "🔄 Переключаемся на резервную ветку..."
git checkout "$BACKUP_BRANCH"

echo "🔄 Обновляем резервную ветку..."
git pull --ff-only origin "$BACKUP_BRANCH"

echo "✅ Откат завершен успешно!"
echo "📋 Текущая ветка: $(git branch --show-current)"
echo "📋 Последний коммит:" && git log --oneline -1 | cat

echo ""
echo "💡 Полезные команды:"
echo "  - git log --oneline -10 | cat   # История коммитов"
echo "  - git stash list | cat          # Сохраненные изменения"
echo "  - git stash pop                 # Восстановить последние изменения"
echo "  - git branch -a | cat           # Все ветки" 