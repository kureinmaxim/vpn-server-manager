import io
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.services import registry
from app.services.data_manager_service import DataManagerService
from app.services.vault_io import VaultConflict


@pytest.fixture
def receipts(app, client, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    vault = tmp_path / 'servers.enc'
    manager.save_servers([{'id': 1, 'name': 'Example', 'ip_address': '192.0.2.1'},
                          {'id': 2, 'name': 'Other', 'ip_address': '192.0.2.2'}], str(vault))
    registry.register('data_manager', manager)
    app.config.update(APP_DATA_DIR=str(tmp_path), active_data_file=str(vault),
                      UPLOAD_FOLDER=str(tmp_path / 'uploads'))
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, pin_authenticated=True)
    return manager, vault


def upload(client, **kwargs):
    return client.post('/server/1/receipts/add', data={
        'description': '<b>synthetic receipt</b>',
        'receipt_file': (io.BytesIO(b'%PDF-1.4\nsynthetic\n'), 'receipt.pdf')}, **kwargs)


def test_receipt_round_trip_and_private_download(client, app, receipts):
    result = upload(client)
    assert result.status_code == 200
    item = result.json
    url = '/server/1/receipts/file/' + item['filename']
    download = client.get(url)
    assert download.data == b'%PDF-1.4\nsynthetic\n'
    assert download.headers['Cache-Control'] == 'no-store'
    assert 'attachment' in download.headers['Content-Disposition']
    assert client.get('/server/2/receipts/file/' + item['filename']).status_code == 404
    assert client.get('/uploads/' + item['filename']).status_code == 404
    assert len(receipts[0].load_servers(app.config)[0]['payment_info']['receipts']) == 1
    assert client.post('/server/1/receipts/delete/' + item['filename']).status_code == 200
    assert client.get(url).status_code == 404
    assert not list((Path(app.config['UPLOAD_FOLDER']) / 'receipts').iterdir())


@pytest.mark.parametrize('flag', ['authenticated', 'pin_verified'])
def test_receipts_require_access(client, receipts, flag):
    item = upload(client).json
    with client.session_transaction() as state:
        state[flag] = False
    assert upload(client).status_code == 401
    assert client.get('/server/1/receipts/file/' + item['filename']).status_code == 401
    assert client.post('/server/1/receipts/delete/' + item['filename']).status_code == 401


def test_csrf_and_save_failure_preserve_inventory(client, app, receipts, monkeypatch):
    manager, vault = receipts
    before = vault.read_bytes()
    assert upload(client, csrf=False).status_code == 403
    def conflict(*args, **kwargs):
        raise VaultConflict('synthetic')
    monkeypatch.setattr(manager, 'save_servers', conflict)
    assert upload(client).status_code == 409
    assert vault.read_bytes() == before
    assert not list((Path(app.config['UPLOAD_FOLDER']) / 'receipts').iterdir())


def test_delete_failure_keeps_file(client, app, receipts, monkeypatch):
    item = upload(client).json
    def conflict(*args, **kwargs):
        raise VaultConflict('synthetic')
    monkeypatch.setattr(receipts[0], 'save_servers', conflict)
    assert client.post('/server/1/receipts/delete/' + item['filename']).status_code == 409
    assert client.get('/server/1/receipts/file/' + item['filename']).status_code == 200


def test_rejects_unsafe_empty_or_unowned_uploads(client, app, receipts):
    for filename, content in [('script.html', b'<script>'), ('receipt.pdf', b'')]:
        response = client.post('/server/1/receipts/add', data={
            'description': 'test', 'receipt_file': (io.BytesIO(content), filename)})
        assert response.status_code == 400
    item = upload(client).json
    endpoint = '/server/1/receipts/delete/' + item['filename']
    assert client.post(endpoint, csrf=False).status_code == 403
    assert client.post('/server/2/receipts/delete/' + item['filename']).status_code == 404
    assert client.get('/server/1/receipts/file/' + item['filename']).status_code == 200


def test_unicode_receipt_name_is_preserved(client, receipts):
    response = client.post('/server/1/receipts/add', data={
        'description': 'Test', 'receipt_file': (io.BytesIO(b'%PDF-1.4'), 'чек.pdf')})
    assert response.status_code == 200
    assert response.json['original_name'] == 'чек.pdf'
    assert response.json['filename'].endswith('.pdf')
