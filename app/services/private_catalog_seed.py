"""Load an optional, locally bundled catalog seed without putting user data in source."""
import hashlib
from pathlib import Path
import sys

from . import catalog_transfer
from .config_io import read_config, write_config
from .profile_transaction import profile_lock

SEED_MARKER = '_private_catalog_seed_sha256'


def _seed_path():
    bundle = getattr(sys, '_MEIPASS', None)
    return Path(bundle) / 'private' / 'user_catalogs.json' if bundle else None


def seed_private_catalogs(app):
    """Apply a build-time private seed once per seed version, preserving other rows."""
    seed_path = _seed_path()
    if seed_path is None or seed_path.is_symlink() or not seed_path.is_file():
        return False
    raw = seed_path.read_bytes()
    incoming = catalog_transfer._parse(raw)
    if set(incoming) != set(catalog_transfer.CATALOGS):
        raise catalog_transfer.CatalogTransferError('private_seed_incomplete')
    digest = hashlib.sha256(raw).hexdigest()

    app_data_dir = Path(app.config['APP_DATA_DIR'])
    path = app_data_dir / 'config.json'
    with profile_lock(app_data_dir):
        config = read_config(path)
        if config.get(SEED_MARKER) == digest:
            return False

        for kind in catalog_transfer.CATALOGS:
            config_key = catalog_transfer.CATALOGS[kind][0]
            current = catalog_transfer._clean(kind, config.get(config_key, []))
            # The private seed supplies missing historical rows; a local same-name
            # row may already contain the user's edits, so retain that version.
            merged = catalog_transfer._merge(kind, incoming[kind], current)
            stored, _ = catalog_transfer._stored(kind, merged)
            config[config_key] = stored
        config[SEED_MARKER] = digest

        ui = config.get('ui')
        if not isinstance(ui, dict):
            ui = {}
        if not isinstance(ui.get('features'), dict):
            from .ui_preferences import DEFAULT_FEATURES
            ui['features'] = {**DEFAULT_FEATURES, 'projects': True, 'bots': True}
        config['ui'] = ui
        write_config(path, config)
        return True
