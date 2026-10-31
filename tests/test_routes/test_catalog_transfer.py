import io
import json

from cryptography.fernet import Fernet

from app.services import registry
from app.services.config_io import read_config, write_config
from app.services.data_manager_service import DataManagerService


def prepare(app, client):
    manager = DataManagerService(Fernet.generate_key().decode(), app.config['APP_DATA_DIR'])
    config_path = app.config['APP_DATA_DIR'] + '/config.json'
    config = read_config(config_path)
    config.update({
        'tracked_projects': [{'name': 'Local project', 'units': ['local-project']}],
        'tracked_bots': [{'name': 'Local bot', 'units': ['local-bot']}],
        'private_setting': 'never-export',
    })
    write_config(config_path, config)
    registry.register('data_manager', manager)
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, csrf_token='catalog-csrf')
    return manager


def catalog_file(projects=None, bots=None):
    return json.dumps({
        'format': 'vpnservermanager-catalogs',
        'version': 1,
        'catalogs': {'projects': projects or [], 'bots': bots or []},
    }).encode()


def import_form(raw, *, projects='yes', bots='yes', mode='merge', confirm='yes', filename='catalogs.json'):
    return {
        'catalog_file': (io.BytesIO(raw), filename),
        'import_projects': projects,
        'import_bots': bots,
        'catalog_mode': mode,
        'confirm_catalog_import': confirm,
    }


def test_settings_shows_cross_platform_catalog_transfer(app, client):
    prepare(app, client)

    page = client.get('/settings')

    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'vpnservermanager-catalogs' not in html
    assert 'export_catalogs' in html and 'import_catalogs' in html
    assert 'catalogMerge' in html and 'catalogReplace' in html
    assert 'exportCatalogProjects' in html and 'exportCatalogBots' in html


def test_export_downloads_only_selected_catalogs_without_profile_secrets(app, client):
    prepare(app, client)

    response = client.post('/export_catalogs', data={
        'include_projects': 'yes',
    })

    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'attachment' in response.headers['Content-Disposition']
    payload = json.loads(response.data)
    assert [row['name'] for row in payload['catalogs']['projects']] == ['Local project']
    assert 'bots' not in payload['catalogs']
    assert b'never-export' not in response.data


def test_import_merges_only_checked_catalog_and_keeps_other_profile_settings(app, client):
    prepare(app, client)
    raw = catalog_file(
        projects=[{'name': 'Remote project', 'units': ['remote-project']}],
        bots=[{'name': 'Remote bot', 'units': ['remote-bot']}],
    )

    response = client.post('/import_catalogs', data=import_form(raw, projects='yes', bots='', mode='merge'))

    assert response.status_code == 302
    saved = read_config(app.config['APP_DATA_DIR'] + '/config.json')
    assert [row['name'] for row in saved['tracked_projects']] == ['Local project', 'Remote project']
    assert [row['name'] for row in saved['tracked_bots']] == ['Local bot']
    assert saved['private_setting'] == 'never-export'


def test_import_can_replace_one_list_without_touching_the_other(app, client):
    prepare(app, client)
    raw = catalog_file(projects=[{'name': 'New project', 'units': ['new-project']}],
                       bots=[{'name': 'New bot', 'units': ['new-bot']}])

    client.post('/import_catalogs', data=import_form(raw, projects='', bots='yes', mode='replace'))

    saved = read_config(app.config['APP_DATA_DIR'] + '/config.json')
    assert [row['name'] for row in saved['tracked_projects']] == ['Local project']
    assert [row['name'] for row in saved['tracked_bots']] == ['New bot']


def test_invalid_or_unconfirmed_catalog_import_changes_nothing(app, client):
    prepare(app, client)
    before = (read_config(app.config['APP_DATA_DIR'] + '/config.json'))

    client.post('/import_catalogs', data=import_form(b'broken', confirm=''))

    after = read_config(app.config['APP_DATA_DIR'] + '/config.json')
    assert after == before
    assert client.post('/import_catalogs', data={}, csrf=False).status_code == 403


def test_catalog_transfer_requires_auth_and_pin(client):
    assert client.post('/export_catalogs').status_code in (302, 401)
    assert client.post('/import_catalogs').status_code in (302, 401)
