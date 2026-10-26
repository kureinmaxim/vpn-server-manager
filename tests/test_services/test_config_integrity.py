import pytest
from app.services.config_io import read_config, write_config
from app.services.vault_io import VaultConflict, VaultError
from app.services.ui_preferences import _read_config, _write_config


def test_two_config_writers_cannot_lose_settings(tmp_path):
    path = str(tmp_path / 'config.json')
    first, second = read_config(path), read_config(path)
    first['ui'] = {'zoom': '100'}
    write_config(path, first)
    second['tracked_bots'] = []
    with pytest.raises(VaultConflict):
        write_config(path, second)
    assert read_config(path)['ui'] == {'zoom': '100'}


def test_corrupt_config_defaults_are_never_saved(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text('{broken')
    with pytest.raises(VaultError):
        read_config(str(path))
    fallback = _read_config(str(path))
    fallback['ui'] = {}
    assert _write_config(str(path), fallback) is False
    assert path.read_text() == '{broken'
