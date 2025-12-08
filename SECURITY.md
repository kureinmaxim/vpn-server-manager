# 🔒 Безопасность VPN Server Manager

## ⚠️ Файлы, которые НЕ ДОЛЖНЫ попадать в Git

| Файл | Содержит |
|------|----------|
| `.env` | SECRET_KEY, DEFAULT_PIN |
| `config.json` | PIN-код, пути к данным |
| `data/*.enc` | Зашифрованные данные серверов |
| `*.key`, `*.pem` | Ключи и сертификаты |

## ✅ Проверка перед коммитом

```bash
# Проверить, что секреты не в индексе
git ls-files | grep -E "\.env$|config\.json$|\.enc$"
# Если команда что-то выводит - НЕ КОММИТЬТЕ!
```

## 🚨 Если секреты уже в Git

```bash
# 1. Удалить из истории
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env config.json" \
  --prune-empty --tag-name-filter cat -- --all

# 2. Очистить и запушить
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all

# 3. Сгенерировать новые ключи
python generate_key.py
```

## 🛡️ Первоначальная настройка

```bash
cp env.example .env
python generate_key.py
cp config/config.json.template config.json
# Измените PIN в config.json!
```

## ✅ Чеклист

- [ ] `.env` в `.gitignore`
- [ ] `config.json` в `.gitignore`
- [ ] Сгенерирован уникальный `SECRET_KEY`
- [ ] Изменён PIN с 1234 на свой
