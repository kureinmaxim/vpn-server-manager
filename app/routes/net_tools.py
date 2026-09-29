"""Network tools catalogue and authenticated diagnostic endpoints."""
import hmac
import http.client
import secrets
import socket
import ssl
import subprocess
import threading

import requests
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from flask_babel import gettext as _, lazy_gettext as _l

from ..services.net_tools import ToolError, run_tool

net_tools_bp = Blueprint('net_tools', __name__, url_prefix='/net-tools')
_slots = threading.BoundedSemaphore(4)

TOOLS = [
    dict(id='port', icon='door-open', title=_l('Проверка портов'),
         description=_l('Проверьте доступность TCP-порта на сервере.'),
         note=_l('Успешное соединение означает, что TCP-порт доступен с компьютера приложения. Тайм-аут может означать фильтрацию трафика. UDP не проверяется.'),
         source=_l('Компьютер приложения'), command='nc -vz example.com 443', windows='Test-NetConnection example.com -Port 443'),
    dict(id='dns', icon='globe2', title=_l('DNS-запрос / dig'),
         description=_l('Просмотрите A, AAAA, MX, TXT и другие записи домена.'),
         note=_l('Запрос отправляется в Google Public DNS. Ответ может отличаться от DNS вашего провайдера. Для PTR можно указать IP-адрес.'),
         source='Google Public DNS', command='dig example.com',
         extra_command='dig +short example.com @1.1.1.1',
         windows='Resolve-DnsName example.com',
         command_note=_l('dig запрашивает DNS-записи, а не проверяет доступность хоста. Без @ используется настроенный DNS-сервер; @1.1.1.1 выбирает Cloudflare, а +short сокращает вывод. На Windows можно запустить dig в WSL, если он установлен, или использовать Resolve-DnsName в PowerShell. Для проверки доступности используйте Ping или Test-Connection.')),
    dict(id='ping', icon='broadcast', title='Ping',
         description=_l('Проверьте доступность узла и задержку четырьмя ICMP-пакетами.'),
         note=_l('Некоторые серверы блокируют ICMP. Отсутствие ответа Ping не означает, что сайт или VPN недоступен.'),
         source=_l('Компьютер приложения'), command='ping -c 4 example.com', windows='ping -n 4 example.com'),
    dict(id='tls', icon='shield-check', title=_l('Проверка SSL/TLS'),
         description=_l('Проверьте сертификат, срок действия и согласованный протокол TLS.'),
         note=_l('Проверяются доверие к сертификату и соответствие имени узла. Это проверка одного TLS-соединения, а не полный аудит шифров.'),
         source=_l('Компьютер приложения'), command='openssl s_client -connect example.com:443 -servername example.com </dev/null', windows='curl.exe -Iv https://example.com'),
    dict(id='whois', icon='binoculars', title='WHOIS / RDAP',
         description=_l('Получите регистрационные данные домена или IP-адреса.'),
         note=_l('Используется RDAP — современный формат регистрационных данных. Реестр может скрывать персональные данные или ограничивать запросы.'),
         source='RDAP.org', command='curl -L https://rdap.org/domain/example.com', windows='curl.exe -L https://rdap.org/domain/example.com'),
    dict(id='reverse-ip', icon='search', title='Reverse IP Lookup',
         description=_l('Найдите сайты, которые могут использовать тот же IP-адрес.'),
         note=_l('Поиск соседних сайтов требует внешней базы. Откройте Connected и введите адрес там. PTR в DNS-запросе показывает обратную DNS-запись, а не список сайтов.'),
         source='Connected', command=None, windows=None),
    dict(id='fetch', icon='cloud-arrow-down', title='HTTP / Fetch',
         description=_l('Посмотрите HTTP-статус, заголовки и начало ответа сервера.'),
         note=_l('Выполняется GET без cookies и авторизации. Перенаправления не выполняются автоматически. Ответ ограничен 64 КиБ и показан как текст.'),
         source=_l('Компьютер приложения'), command='curl -i --max-time 15 https://example.com', windows='curl.exe -i --max-time 15 https://example.com'),
    dict(id='location', icon='map', title=_l('Сетевое расположение'),
         description=_l('Узнайте примерное местоположение и организацию IP-адреса.'),
         note=_l('Геолокация IP приблизительна и может указывать на дата-центр или выход VPN. Для домена используется один из его IP-адресов.'),
         source='IPinfo', command='curl https://ipinfo.io/8.8.8.8/json', windows='curl.exe https://ipinfo.io/8.8.8.8/json'),
    dict(id='my-ip', icon='geo-alt', title=_l('Мой внешний IP'),
         description=_l('Узнайте внешний IP и местоположение подключения приложения.'),
         note=_l('Показан адрес выхода компьютера приложения. При запуске на удалённом сервере это IP сервера, а не вашего браузера.'),
         source='IPinfo', command='curl https://ipinfo.io/json', windows='curl.exe https://ipinfo.io/json'),
]

ERRORS = {
    'host': _l('Введите корректный IP-адрес или доменное имя без протокола и пути.'),
    'port': _l('Порт должен быть целым числом от 1 до 65535.'),
    'record': _l('Выберите поддерживаемый тип DNS-записи.'),
    'url': _l('Введите HTTP- или HTTPS-адрес без логина и пароля.'),
    'public': _l('Для этой проверки нужен публичный IP-адрес. Локальные и служебные адреса недоступны.'),
    'provider': _l('Источник данных не ответил или не нашёл запись. Повторите запрос позже.'),
    'ping_missing': _l('Утилита ping не установлена. Используйте команду ниже на своём компьютере.'),
    'tool': _l('Неизвестный инструмент.'),
}


@net_tools_bp.before_request
def protect_tools():
    if not (session.get('pin_authenticated') or (session.get('authenticated') and session.get('pin_verified'))):
        if request.method == 'POST':
            return jsonify(error=_('Разблокируйте приложение и повторите проверку.')), 401
        return redirect(url_for('main.index_locked'))
    if request.method == 'POST':
        token = session.get('net_tools_token', '')
        if not token or not hmac.compare_digest(token.encode(), request.headers.get('X-Net-Tools-Token', '').encode()):
            return jsonify(error=_('Обновите страницу и повторите проверку.')), 403


@net_tools_bp.get('/')
def index():
    return render_template('net_tools.html', tools=TOOLS, selected=None)


@net_tools_bp.get('/<tool_id>')
def detail(tool_id):
    tool = next((t for t in TOOLS if t['id'] == tool_id), None)
    if tool is None:
        abort(404)
    if 'net_tools_token' not in session:
        session['net_tools_token'] = secrets.token_urlsafe(32)
    return render_template('net_tools.html', tools=TOOLS, selected=tool,
                           token=session['net_tools_token'])


@net_tools_bp.post('/<tool_id>/run')
def run(tool_id):
    if tool_id not in {t['id'] for t in TOOLS if t['id'] != 'reverse-ip'}:
        abort(404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error=_('Некорректные параметры запроса.')), 400
    if not _slots.acquire(blocking=False):
        return jsonify(error=_('Дождитесь завершения предыдущих проверок.')), 429
    try:
        return jsonify(result=run_tool(tool_id, data))
    except ToolError as exc:
        return jsonify(error=str(ERRORS[exc.code])), 400
    except ssl.SSLCertVerificationError:
        return jsonify(error=_('Сертификат не прошёл проверку доверия, имени или срока действия.')), 422
    except (TimeoutError, subprocess.TimeoutExpired, requests.Timeout):
        return jsonify(error=_('Время ожидания истекло. Проверьте адрес и повторите запрос.')), 504
    except socket.gaierror:
        return jsonify(error=_('Не удалось определить IP-адрес домена.')), 422
    except (OSError, requests.RequestException, ValueError, http.client.HTTPException):
        return jsonify(error=_('Проверка не выполнена. Проверьте адрес, подключение и доступность сервиса.')), 502
    finally:
        _slots.release()
