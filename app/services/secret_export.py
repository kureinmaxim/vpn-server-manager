"""Explicitly unencrypted portable export; no intermediate disk copies."""
from io import BytesIO
from pathlib import Path
import zipfile

from . import backup_service
from . import catalog_transfer
from .profile_transaction import profile_lock


def package(manager, config, timestamp, readme):
    with profile_lock(manager.app_data_dir):
        manager._check_profile_generation()
        selected = manager.get_active_data_path(config)
        backup_service._selection(manager, selected)
        raw = Path(selected).read_bytes()
        backup_service.validate(manager, raw)
        catalogs = catalog_transfer.export(
            manager, config, {'projects': True, 'bots': True})
        output = BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f'servers_{timestamp}.enc', raw)
            archive.writestr('SECRET_KEY.env', f'SECRET_KEY={manager.secret_key}\n')
            archive.writestr('catalogs.json', catalogs)
            # PIN is a local UI lock; it is not required to restore the inventory.
            uploads = Path(manager.app_data_dir) / 'uploads'
            if uploads.is_dir() and not uploads.is_symlink():
                for path in uploads.iterdir():
                    if path.is_file() and not path.is_symlink():
                        archive.write(path, f'uploads/{path.name}')
            archive.writestr('README.txt', readme)
        return output.getvalue()
