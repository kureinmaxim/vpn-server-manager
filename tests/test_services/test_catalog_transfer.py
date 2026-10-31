import json

import pytest
from cryptography.fernet import Fernet

from app.services import catalog_transfer
from app.services.config_io import read_config, write_config
from app.services.data_manager_service import DataManagerService


def make_profile(tmp_path, projects=None, bots=None):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    config_path = tmp_path / 'config.json'
    config = read_config(config_path)
    config.update({
        'tracked_projects': projects or [],
        'tracked_bots': bots or [],
        'unrelated_setting': 'keep-me',
    })
    write_config(config_path, config)
    return manager


def package(catalogs):
    return json.dumps({
        'format': catalog_transfer.FORMAT,
        'version': catalog_transfer.VERSION,
        'catalogs': catalogs,
    }).encode()


def test_export_contains_only_selected_sanitized_catalogs(tmp_path):
    manager = make_profile(tmp_path, projects=[{
        'name': 'Blog', 'units': ['blog'], 'containers': [], 'processes': [], 'password': 'never-export',
    }], bots=[{'name': 'Worker', 'units': ['worker']}])

    raw = catalog_transfer.export(manager, {}, {'projects': True, 'bots': False})
    payload = json.loads(raw)

    assert payload['format'] == catalog_transfer.FORMAT
    assert payload['version'] == catalog_transfer.VERSION
    assert [row['name'] for row in payload['catalogs']['projects']] == ['Blog']
    assert 'bots' not in payload['catalogs']
    assert b'never-export' not in raw
    assert b'keep-me' not in raw


def test_export_requires_at_least_one_catalog(tmp_path):
    manager = make_profile(tmp_path)
    with pytest.raises(catalog_transfer.CatalogTransferError, match='nothing_selected'):
        catalog_transfer.export(manager, {}, {'projects': False, 'bots': False})


def test_import_merge_keeps_other_entries_and_updates_same_name(tmp_path):
    manager = make_profile(tmp_path,
                           projects=[{'name': 'Blog', 'units': ['old-blog']}, {'name': 'Local', 'units': ['local']}],
                           bots=[{'name': 'Local bot', 'units': ['local-bot']}])
    raw = package({'projects': [
        {'name': 'blog', 'units': ['new-blog']}, {'name': 'Remote', 'containers': ['remote-app']},
    ], 'bots': [{'name': 'Remote bot', 'containers': ['remote-bot']}]})

    counts = catalog_transfer.import_catalogs(
        manager, raw, selected={'projects': True, 'bots': False}, mode='merge'
    )

    saved = read_config(tmp_path / 'config.json')
    assert counts == {'projects': 3}
    assert [(row['name'], row['units'], row['containers']) for row in saved['tracked_projects']] == [
        ('blog', ['new-blog'], []), ('Local', ['local'], []), ('Remote', [], ['remote-app']),
    ]
    assert [row['name'] for row in saved['tracked_bots']] == ['Local bot']
    assert saved['unrelated_setting'] == 'keep-me'


def test_import_replace_only_changes_selected_catalogs(tmp_path):
    manager = make_profile(tmp_path, projects=[{'name': 'Keep project', 'units': ['keep']}],
                           bots=[{'name': 'Old bot', 'units': ['old']}])
    raw = package({'projects': [{'name': 'Incoming project', 'units': ['incoming']}],
                   'bots': [{'name': 'Incoming bot', 'units': ['incoming-bot']}]})

    counts = catalog_transfer.import_catalogs(
        manager, raw, selected={'projects': False, 'bots': True}, mode='replace'
    )

    saved = read_config(tmp_path / 'config.json')
    assert counts == {'bots': 1}
    assert [row['name'] for row in saved['tracked_projects']] == ['Keep project']
    assert [row['name'] for row in saved['tracked_bots']] == ['Incoming bot']


@pytest.mark.parametrize('raw,selected,mode,reason', [
    (b'not json', {'projects': True}, 'merge', 'invalid_file'),
    (package({'bots': []}), {'projects': True}, 'merge', 'selected_catalog_missing'),
    (package({'projects': [{'name': 'Invalid', 'units': ['bad; command']}]}),
     {'projects': True}, 'merge', 'invalid_catalog'),
    (package({'projects': []}), {'projects': True}, 'unknown', 'invalid_mode'),
    (package({'projects': []}), {'projects': False, 'bots': False}, 'merge', 'nothing_selected'),
])
def test_invalid_import_preserves_profile(tmp_path, raw, selected, mode, reason):
    manager = make_profile(tmp_path, projects=[{'name': 'Keep', 'units': ['keep']}],
                           bots=[{'name': 'Keep bot', 'units': ['keep-bot']}])
    before = (tmp_path / 'config.json').read_bytes()

    with pytest.raises(catalog_transfer.CatalogTransferError, match=reason):
        catalog_transfer.import_catalogs(manager, raw, selected=selected, mode=mode)

    assert (tmp_path / 'config.json').read_bytes() == before
