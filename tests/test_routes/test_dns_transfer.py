"""DNS card must survive every export/import path together with servers."""
import io
import os
import sys
import zipfile

import pytest
from cryptography.fernet import Fernet

from app.services import dns_registry as dns_reg, registry
from app.services.data_manager_service import DataManagerService


def fill(manager, path, domain_name='example.com', provider_name='Cloudflare', server='vps', ip='203.0.113.5'):
    provider = dns_reg.build_provider({'kind': 'cloudflare', 'name': provider_name, 'user': 'me@x.io',
                                       'password': 'p%ss'}, None, manager.encrypt_data)
    domain = dns_reg.build_domain({'name': domain_name, 'provider_id': provider['id'], 'registrar': 'Namecheap',
                                   'expires_on': '2027-01-01'}, None, [provider])
    domain['records'].append(dns_reg.build_record({'name': 'vpn', 'type': 'A', 'content': '203.0.113.5'}, domain))
    manager.save_servers([{'id': 1, 'name': server, 'ip_address': ip,
                           'ssh_credentials': {'password': manager.encrypt_data('ssh')}}], str(path),
                         dns={'providers': [provider], 'domains': [domain]})


@pytest.fixture
def env(app, client, tmp_path, monkeypatch):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    app.config.update(SECRET_KEY=manager.secret_key, APP_DATA_DIR=str(tmp_path))
    path = tmp_path / 'data' / 'servers.enc'
    path.parent.mkdir(exist_ok=True)
    fill(manager, path)
    registry.register('data_manager', manager)
    app.config['active_data_file'] = str(path)
    exports = tmp_path / 'exports'
    exports.mkdir()
    monkeypatch.setattr(DataManagerService, 'get_export_dir', lambda self: str(exports))
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, pin_authenticated=True)
    return client, exports


def current():
    from flask import current_app
    manager = registry.get('data_manager')
    return manager, manager.load_servers(current_app.config), dns_reg.normalize(manager.load_dns(current_app.config))


def password(manager, dns):
    return manager.decrypt_data(dns['providers'][0]['password'])


def test_export_then_import_restores_dns(env):
    client, exports = env
    assert client.get('/export_data').status_code == 200
    exported = next(exports.glob('servers_export_*.enc')).read_bytes()

    response = client.post('/export_package', data={'confirm_secret_export': 'yes'})
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert archive.read(next(n for n in archive.namelist() if n.endswith('.enc'))) == exported

    manager = registry.get('data_manager')
    manager.save_dns({}, client.application.config['active_data_file'])
    assert current()[2]['domains'] == []

    client.post('/import_data', data={'data_file': (io.BytesIO(exported), 'backup.enc')},
                content_type='multipart/form-data')
    manager, servers, dns = current()
    assert [s['name'] for s in servers] == ['vps']
    assert dns['domains'][0]['name'] == 'example.com' and dns['domains'][0]['records'][0]['name'] == 'vpn'
    assert password(manager, dns) == 'p%ss'
    assert 'vpn.example.com' in client.get(f"/dns/domains/{dns['domains'][0]['id']}").text


def test_import_external_merges_dns_and_reencrypts(env, tmp_path):
    client, _ = env
    other = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    other_path = tmp_path / 'other.enc'
    fill(other, other_path, domain_name='other.org', provider_name='Porkbun', server='vps2', ip='203.0.113.7')
    fill_dup = other.read_payload(str(other_path))
    # Same domain as ours must be skipped
    fill_dup[1]['domains'].append(dict(fill_dup[1]['domains'][0], id='dup', name='example.com'))
    other.save_servers(fill_dup[0], str(other_path), dns=fill_dup[1])

    response = client.post('/import_external_data', data={
        'external_file': (io.BytesIO(other_path.read_bytes()), 'other.enc'), 'external_key': other.secret_key},
        content_type='multipart/form-data', follow_redirects=True)
    assert 'DNS domains imported: 1' in response.text
    manager, servers, dns = current()
    assert sorted(s['name'] for s in servers) == ['vps', 'vps2']
    assert sorted(d['name'] for d in dns['domains']) == ['example.com', 'other.org']
    porkbun = next(p for p in dns['providers'] if p['name'] == 'Porkbun')
    assert manager.decrypt_data(porkbun['password']) == 'p%ss'
    other_domain = next(d for d in dns['domains'] if d['name'] == 'other.org')
    assert other_domain['provider_id'] == porkbun['id'] and other_domain['records']


def test_import_external_legacy_file_keeps_our_dns(env, tmp_path):
    client, _ = env
    other = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    legacy = tmp_path / 'legacy.enc'
    other.save_servers([{'id': 1, 'name': 'old'}], str(legacy))
    client.post('/import_external_data', data={
        'external_file': (io.BytesIO(legacy.read_bytes()), 'legacy.enc'), 'external_key': other.secret_key},
        content_type='multipart/form-data')
    _, servers, dns = current()
    assert sorted(s['name'] for s in servers) == ['old', 'vps'] and dns['domains'][0]['name'] == 'example.com'


def test_verify_key_reports_dns(env):
    client, _ = env
    path = client.application.config['active_data_file']
    response = client.post('/verify_key_data', data={
        'verify_file': (io.BytesIO(open(path, 'rb').read()), 'x.enc'), 'verify_key': registry.get('data_manager').secret_key},
        content_type='multipart/form-data', follow_redirects=True)
    assert 'Найдено серверов: 1' in response.text and 'Доменов DNS: 1' in response.text


def test_change_key_keeps_dns_readable(env, monkeypatch):
    client, _ = env
    monkeypatch.setattr(sys, 'frozen', True, raising=False)  # .env goes to the temp APP_DATA_DIR
    new_key = Fernet.generate_key().decode()
    client.post('/change_main_key', data={'new_key': new_key, 'confirm_key': new_key})
    manager, servers, dns = current()
    assert manager.secret_key == new_key and servers[0]['name'] == 'vps'
    assert password(manager, dns) == 'p%ss' and dns['domains'][0]['records']
    assert servers[0]['ssh_credentials']['password_decrypted'] == 'ssh'
    assert os.path.exists(os.path.join(client.application.config['APP_DATA_DIR'], '.env'))


def test_failed_key_change_keeps_old_key(env, monkeypatch):
    client, _ = env
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    old_key = registry.get('data_manager').secret_key
    monkeypatch.setattr(DataManagerService, 'save_servers', lambda *a, **k: (_ for _ in ()).throw(OSError('disk full')))
    new_key = Fernet.generate_key().decode()
    client.post('/change_main_key', data={'new_key': new_key, 'confirm_key': new_key})
    assert registry.get('data_manager').secret_key == old_key
    assert client.application.config['SECRET_KEY'] == old_key
    assert not os.path.exists(os.path.join(client.application.config['APP_DATA_DIR'], '.env'))


def test_import_with_wrong_key_is_rejected_and_keeps_active_file(env, tmp_path):
    client, _ = env
    active = client.application.config['active_data_file']
    other = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    foreign = tmp_path / 'foreign.enc'
    other.save_servers([{'id': 1, 'name': 'x'}], str(foreign))
    client.post('/import_data', data={'data_file': (io.BytesIO(foreign.read_bytes()), 'foreign.enc')},
                content_type='multipart/form-data')
    assert client.application.config['active_data_file'] == active
    assert not list((tmp_path / 'data').glob('imported_*'))


def test_external_merge_skips_same_ip_under_another_name(env, tmp_path):
    client, _ = env
    other = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    foreign = tmp_path / 'foreign.enc'
    other.save_servers([{'id': 1, 'name': 'renamed', 'ip_address': '203.0.113.5'},
                        {'id': 2, 'name': 'new', 'ip_address': '203.0.113.9'}], str(foreign))
    client.post('/import_external_data', data={
        'external_file': (io.BytesIO(foreign.read_bytes()), 'foreign.enc'), 'external_key': other.secret_key},
        content_type='multipart/form-data')
    assert sorted(s['name'] for s in current()[1]) == ['new', 'vps']


def test_full_export_readme_explains_both_restore_paths(env):
    client, exports = env
    response = client.post('/export_package', data={'confirm_secret_export': 'yes'})
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        readme = archive.read('README.txt').decode()
    for text in ('карточка DNS', 'Импорт файла данных', 'Импорт серверов из другой установки',
                 'PIN этого компьютера', 'VPNServerManager-Clean'):
        assert text in readme


@pytest.mark.parametrize('lang,expected', [
    ('en', ['Data backup (recommended):', 'Restoring from a full export', 'VPNServerManager-Clean</code>', 'App data folder:']),
    ('zh', ['数据备份（推荐）：', '从完整导出恢复']),
])
def test_help_explains_backup_and_restore(env, lang, expected):
    client, _ = env
    text = client.get('/help?lang=' + lang).text
    for item in expected:
        assert item in text


@pytest.mark.parametrize('route', ['/export_key', '/export_package'])
def test_secret_export_requires_post_confirmation_csrf_and_auth(env, route):
    client, exports = env
    assert client.get(route).status_code == 405
    assert client.post(route).status_code == 400
    assert client.post(route, data={'confirm_secret_export': 'yes'}, csrf=False).status_code == 403
    for flags in ({'authenticated': False, 'pin_verified': False},
                  {'authenticated': True, 'pin_verified': False, 'pin_authenticated': False}):
        with client.session_transaction() as session:
            session.update(flags)
        result = client.post(route, data={'confirm_secret_export': 'yes'})
        assert result.status_code in (302, 401, 403)
        assert 'attachment' not in result.headers.get('Content-Disposition', '')
    assert not list(exports.iterdir())


@pytest.mark.parametrize('route', ['/export_key', '/export_package'])
def test_secret_export_no_disk_copy_or_fixed_session_key(env, route):
    client, exports = env
    response = client.post(route, data={'confirm_secret_export': 'yes'})
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert not list(exports.iterdir())
    if route == '/export_package':
        assert 'UNENCRYPTED_SECRETS_' in response.headers['Content-Disposition']
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            assert 'PIN.txt' not in archive.namelist()
            raw = archive.read('SECRET_KEY.env')
    else:
        raw = response.data
    assert raw == f'SECRET_KEY={registry.get("data_manager").secret_key}\n'.encode()
    assert b'FLASK_SECRET_KEY' not in raw


def test_package_restores_in_clean_profile_with_exported_key(env, tmp_path):
    client, _ = env
    response = client.post('/export_package', data={'confirm_secret_export': 'yes'})
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        key = archive.read('SECRET_KEY.env').decode().strip().split('=', 1)[1]
        raw = archive.read(next(n for n in archive.namelist() if n.endswith('.enc')))
    clean = tmp_path / 'clean-profile'
    clean.mkdir()
    manager = DataManagerService(key, str(clean))
    registry.register('data_manager', manager)
    client.application.config.update(APP_DATA_DIR=str(clean), active_data_file=None)
    response = client.post('/restore_backup', data={
        'backup_file': (io.BytesIO(raw), 'copy.enc'), 'confirm_restore': 'yes'})
    assert response.status_code == 302
    manager, servers, dns = current()
    assert servers[0]['ssh_credentials']['password_decrypted'] == 'ssh'
    assert dns['domains'][0]['name'] == 'example.com'
    assert password(manager, dns) == 'p%ss'


def test_package_skips_symlink_attachments(env, tmp_path):
    client, _ = env
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    outside = tmp_path / 'unrelated-secret'
    outside.write_text('not-an-attachment')
    (uploads / 'linked.txt').symlink_to(outside)
    (uploads / 'icon.txt').write_text('fixture')
    response = client.post('/export_package', data={'confirm_secret_export': 'yes'})
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert 'uploads/linked.txt' not in archive.namelist()
        assert archive.read('uploads/icon.txt') == b'fixture'
