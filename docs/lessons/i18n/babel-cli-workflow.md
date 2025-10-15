### Babel CLI: рабочий цикл (extract → update → translate → compile)

#### Конфиг
Уже есть `babel.cfg`:
```
[python: **.py]
[jinja2: **/templates/**.html]
```

#### 1) Экстракция строк в POT
```bash
source venv/bin/activate && pybabel extract -F babel.cfg -o translations/messages.pot . | cat
```

#### 2) Обновление/создание каталогов переводов
- Обновить существующие:
```bash
source venv/bin/activate && pybabel update -i translations/messages.pot -d translations -l en -l zh | cat
```
- Создать новый язык (пример: de):
```bash
source venv/bin/activate && pybabel init -i translations/messages.pot -d translations -l de | cat
```

#### 3) Редактирование `.po`
Откройте `translations/<lang>/LC_MESSAGES/messages.po` и заполните `msgstr`.

#### 4) Компиляция `.mo` ⚠️ **ОБЯЗАТЕЛЬНО!**

**⚠️ БЕЗ ЭТОГО ШАГА ПЕРЕВОДЫ НЕ РАБОТАЮТ!**

Flask-Babel читает только скомпилированные `.mo` файлы, а не текстовые `.po`!

```bash
# macOS/Linux
source venv/bin/activate && pybabel compile -d translations | cat

# Windows (PowerShell)
venv\Scripts\activate
pybabel compile -d translations
```

**Что создаётся:**
- `translations/en/LC_MESSAGES/messages.mo` ✓
- `translations/zh/LC_MESSAGES/messages.mo` ✓

**Для установленного приложения (Windows):**
После компиляции скопируйте `.mo` файлы в установленное приложение:
```powershell
$installPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\VPN Server Manager"
Copy-Item "translations\en\LC_MESSAGES\messages.mo" "$installPath\translations\en\LC_MESSAGES\" -Force
Copy-Item "translations\zh\LC_MESSAGES\messages.mo" "$installPath\translations\zh\LC_MESSAGES\" -Force
```

---

### Советы (Cursor/macOS):
- Всегда активируйте окружение: `source venv/bin/activate`
- Добавляйте `| cat`, чтобы избежать пейджера
- Если предупреждения про plural — проверьте формы множественного числа и ключ `Plural-Forms` в заголовке `.po`

### Советы (Windows):
- Активация venv: `venv\Scripts\activate`
- После изменения `.po` файлов **ВСЕГДА** запускайте `pybabel compile`
- Для установленного приложения копируйте `.mo` файлы в папку установки 