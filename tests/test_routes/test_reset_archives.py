import time
from unittest.mock import Mock
import pytest
from app.routes import reset as routes
from .test_reset import reset_client


def post(client, endpoint='', body=None, server='one'):
    return client.post(f'/api/servers/{server}/reset/archives{endpoint}', json=body or {},
                       headers={'X-CSRF-Token': 'test-csrf'})


def issue(client, monkeypatch):
    routes._archive_tickets.clear()
    monkeypatch.setattr(routes, 'remote', lambda *args, **kwargs: {'hostname': 'test-vps',
        'archives': [{'name': '20260925-120000-aaaaaaaaaaaa', 'bytes': 100, 'hash': 'abc'}]})
    response = post(client)
    assert response.status_code == 200
    assert 'hash' not in response.json['archives'][0]
    return response.json['archives'][0]['ticket']


def test_archive_page(reset_client):
    assert reset_client.get('/servers/one/reset/archives').status_code == 200


def test_archive_requires_auth(client):
    assert post(client).status_code == 401


def test_archive_requires_csrf(reset_client):
    assert reset_client.post('/api/servers/one/reset/archives', json={}).status_code == 403
    assert reset_client.post('/api/servers/one/reset/archives/delete', json={}).status_code == 403


@pytest.mark.parametrize('change', ['host', 'server', 'owner', 'expired'])
def test_archive_rejects_invalid_confirmation(reset_client, monkeypatch, change):
    ticket = issue(reset_client, monkeypatch)
    body = dict(ticket=ticket, confirmation='test-vps')
    server = 'one'
    if change == 'host': body['confirmation'] = 'wrong'
    if change == 'server': server = 'two'
    if change == 'owner': routes._archive_tickets[ticket]['owner'] = 'other-session'
    if change == 'expired': routes._archive_tickets[ticket]['time'] = time.monotonic() - 601
    remote = Mock()
    monkeypatch.setattr(routes, 'remote', remote)
    assert post(reset_client, '/delete', body, server).status_code in (400, 409)
    remote.assert_not_called()


def test_archive_ticket_single_use(reset_client, monkeypatch):
    ticket = issue(reset_client, monkeypatch)
    remote = Mock(return_value={'success': True})
    monkeypatch.setattr(routes, 'remote', remote)
    body = dict(ticket=ticket, confirmation='test-vps')
    assert post(reset_client, '/delete', body).status_code == 200
    assert post(reset_client, '/delete', body).status_code == 409
    assert remote.call_count == 1
    assert remote.call_args.args[1] == ['20260925-120000-aaaaaaaaaaaa', 'abc', 'test-vps']


def test_archive_uncertain_delete_cannot_retry(reset_client, monkeypatch):
    ticket = issue(reset_client, monkeypatch)
    monkeypatch.setattr(routes, 'remote', Mock(side_effect=TimeoutError))
    body = dict(ticket=ticket, confirmation='test-vps')
    assert post(reset_client, '/delete', body).status_code == 502
    assert post(reset_client, '/delete', body).status_code == 409
