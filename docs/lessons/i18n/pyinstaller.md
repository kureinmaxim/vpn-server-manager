### Упаковка (PyInstaller) и переводы

Чтобы переводы работали в собранном `.app`, каталог `translations` должен быть включён в сборку.

#### Вариант 1: командой PyInstaller
Добавьте к параметрам:
```
--add-data=translations:translations
```

#### Вариант 2: правка `build_macos.py`
В список `datas` добавить строку:
```python
datas = [
    "templates:templates",
    "static:static",
    "config.json:.",
    "data:data",
    "requirements.txt:.",
    # ДОБАВИТЬ:
    "translations:translations",
]
```
Затем пересоберите:
```bash
source venv/bin/activate && python3 build_macos.py | cat
```

После сборки проверьте, что внутри `.app/Contents/Resources/translations` присутствуют `.mo`. 