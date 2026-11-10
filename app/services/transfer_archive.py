"""Файл переноса на другой компьютер: защита паролем и восстановление одним действием.

Архив собирает secret_export.package(): файл данных, его ключ, списки проектов и ботов,
иконки. Здесь две вещи поверх него:

- seal()/unseal(): тот же архив, зашифрованный паролем. Ключ выводится scrypt из пароля и
  случайной соли, поэтому флешка с файлом без пароля бесполезна.
- restore(): разбирает архив и добавляет его содержимое в текущий профиль через уже
  существующие операции объединения. Ключ профиля не заменяется, имеющиеся записи не
  удаляются: на пустом профиле это полное восстановление, на непустом — добавление.

Архив — чужие данные: имена и размеры проверяются до любой записи.
"""
import base64
import hashlib
import os
import re
import zipfile
from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from werkzeug.utils import secure_filename

from . import catalog_transfer
from .external_import import merge_external_vault

MAGIC = b'VSMX1\n'
SALT_BYTES = 16
MIN_PASSPHRASE = 8
MAX_UNPACKED = 128 * 1024 * 1024
MAX_UPLOAD = 16 * 1024 * 1024
MAX_MEMBERS = 2000
_VAULT_NAME = re.compile(r'servers_[0-9_]{1,32}\.enc')


class TransferError(ValueError):
    """Код ошибки для сообщения пользователю; содержимое архива в текст не попадает."""


def _passphrase_key(passphrase, salt):
    raw = hashlib.scrypt(passphrase.encode('utf-8'), salt=salt, n=2 ** 15, r=8, p=1,
                         dklen=32, maxmem=2 ** 27)
    return base64.urlsafe_b64encode(raw)


def seal(archive, passphrase):
    """Зашифровать готовый архив паролем. Формат: метка, соль, токен Fernet."""
    if len(passphrase) < MIN_PASSPHRASE:
        raise TransferError('weak_passphrase')
    salt = os.urandom(SALT_BYTES)
    return MAGIC + salt + Fernet(_passphrase_key(passphrase, salt)).encrypt(archive)


def is_sealed(raw):
    return raw.startswith(MAGIC)


def unseal(raw, passphrase):
    if not passphrase:
        raise TransferError('passphrase_required')
    salt, token = raw[len(MAGIC):len(MAGIC) + SALT_BYTES], raw[len(MAGIC) + SALT_BYTES:]
    if len(salt) != SALT_BYTES or not token:
        raise TransferError('invalid_file')
    try:
        return Fernet(_passphrase_key(passphrase, salt)).decrypt(token)
    except InvalidToken as exc:
        raise TransferError('wrong_passphrase') from exc


def read(raw, passphrase=''):
    """Содержимое архива переноса: {'vault', 'key', 'catalogs', 'uploads'}; без записи на диск."""
    if is_sealed(raw):
        raw = unseal(raw, passphrase)
    try:
        archive = zipfile.ZipFile(BytesIO(raw))
    except (zipfile.BadZipFile, ValueError) as exc:
        raise TransferError('invalid_file') from exc
    with archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if len(members) > MAX_MEMBERS or sum(info.file_size for info in members) > MAX_UNPACKED:
            raise TransferError('too_large')
        vaults = [info for info in members if _VAULT_NAME.fullmatch(info.filename)]
        names = {info.filename for info in members}
        if len(vaults) != 1 or 'SECRET_KEY.env' not in names:
            raise TransferError('not_a_transfer')
        key = ''
        for line in archive.read('SECRET_KEY.env').decode('utf-8', 'replace').splitlines():
            if line.startswith('SECRET_KEY='):
                key = line[len('SECRET_KEY='):].strip()
        try:
            Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise TransferError('not_a_transfer') from exc
        uploads = {}
        for info in members:
            folder, _, name = info.filename.partition('/')
            # Только файлы прямо в uploads/ с именем, которое не уводит из каталога.
            if folder != 'uploads' or not name or name != secure_filename(name) or name.startswith('.'):
                continue
            if info.file_size > MAX_UPLOAD:
                raise TransferError('too_large')
            uploads[name] = archive.read(info)
        return {
            'vault': archive.read(vaults[0]),
            'key': key,
            'catalogs': archive.read('catalogs.json') if 'catalogs.json' in names else None,
            'uploads': uploads,
        }


def restore(manager, runtime_config, raw, passphrase=''):
    """Добавить содержимое архива в текущий профиль; вернуть, что именно добавлено.

    Порядок: сначала всё проверяется (пароль, структура, ключ, списки), потом пишется.
    Серверы и DNS объединяются с имеющимися, дубликаты пропускаются; секреты
    перешифровываются ключом этого профиля. Списки проектов и ботов объединяются по имени.
    Иконки копируются, если файла с таким именем ещё нет.
    """
    contents = read(raw, passphrase)
    catalogs = None
    if contents['catalogs'] is not None:
        try:
            catalogs = catalog_transfer._parse(contents['catalogs'])
        except catalog_transfer.CatalogTransferError as exc:
            raise TransferError('invalid_catalogs') from exc
    try:
        merged = merge_external_vault(manager, runtime_config, contents['vault'], contents['key'])
    except InvalidToken as exc:
        raise TransferError('not_a_transfer') from exc

    summary = dict(merged, projects=0, bots=0, icons=0)
    if catalogs:
        applied = catalog_transfer.import_catalogs(
            manager, contents['catalogs'], selected={kind: True for kind in catalogs}, mode='merge')
        summary['projects'] = applied.get('projects', 0)
        summary['bots'] = applied.get('bots', 0)

    folder = Path(manager.app_data_dir) / 'uploads'
    if contents['uploads'] and not folder.is_symlink():
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in contents['uploads'].items():
            try:
                with open(folder / name, 'xb') as handle:
                    handle.write(data)
                summary['icons'] += 1
            except FileExistsError:
                continue
    return summary
