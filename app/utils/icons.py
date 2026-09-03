"""Normalize uploaded or captured server icons to a square PNG."""
from __future__ import annotations

import base64
import io
import os
import re
from datetime import datetime

from PIL import Image, UnidentifiedImageError

ICON_SIZE = 128
_DATA_URL_RE = re.compile(r'^data:image/[^;]+;base64,', re.IGNORECASE)


def decode_icon_payload(value: str) -> bytes:
    """Decode a data URL or raw base64 payload into image bytes."""
    if not value or not str(value).strip():
        raise ValueError('empty icon payload')
    text = _DATA_URL_RE.sub('', str(value).strip())
    try:
        data = base64.b64decode(text, validate=False)
    except Exception as exc:
        raise ValueError('invalid icon payload') from exc
    if not data:
        raise ValueError('empty icon payload')
    return data


def process_icon_bytes(data: bytes) -> bytes:
    """Center-crop to square and return a PNG of ICON_SIZE pixels."""
    if not data:
        raise ValueError('empty image')
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError('not an image') from exc

    image = image.convert('RGBA')
    width, height = image.size
    if width < 1 or height < 1:
        raise ValueError('empty image')

    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    image.save(out, format='PNG', optimize=True)
    return out.getvalue()


def _delete_old_icon(upload_folder: str, old_filename: str | None) -> None:
    if not old_filename:
        return
    path = os.path.join(upload_folder, old_filename)
    if os.path.isfile(path):
        os.remove(path)


def save_server_icon(
    upload_folder: str,
    server_id,
    image_bytes: bytes,
    old_filename: str | None = None,
) -> str:
    """Write a processed PNG and remove the previous icon file if present."""
    os.makedirs(upload_folder, exist_ok=True)
    png = process_icon_bytes(image_bytes)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f'icon_{server_id}_{timestamp}.png'
    with open(os.path.join(upload_folder, filename), 'wb') as handle:
        handle.write(png)
    if old_filename and old_filename != filename:
        _delete_old_icon(upload_folder, old_filename)
    return filename


def apply_icon_from_form(
    form,
    files,
    upload_folder: str,
    server_id,
    old_filename: str | None = None,
) -> str | None:
    """Apply icon changes from an add/edit form. None means the icon was cleared."""
    form = form or {}
    files = files or {}
    if str(form.get('remove_icon') or '').lower() in ('1', 'true', 'on', 'yes'):
        _delete_old_icon(upload_folder, old_filename)
        return None

    payload = str(form.get('server_icon_data') or '').strip()
    if payload:
        return save_server_icon(
            upload_folder,
            server_id,
            decode_icon_payload(payload),
            old_filename,
        )

    upload = files.get('server_icon') if hasattr(files, 'get') else None
    filename = getattr(upload, 'filename', None) if upload is not None else None
    if upload is not None and filename:
        data = upload.read()
        if data:
            return save_server_icon(upload_folder, server_id, data, old_filename)

    return old_filename
