"""SSH-ключ в карточке сервера: сохранение, удаление, вход без пароля."""
import copy
from unittest.mock import Mock

import pytest

from app.routes import api as api_routes
from app.routes.api import _get_server_ssh_credentials, load_check_limiter
from app.services import registry
from app.services.crypto_service import CryptoService
from app.services.load_snapshot import parse_snapshot
from tests.test_services.test_load_snapshot import SAMPLE
from tests.test_services.test_ssh_auth import ed25519_key, expected_fingerprint, rsa_pem_encrypted


def make_server(**ssh):
    return {
        'id': '1',
        'name': 'Test server',
        'provider': 'Test provider',
        'ip_address': '192.0.2.10',
        'os': 'Debian',
        'status': 'Active',
        'notes': '',
        'docker_info': '',
        'software_info': '',
        'card_color': '#ffc107',
        'panel_url': '',
        'hoster_url': '',
        'icon_filename': '',
        'archived': False,
        'geolocation': {},
        'specs': {'cpu': '', 'ram': '', 'disk': ''},
        'payment_info': {'amount': 0.0, 'currency': 'USD', 'next_due_date': '', 'payment_period': 'Monthly'},
        'ssh_credentials': {
            'user': 'root', 'port': 22, 'root_login_allowed': True,
            'password': 'enc::old-ssh', 'password_decrypted': 'old-ssh',
            'root_password': '', 'root_password_decrypted': '',
            **ssh,
        },
        'panel_credentials': {'user': '', 'user_decrypted': '', 'password': '', 'password_decrypted': ''},
        'hoster_credentials': {'login_method': 'password', 'user': '', 'user_decrypted': '',
                               'password': '', 'password_decrypted': ''},
        'checks': {'dns_ok': False, 'streaming_ok': False},
    }


class StubDataManager:
    """Шифрование — префикс enc::, как в соседних тестах; пустое значение остаётся пустым."""

    def __init__(self, servers):
        self.servers = servers
        self.saved_servers = None

    def load_servers(self, config):
        return self.servers

    def get_active_data_path(self, config):
        return 'test-data.enc'

    def save_servers(self, servers, file_path):
        self.saved_servers = copy.deepcopy(servers)

    def encrypt_data(self, data):
        return f'enc::{data}' if data else ''

    def decrypt_data(self, data):
        return data[len('enc::'):] if isinstance(data, str) and data.startswith('enc::') else (data or '')


@pytest.fixture
def card_client(client, monkeypatch):
    from app.routes import main as main_routes
    # Сохранение карточки ищет город по IP в интернете — в тестах без сети
    monkeypatch.setattr(main_routes, '_apply_fresh_geolocation', lambda server: False)
    registry.register('crypto', CryptoService())
    with client.session_transaction() as sess:
        sess['authenticated'] = True
        sess['pin_verified'] = True
    return client


def flashes(client):
    with client.session_transaction() as sess:
        return [message for _category, message in sess.get('_flashes', [])]


def test_pasted_key_is_saved_encrypted_with_fingerprint(card_client):
    text, public = ed25519_key()
    manager = StubDataManager([make_server()])
    registry.register('data_manager', manager)
    pasted = text.replace('\n', '\r\n')  # вставка из Windows
    response = card_client.post('/edit_server/1', data={'ssh_key': pasted, 'name': 'Renamed'})
    assert response.status_code == 302
    ssh = manager.saved_servers[0]['ssh_credentials']
    assert ssh['private_key'] == 'enc::' + text
    assert ssh['key_hint'] == expected_fingerprint(public)
    assert ssh['key_path'] == ''
    assert ssh['key_passphrase'] == ''
    assert ssh['password'] == 'enc::old-ssh'  # пароль остаётся запасным
    assert manager.saved_servers[0]['name'] == 'Renamed'


def test_key_path_with_passphrase(card_client, tmp_path):
    path = tmp_path / 'id_rsa'
    path.write_text(rsa_pem_encrypted('pw'))
    manager = StubDataManager([make_server()])
    registry.register('data_manager', manager)
    card_client.post('/edit_server/1', data={'ssh_key': f'  {path}  ', 'ssh_key_passphrase': 'pw'})
    ssh = manager.saved_servers[0]['ssh_credentials']
    assert ssh['private_key'] == f'enc::{path}'
    assert ssh['key_path'] == str(path)
    assert ssh['key_passphrase'] == 'enc::pw'
    assert ssh['key_hint'].startswith('ssh-rsa SHA256:')


def test_unreadable_key_is_not_saved_but_the_card_is(card_client):
    manager = StubDataManager([make_server(private_key='enc::OLD', key_hint='ssh-ed25519 SHA256:old')])
    registry.register('data_manager', manager)
    response = card_client.post('/edit_server/1', data={'ssh_key': '/nonexistent/id_ed25519', 'name': 'Renamed'})
    assert response.status_code == 302
    ssh = manager.saved_servers[0]['ssh_credentials']
    assert ssh['private_key'] == 'enc::OLD'
    assert ssh['key_hint'] == 'ssh-ed25519 SHA256:old'
    assert manager.saved_servers[0]['name'] == 'Renamed'
    assert any('SSH' in message for message in flashes(card_client))


def test_trash_removes_the_key(card_client):
    manager = StubDataManager([make_server(private_key='enc::KEY', key_passphrase='enc::PP',
                                           key_hint='ssh-ed25519 SHA256:x', key_path='~/.ssh/id')])
    registry.register('data_manager', manager)
    card_client.post('/edit_server/1', data={'clear_ssh_key': '1'})
    ssh = manager.saved_servers[0]['ssh_credentials']
    assert [ssh[field] for field in ('private_key', 'key_passphrase', 'key_hint', 'key_path')] == ['', '', '', '']
    assert ssh['password'] == 'enc::old-ssh'


def test_empty_key_field_keeps_the_saved_key(card_client):
    manager = StubDataManager([make_server(private_key='enc::KEY', key_hint='ssh-ed25519 SHA256:x')])
    registry.register('data_manager', manager)
    card_client.post('/edit_server/1', data={'ssh_key': '', 'name': 'Renamed'})
    assert manager.saved_servers[0]['ssh_credentials']['private_key'] == 'enc::KEY'


def test_edit_page_shows_fingerprint_but_never_the_key(card_client):
    manager = StubDataManager([make_server(private_key='enc::PRIVATE-KEY-MATERIAL', key_passphrase='enc::PASSPHRASE-X',
                                           key_hint='ssh-ed25519 SHA256:abcdef', key_path='~/.ssh/id_ed25519')])
    registry.register('data_manager', manager)
    response = card_client.get('/edit_server/1')
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'ssh-ed25519 SHA256:abcdef' in page
    assert '~/.ssh/id_ed25519' in page
    assert 'name="ssh_key"' in page
    assert 'PRIVATE-KEY-MATERIAL' not in page
    assert 'PASSPHRASE-X' not in page


def test_add_server_with_key_only(card_client):
    text, public = ed25519_key()
    manager = StubDataManager([])
    registry.register('data_manager', manager)
    response = card_client.post('/add_server', data={
        'name': 'New', 'ip_address': '192.0.2.20', 'ssh_user': 'root', 'ssh_port': '22', 'ssh_key': text,
    })
    assert response.status_code == 302
    ssh = manager.saved_servers[0]['ssh_credentials']
    assert ssh['password'] == ''
    assert ssh['private_key'] == 'enc::' + text
    assert ssh['key_hint'] == expected_fingerprint(public)


def test_credentials_include_key_only_when_set(app):
    with_key = make_server(private_key='enc::KEY-TEXT', key_passphrase='enc::PP')
    without_key = dict(make_server(), id='2')
    manager = StubDataManager([with_key, without_key])
    _, creds = _get_server_ssh_credentials('1', manager)
    assert creds['key'] == 'KEY-TEXT' and creds['key_passphrase'] == 'PP'
    assert creds['password'] == 'old-ssh'
    _, creds = _get_server_ssh_credentials('2', manager)
    assert set(creds) == {'ip', 'user', 'password', 'port'}


def test_load_snapshot_works_with_key_and_no_password(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, language='ru')
    manager = StubDataManager([{
        'id': 'k', 'name': 'Key only', 'ip_address': '192.0.2.30', 'status': 'Active',
        'ssh_credentials': {'user': 'root', 'port': 22, 'private_key': 'enc::KEY-TEXT'},
    }])
    registry.register('data_manager', manager)
    ssh = Mock()
    ssh.get_load_snapshot.return_value = parse_snapshot(SAMPLE)
    registry.register('ssh', ssh)
    load_check_limiter.requests.clear()
    try:
        response = client.get('/api/monitoring/k/load-snapshot')
    finally:
        load_check_limiter.requests.clear()
    assert response.status_code == 200
    kwargs = ssh.get_load_snapshot.call_args.kwargs
    assert kwargs['key'] == 'KEY-TEXT'
    assert kwargs['password'] == ''
    assert b'KEY-TEXT' not in response.data


def test_has_ssh_auth_message_mentions_key(client):
    """Без пароля и ключа проверка нагрузки просит указать одно из двух."""
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, language='ru')
    registry.register('data_manager', StubDataManager([{
        'id': 'n', 'ip_address': '192.0.2.40', 'status': 'Active', 'ssh_credentials': {'user': 'root'},
    }]))
    registry.register('ssh', Mock())
    load_check_limiter.requests.clear()
    response = client.get('/api/monitoring/n/load-snapshot')
    assert response.status_code == 400
    assert 'SSH-ключ' in response.json['error']
    assert api_routes.has_ssh_auth({'key': 'x'})
