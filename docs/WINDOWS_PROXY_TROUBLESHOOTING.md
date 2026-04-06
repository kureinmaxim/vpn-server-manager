# Windows: `pip` не устанавливает зависимости из-за прокси

## Симптомы

При запуске `setup_windows.bat` или ручной установке зависимостей на Windows установка может падать с ошибками вида:

```text
WARNING: Retrying (...) after connection broken by 'ProxyError('Cannot connect to proxy.' ...)
ERROR: Could not find a version that satisfies the requirement Flask>=3.0.0
ERROR: No matching distribution found for Flask>=3.0.0
```

Иногда проблема проявляется даже при прямом вызове:

```powershell
.\venv\Scripts\python.exe -m pip --isolated install Flask -i https://pypi.org/simple -vvv
```

При этом в логе видно:

```text
ProxyError('Cannot connect to proxy.', NewConnectionError(... [WinError 10061] ...))
```

## Что это означает

Проблема не в пакете `Flask` и не в `requirements.txt`.

`pip` не может подключиться к `PyPI`, потому что Windows направляет сетевые запросы через прокси-сервер, который недоступен. В результате `pip` не видит список доступных версий пакета и сообщает ложную ошибку `No matching distribution found`.

## Как была выявлена причина

Проверка стандартных источников настроек `pip` показала, что:

- переменные окружения `HTTP_PROXY` / `HTTPS_PROXY` не заданы
- `pip config debug` не показывает активных `pip.ini`
- `netsh winhttp show proxy` показывает `Direct access`

Но при этом пользовательские настройки Windows содержали активный прокси:

```powershell
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' |
Select-Object ProxyEnable, ProxyServer, AutoConfigURL
```

Пример проблемного результата:

```text
ProxyEnable ProxyServer            AutoConfigURL
----------- -----------            -------------
          1 http://127.0.0.1:12334
```

Дополнительная проверка тоже подтверждает проблему:

```powershell
Invoke-WebRequest https://pypi.org/simple/flask/ -UseBasicParsing
```

Если команда отвечает ошибкой подключения, значит доступ к `PyPI` блокируется системным прокси или локальным proxy-приложением.

## Причина

В Windows был включён системный прокси:

- `ProxyEnable = 1`
- `ProxyServer = http://127.0.0.1:12334`

Это означает, что запросы шли через локальный прокси на `127.0.0.1:12334`, но на этом порту не было работающего сервиса. Поэтому соединение отклонялось с ошибкой `[WinError 10061]`.

## Решение

Если этот прокси не нужен, его нужно временно отключить.

### Вариант 1. Отключить через PowerShell

```powershell
Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
```

При необходимости можно также очистить адрес прокси:

```powershell
Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0
Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value ''
```

После этого:

1. Закройте терминал Cursor.
2. Откройте новый терминал.
3. Повторите установку зависимостей.

### Вариант 2. Отключить через интерфейс Windows

Откройте:

`Параметры -> Сеть и Интернет -> Прокси`

Выключите:

- `Использовать прокси-сервер`
- `Использовать сценарий настройки`, если включён

При необходимости также временно отключите:

- `Автоматически определять параметры`

## Проверка после исправления

Проверьте доступ к `PyPI`:

```powershell
Invoke-WebRequest https://pypi.org/simple/flask/ -UseBasicParsing
```

Затем установите зависимости:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Или, если `venv` ещё не создан:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Если прокси нужен

Если локальный прокси `127.0.0.1:12334` используется специально, отключать его не нужно. В этом случае необходимо:

- запустить приложение, которое должно слушать этот порт
- убедиться, что прокси действительно работает
- только после этого повторить установку через `pip`

## Краткий вывод

Ошибка `No matching distribution found for Flask` в данном случае была вторичной. Настоящая причина состояла в том, что Windows направлял запросы `pip` через локальный прокси `127.0.0.1:12334`, который не отвечал.
