### Траблшутинг i18n

#### ⚠️ КРИТИЧНО: Переводы не работают / язык не переключается
**Симптомы:**
- Интерфейс всегда на одном языке (обычно на русском)
- Переключение языка не работает
- Все страницы показывают только дефолтный язык

**Причина:** 
Flask-Babel требует **скомпилированные** файлы `.mo`, а не текстовые `.po`!

**Решение:**
```bash
# Windows
venv\Scripts\activate
pybabel compile -d translations

# macOS/Linux
source venv/bin/activate
pybabel compile -d translations
```

**Что это делает:**
- Создаёт `translations/en/LC_MESSAGES/messages.mo`
- Создаёт `translations/zh/LC_MESSAGES/messages.mo`
- Без этих файлов Flask-Babel **НЕ ВИДИТ** переводы!

**Для установленного приложения:**
После компиляции нужно скопировать `.mo` файлы в папку установленного приложения:
```powershell
# Windows (PowerShell)
$installPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\VPN Server Manager"
Copy-Item "translations\en\LC_MESSAGES\messages.mo" "$installPath\translations\en\LC_MESSAGES\" -Force
Copy-Item "translations\zh\LC_MESSAGES\messages.mo" "$installPath\translations\zh\LC_MESSAGES\" -Force
```

**Проверка:**
```powershell
# Проверьте наличие .mo файлов
Test-Path "translations\en\LC_MESSAGES\messages.mo"  # Должно быть True
Test-Path "translations\zh\LC_MESSAGES\messages.mo"  # Должно быть True
```

---

#### Проблема: «msg has more translations than num_plurals of catalog»
- Причина: в `.po` заданы plural-формы с количеством, превышающим `nplurals` из заголовка `Plural-Forms`.
- Решение: привести число форм к корректному для языка (en — 2 формы; zh — 1). Лишние индексы удалить.

#### Пустые строки в UI
- Убедитесь, что `.mo` скомпилированы: `pybabel compile -d translations`
- Проверьте, что используемый язык действительно активирован (`session['language']`).
- Если строка не обёрнута в `_(...)`, она не попадёт в `.po`.

#### Плейсхолдеры ломаются
- Во всех переводах сохраняйте те же плейсхолдеры `%(name)s`/`%s`.
- В автопереводе плейсхолдеры защищаются автоматически.

#### Переводы не попадают в .app
- При упаковке нужно включить каталог `translations` в дистрибутив. См. «Упаковка (PyInstaller)».

#### Компиляция не создаёт `.mo`
- Проверьте права на `translations/*/LC_MESSAGES`
- Убедитесь, что `babel` установлен и активировано venv 