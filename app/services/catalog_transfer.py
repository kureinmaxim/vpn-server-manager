"""Portable export/import for the non-secret project and bot catalogs."""
from datetime import datetime, timezone
import json
from pathlib import Path

from .bot_stats import BotError, clean_bots
from .config_io import read_config, write_config
from .profile_transaction import profile_lock
from .project_stats import ProjectError, clean_projects

FORMAT = 'vpnservermanager-catalogs'
VERSION = 1
MAX_BYTES = 2 * 1024 * 1024

CATALOGS = {
    'projects': ('tracked_projects', clean_projects, ('name', 'units', 'containers', 'processes')),
    'bots': ('tracked_bots', clean_bots,
             ('name', 'units', 'containers', 'processes', 'commands', 'tasks',
              'health_url', 'health_word', 'service')),
}


class CatalogTransferError(ValueError):
    """Safe catalog transfer validation failure with a stable reason code."""


def _clean(kind, rows):
    _, cleaner, fields = CATALOGS[kind]
    try:
        return [{field: row[field] for field in fields} for row in cleaner(rows or [])]
    except (ProjectError, BotError, KeyError, TypeError) as exc:
        raise CatalogTransferError('invalid_catalog') from exc


def export(manager, runtime_config, include):
    selected = [kind for kind in CATALOGS if include.get(kind)]
    if not selected:
        raise CatalogTransferError('nothing_selected')

    path = Path(manager.app_data_dir) / 'config.json'
    with profile_lock(manager.app_data_dir):
        manager._check_profile_generation()
        config = read_config(path)
        for key in ('active_data_file',):
            if key in config:
                saved = manager.get_active_data_path(config)
                runtime = manager.get_active_data_path(runtime_config)
                if saved != runtime:
                    from .vault_io import canonical, VaultConflict
                    if (canonical(saved) if saved else None) != (canonical(runtime) if runtime else None):
                        raise VaultConflict('Active vault changed; reload before exporting')
        catalogs = {
            kind: _clean(kind, config.get(CATALOGS[kind][0], []))
            for kind in selected
        }
        payload = {
            'format': FORMAT,
            'version': VERSION,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'catalogs': catalogs,
        }
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise CatalogTransferError('catalog_too_large')
    return raw


def _parse(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise CatalogTransferError('catalog_too_large')
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError) as exc:
        raise CatalogTransferError('invalid_file') from exc
    if (not isinstance(payload, dict) or payload.get('format') != FORMAT or
            payload.get('version') != VERSION or not isinstance(payload.get('catalogs'), dict)):
        raise CatalogTransferError('unsupported_format')

    imported = {}
    for kind in CATALOGS:
        if kind in payload['catalogs']:
            rows = payload['catalogs'][kind]
            if not isinstance(rows, list):
                raise CatalogTransferError('invalid_catalog')
            imported[kind] = _clean(kind, rows)
    if not imported:
        raise CatalogTransferError('no_catalogs')
    return imported


def _merge(kind, current, incoming):
    rows = _clean(kind, current)
    positions = {row['name'].casefold(): index for index, row in enumerate(rows)}
    for row in incoming:
        identity = row['name'].casefold()
        if identity in positions:
            rows[positions[identity]] = row
        else:
            positions[identity] = len(rows)
            rows.append(row)
    return _clean(kind, rows)


def _stored(kind, rows):
    config_key, _cleaner, fields = CATALOGS[kind]
    return [{field: row[field] for field in fields} for row in rows], config_key


def import_catalogs(manager, raw, *, selected, mode='merge'):
    """Apply selected lists under the profile lock; same-name imported rows win in merge mode."""
    kinds = [kind for kind in CATALOGS if selected.get(kind)]
    if not kinds:
        raise CatalogTransferError('nothing_selected')
    if mode not in ('merge', 'replace'):
        raise CatalogTransferError('invalid_mode')
    imported = _parse(raw)
    if any(kind not in imported for kind in kinds):
        raise CatalogTransferError('selected_catalog_missing')

    path = Path(manager.app_data_dir) / 'config.json'
    with profile_lock(manager.app_data_dir):
        manager._check_profile_generation()
        config = read_config(path)
        applied = {}
        for kind in kinds:
            config_key, cleaner, _fields = CATALOGS[kind]
            current = config.get(config_key, [])
            incoming = imported[kind]
            rows = _merge(kind, current, incoming) if mode == 'merge' else _clean(kind, incoming)
            stored, _ = _stored(kind, rows)
            config[config_key] = stored
            applied[kind] = rows
        try:
            write_config(path, config)
        except Exception:
            # Atomic replace may have committed before a directory fsync error.
            committed = read_config(path)
            if any(committed.get(CATALOGS[kind][0]) != _stored(kind, rows)[0]
                   for kind, rows in applied.items()):
                raise
        return {kind: len(rows) for kind, rows in applied.items()}
