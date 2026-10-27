"""Synthetic packaged-profile checks; refuse to operate outside a marked temp HOME."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

MARKER = 'VPN Server Manager disposable build fixture\n'


def checked_home():
    home = Path(os.environ.get('HOME', '')).resolve()
    temporary = Path(tempfile.gettempdir()).resolve()
    if (not getattr(sys, 'frozen', False) or home.parent.parent != temporary
            or not home.parent.name.startswith('vsm-install-')
            or not (home / '.vsm-build-fixture').is_file()
            or (home / '.vsm-build-fixture').read_text() != MARKER):
        raise RuntimeError('Profile smoke requires a marked disposable HOME and a frozen executable')
    return home


def run(phase):
    home = checked_home()  # Must precede app imports, which create the frozen profile.
    if phase not in ('seed', 'verify', 'restore'):
        raise ValueError('Unknown profile smoke phase')
    from app import create_app
    from app.services import registry
    app = create_app('production')
    profile = home / 'Library/Application Support/VPNServerManager-Clean'
    if Path(app.config['APP_DATA_DIR']).resolve() != profile:
        raise RuntimeError('Unexpected profile location')
    manager = registry.get('data_manager')
    if manager is None:
        raise RuntimeError('Fresh profile encryption service unavailable')
    client = app.test_client()
    if client.get('/locked').status_code != 200:
        raise RuntimeError('Packaged templates did not render')
    fixture = home / 'fixture.json'
    if phase == 'seed':
        if fixture.exists():
            raise RuntimeError('Fixture already exists')
        path = profile / 'data/synthetic.enc'
        path.parent.mkdir(exist_ok=True)
        # Historical list-only payload: migration must preserve credentials and fields.
        rows = [{'id': 1, 'name': 'Build fixture', 'ip_address': '192.0.2.10',
                 'ssh_credentials': {'user': 'operator', 'port': 2222,
                                     'password': manager.encrypt_data('synthetic-only')}}]
        path.write_bytes(manager.fernet.encrypt(json.dumps(rows).encode()))
        migrated = manager.load_servers({'active_data_file': str(path)})
        manager.save_servers(migrated, str(path), dns={'domains': [
            {'id': 'fixture', 'name': 'example.com', 'records': []}]})
        if not manager.update_user_config({'active_data_file': str(path)}):
            raise RuntimeError('Profile config was not persisted')
        backup = manager.create_backup(str(path), str(profile / 'backups'))
        fixture.write_text(json.dumps({'backup': backup, 'vault': str(path),
                                      'env_hash': hashlib.sha256((profile / '.env').read_bytes()).hexdigest()}))
        app.config['active_data_file'] = str(path)
    state = json.loads(fixture.read_text())
    if hashlib.sha256((profile / '.env').read_bytes()).hexdigest() != state['env_hash']:
        raise RuntimeError('Profile key file changed across startup')
    if phase == 'restore':
        old_path = Path(app.config['active_data_file'])
        old_bytes = old_path.read_bytes()
        with client.session_transaction() as session:
            session.update(authenticated=True, pin_verified=True, csrf_token='build-fixture-token')
        def upload(raw):
            return client.post('/import_data', data={'data_file': (io.BytesIO(raw), 'backup.enc')},
                               headers={'X-CSRF-Token': 'build-fixture-token'})
        if upload(b'broken fixture').status_code != 302 or app.config['active_data_file'] != str(old_path):
            raise RuntimeError('Invalid backup changed active data')
        if upload(Path(state['backup']).read_bytes()).status_code != 302:
            raise RuntimeError('Backup import failed')
        if app.config['active_data_file'] == str(old_path) or old_path.read_bytes() != old_bytes:
            raise RuntimeError('Restore did not preserve the original vault')
    rows = manager.load_servers(app.config)
    dns = manager.load_dns(app.config)
    if (len(rows) != 1 or rows[0]['name'] != 'Build fixture'
            or rows[0]['ssh_credentials']['password_decrypted'] != 'synthetic-only'
            or dns['domains'][0]['name'] != 'example.com'):
        raise RuntimeError('Synthetic inventory did not survive startup/restore')
    persisted = json.loads((profile / 'config.json').read_text())
    if persisted['active_data_file'] != app.config['active_data_file']:
        raise RuntimeError('Active vault was not persisted')
    print('VSM_PROFILE_SMOKE=' + json.dumps({'phase': phase, 'status': 'passed'}))
