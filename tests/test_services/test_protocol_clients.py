import json
from urllib.parse import urlsplit, parse_qs, unquote
import pytest
from app.services import protocol_clients as clients


def test_anytls_encodes_password_and_ipv6():
    uri = clients.export_profile('anytls', {'server':'2001:db8::1','port':443,'sni':'example.com'}, {'password':'a@b:/?#','name':'Test name'})
    parsed = urlsplit(uri)
    assert parsed.hostname == '2001:db8::1'
    assert unquote(parsed.username) == 'a@b:/?#'
    assert unquote(parsed.fragment) == 'Test name'


def test_tuic_profile_fields():
    uri = clients.export_profile('tuic', {'server':'example.com','port':8443,'insecure':True}, {'uuid':'12345678-1234-1234-1234-123456789abc','password':'fixture'})
    query = parse_qs(urlsplit(uri).query)
    assert query['alpn'] == ['h3']
    assert query['allow_insecure'] == ['1']
    assert query['congestion_control'] == ['bbr']


def test_xhttp_preserves_transport_settings():
    uri = clients.export_profile('xhttp', {'server':'example.com','port':443,'path':'/a?b=c','host':'example.org','mode':'packet-up'}, {'uuid':'12345678-1234-1234-1234-123456789abc'})
    query = parse_qs(urlsplit(uri).query)
    assert query['path'] == ['/a?b=c']
    assert query['type'] == ['xhttp']
    assert query['host'] == ['example.org']


@pytest.mark.parametrize('config', [{'server':'example.com@evil.example'}, {'server':'example.com','port':True}, {'server':'example.com','port':70000}])
def test_invalid_endpoint(config):
    with pytest.raises(ValueError):
        clients.export_profile('anytls', config, {'password':'fixture'})


def test_clients_do_not_disclose_credentials(monkeypatch):
    monkeypatch.setattr(clients, 'sources', lambda *a: {'anytls':[('/fixture','candidate')]})
    monkeypatch.setattr(clients, 'read_metadata', lambda p: ({'clients':[{'name':'Alice','password':'private-marker'}]}, 'revision'))
    body = dict(operation='clients',component='anytls',source_id=clients.source_id('/fixture'),revision='revision')
    result = clients.client_operation(body, {}, None)
    assert result['clients'][0]['name'] == 'Alice'
    assert 'private-marker' not in json.dumps(result)
    body['revision'] = 'old'
    with pytest.raises(ValueError, match='target_changed'):
        clients.client_operation(body, {}, None)


def test_unknown_path_never_read(monkeypatch):
    monkeypatch.setattr(clients, 'sources', lambda *a: {'anytls':[('/fixture','candidate')]})
    def forbidden(path):
        pytest.fail('unexpected file access')
    monkeypatch.setattr(clients, 'read_metadata', forbidden)
    with pytest.raises(ValueError):
        clients.selected_config(dict(component='anytls',source_id=clients.source_id('/etc/shadow')), {}, None)


def test_mtproto_link():
    uri = clients.export_profile('mtproto', {'server':'example.com','port':993}, {'secret':'ab'*16})
    assert parse_qs(urlsplit(uri).query)['secret'] == ['ab'*16]
