"""Icon picker: save from the form and capture a screen region."""

import base64
from io import BytesIO

from PIL import Image

from app.services import registry


def _png_data_url():
    buf = BytesIO()
    Image.new('RGB', (40, 24), (10, 80, 200)).save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def _auth(client):
    with client.session_transaction() as sess:
        sess['authenticated'] = True
        sess['pin_authenticated'] = True
        sess['pin_verified'] = True


def test_icon_snip_returns_data_url(client, monkeypatch):
    buf = BytesIO()
    Image.new('RGB', (12, 12), (255, 0, 0)).save(buf, format='PNG')
    png = buf.getvalue()
    monkeypatch.setattr('desktop.snip.capture_region', lambda: png)
    _auth(client)
    response = client.post('/api/icon-snip')
    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True
    assert body['data'].startswith('data:image/png;base64,')
    assert base64.b64decode(body['data'].split(',', 1)[1]) == png


def test_icon_snip_cancelled(client, monkeypatch):
    monkeypatch.setattr('desktop.snip.capture_region', lambda: None)
    _auth(client)
    response = client.post('/api/icon-snip')
    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is False
    assert body['cancelled'] is True


def test_edit_server_saves_icon_payload(client, app, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)

    class StubDataManager:
        def __init__(self):
            self.servers = [{
                'id': '1',
                'name': 'Test',
                'provider': '',
                'ip_address': '127.0.0.1',
                'os': '',
                'status': 'Active',
                'notes': '',
                'docker_info': '',
                'software_info': '',
                'card_color': '#ffc107',
                'icon_filename': '',
                'panel_url': '',
                'hoster_url': '',
                'specs': {'cpu': '', 'ram': '', 'disk': ''},
                'payment_info': {
                    'amount': 0.0, 'currency': 'USD',
                    'next_due_date': '', 'payment_period': 'Monthly',
                },
                'ssh_credentials': {
                    'user': 'root', 'port': 22, 'root_login_allowed': False,
                    'password': 'old', 'password_decrypted': 'old',
                    'root_password': '', 'root_password_decrypted': '',
                },
                'panel_credentials': {
                    'user': '', 'user_decrypted': '',
                    'password': '', 'password_decrypted': '',
                },
                'hoster_credentials': {
                    'login_method': 'password',
                    'user': '', 'user_decrypted': '',
                    'password': '', 'password_decrypted': '',
                },
                'checks': {'dns_ok': False, 'streaming_ok': False},
            }]
            self.saved_servers = None

        def load_servers(self, config):
            return self.servers

        def get_active_data_path(self, config):
            return 'test-data.enc'

        def save_servers(self, servers, file_path):
            self.saved_servers = servers

        def encrypt_data(self, data):
            return f'enc::{data}'

    manager = StubDataManager()
    registry.register('data_manager', manager)
    _auth(client)
    response = client.post(
        '/edit_server/1',
        data={'server_icon_data': _png_data_url()},
        follow_redirects=False,
    )
    assert response.status_code == 302
    saved = manager.saved_servers[0]['icon_filename']
    assert saved.startswith('icon_1_')
    assert saved.endswith('.png')
    assert (tmp_path / saved).is_file()
