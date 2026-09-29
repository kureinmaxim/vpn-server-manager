import re
import ssl
from unittest.mock import patch

import pytest

from app.routes.net_tools import TOOLS
from app.services.net_tools import ToolError


@pytest.fixture
def unlocked(client):
    with client.session_transaction() as session:
        session['pin_authenticated'] = True
    return client


def run(client, tool='port', payload=None, **kwargs):
    client.get('/net-tools/' + tool)
    with client.session_transaction() as session:
        token = session['net_tools_token']
    return client.post('/net-tools/' + tool + '/run',
                       json=payload if payload is not None else {'host': 'example.com', 'port': '443'},
                       headers={'X-Net-Tools-Token': token}, **kwargs)


def test_locked_catalog_and_execution(client):
    assert client.get('/net-tools/').status_code == 302
    with patch('app.routes.net_tools.run_tool') as execute:
        assert client.post('/net-tools/port/run', json={}).status_code == 401
        execute.assert_not_called()


def test_partial_auth_is_not_enough(client):
    with client.session_transaction() as session:
        session['authenticated'] = True
    assert client.get('/net-tools/').status_code == 302


def test_legacy_pin_session(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True)
    assert client.get('/net-tools/').status_code == 200


@pytest.mark.parametrize('lang,title', [('ru', 'Сетевые инструменты'), ('en', 'Network tools'), ('zh', '网络工具')])
def test_catalog_and_all_details_are_localized(unlocked, lang, title):
    response = unlocked.get('/net-tools/?lang=' + lang)
    assert response.status_code == 200
    assert title in response.text
    assert response.text.count('class="net-card ') == 9
    for tool in TOOLS:
        detail = unlocked.get('/net-tools/' + tool['id'])
        assert detail.status_code == 200
        if lang != 'ru':
            # New UI text must not fall back to Russian (exclude shared layout).
            section = detail.text.split('<div class="container net-tools')[1].split('</main>')[0]
            assert not re.search('[А-Яа-яЁё]', section)


def test_home_button(unlocked):
    html = unlocked.get('/').text
    assert 'href="/net-tools/"' in html
    assert html.index('dnsleaktest.com') < html.index('href="/net-tools/"')


def test_token_required(unlocked):
    with patch('app.routes.net_tools.run_tool') as execute:
        assert unlocked.post('/net-tools/port/run', json={}).status_code == 403
        unlocked.get('/net-tools/port')
        assert unlocked.post('/net-tools/port/run', json={}, headers={'X-Net-Tools-Token': 'wrong'}).status_code == 403
        execute.assert_not_called()


def test_run_returns_result(unlocked):
    with patch('app.routes.net_tools.run_tool', return_value={'reachable': True}) as execute:
        response = run(unlocked)
    assert response.json == {'result': {'reachable': True}}
    execute.assert_called_once_with('port', {'host': 'example.com', 'port': '443'})


@pytest.mark.parametrize('payload', [[], 'bad', 3])
def test_malformed_payload(unlocked, payload):
    assert run(unlocked, payload=payload).status_code == 400


@pytest.mark.parametrize('exception,status', [(ToolError('host'), 400), (TimeoutError(), 504),
                                           (ssl.SSLCertVerificationError(), 422), (OSError(), 502)])
def test_localized_failures_and_slot_release(unlocked, exception, status):
    unlocked.get('/net-tools/?lang=zh')
    with patch('app.routes.net_tools.run_tool', side_effect=exception):
        for _ in range(5):
            response = run(unlocked)
            assert response.status_code == status
            assert re.search('[\u4e00-\u9fff]', response.json['error'])


def test_unknown_and_external_tools(unlocked):
    assert unlocked.get('/net-tools/missing').status_code == 404
    assert run(unlocked, tool='reverse-ip').status_code == 404
    page = unlocked.get('/net-tools/reverse-ip').text
    assert 'tools/reverse-ip-lookup' in page
    assert 'rel="noopener noreferrer"' in page


def test_busy(unlocked):
    with patch('app.routes.net_tools._slots') as slots:
        slots.acquire.return_value = False
        assert run(unlocked).status_code == 429
        slots.release.assert_not_called()
