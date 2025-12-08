#!/bin/bash

# Создание новой резервной ветки и архива данных приложения
# Использование:
#   ./backup_tools/create_backup.sh [-m "message"]
# Опционально: переменная APP_DATA_DIR переопределит путь к данным приложения

set -euo pipefail

MESSAGE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message)
      MESSAGE="$2"; shift 2;
      ;;
    *)
      echo "Неизвестный аргумент: $1"; exit 1;
      ;;
  esac
done

TS=$(date +%Y%m%d-%H%M%S)
BRANCH="backup/current-state-${TS}"
BACKUPS_DIR="backups"
mkdir -p "$BACKUPS_DIR"

# Определяем директорию данных приложения (macOS по умолчанию)
DEFAULT_APP_DATA_DIR="$HOME/Library/Application Support/VPNServerManager-Clean"
APP_DATA_DIR="${APP_DATA_DIR:-$DEFAULT_APP_DATA_DIR}"

echo "🗂️  Источник данных приложения: $APP_DATA_DIR"
if [ -d "$APP_DATA_DIR" ]; then
  ARCHIVE_PATH="${BACKUPS_DIR}/appdata_${TS}.tar.gz"
  echo "📦 Архивируем данные приложения в ${ARCHIVE_PATH} ..."
  tar -czf "$ARCHIVE_PATH" -C "$(dirname "$APP_DATA_DIR")" "$(basename "$APP_DATA_DIR")"
else
  echo "⚠️  Директория данных не найдена, пропускаю архивирование"
fi

# Убедимся, что мы в git-репозитории
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ Ошибка: не git-репозиторий"; exit 1
fi

echo "🌐 Обновляем удалённые ссылки..."
git fetch --all --prune

# Создаём новую ветку от текущей
CURRENT_BRANCH=$(git branch --show-current)
echo "📋 Текущая ветка: ${CURRENT_BRANCH}"

echo "🌿 Создаём резервную ветку: ${BRANCH} ..."
git checkout -b "$BRANCH"

# Добавляем архив, если он создан
if [ -f "${ARCHIVE_PATH:-}" ]; then
  git add "$ARCHIVE_PATH"
  git commit -m "backup: add appdata archive ${TS}${MESSAGE:+ - }${MESSAGE}" || true
fi

echo "⬆️  Публикуем ветку: ${BRANCH} ..."
git push -u origin "$BRANCH"

echo "🔁 Возврат на исходную ветку: ${CURRENT_BRANCH}"
git checkout "$CURRENT_BRANCH"

echo "✅ Резервная ветка создана: ${BRANCH}"
echo "📦 Архив (если был): ${ARCHIVE_PATH:-нет}" 