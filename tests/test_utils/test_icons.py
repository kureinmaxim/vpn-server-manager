"""Server icons are always stored as a square PNG the card can display."""

import io
import os
from types import SimpleNamespace

import pytest
from PIL import Image

from app.utils.icons import (
    ICON_SIZE,
    apply_icon_from_form,
    decode_icon_payload,
    process_icon_bytes,
    save_server_icon,
)


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    width = int.from_bytes(data[16:20], 'big')
    height = int.from_bytes(data[20:24], 'big')
    return width, height


def _image_bytes(width: int, height: int, color=(220, 40, 40), fmt='JPEG') -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (width, height), color).save(buf, format=fmt)
    return buf.getvalue()


def test_process_icon_bytes_makes_square_png():
    png = process_icon_bytes(_image_bytes(200, 80, fmt='JPEG'))
    assert _png_size(png) == (ICON_SIZE, ICON_SIZE)
    image = Image.open(io.BytesIO(png))
    assert image.format == 'PNG'


def test_process_icon_bytes_keeps_transparency():
    buf = io.BytesIO()
    Image.new('RGBA', (40, 40), (0, 0, 0, 0)).save(buf, format='PNG')
    png = process_icon_bytes(buf.getvalue())
    image = Image.open(io.BytesIO(png))
    assert image.mode == 'RGBA'
    assert image.getpixel((0, 0))[3] == 0


def test_process_icon_bytes_rejects_garbage():
    with pytest.raises(ValueError):
        process_icon_bytes(b'not-an-image')


def test_decode_icon_payload_accepts_data_url_and_raw_base64():
    raw = _image_bytes(32, 32, fmt='PNG')
    import base64

    encoded = base64.b64encode(raw).decode('ascii')
    from_raw = decode_icon_payload(encoded)
    from_url = decode_icon_payload('data:image/png;base64,' + encoded)
    assert from_raw == raw
    assert from_url == raw


def test_save_server_icon_writes_png_and_replaces_old(tmp_path):
    old = tmp_path / 'icon_1_old.gif'
    old.write_bytes(b'old')
    filename = save_server_icon(
        str(tmp_path),
        server_id=7,
        image_bytes=_image_bytes(90, 40, fmt='JPEG'),
        old_filename='icon_1_old.gif',
    )
    assert filename.startswith('icon_7_')
    assert filename.endswith('.png')
    assert (tmp_path / filename).is_file()
    assert _png_size((tmp_path / filename).read_bytes()) == (ICON_SIZE, ICON_SIZE)
    assert not old.exists()


def test_apply_icon_from_form_uses_hidden_payload(tmp_path):
    import base64

    payload = base64.b64encode(_image_bytes(64, 32, fmt='PNG')).decode('ascii')
    form = {'server_icon_data': 'data:image/png;base64,' + payload}
    name = apply_icon_from_form(form, {}, str(tmp_path), server_id=3, old_filename=None)
    assert name.endswith('.png')
    assert (tmp_path / name).is_file()


def test_apply_icon_from_form_clears_icon(tmp_path):
    old = tmp_path / 'icon_3_old.png'
    old.write_bytes(_image_bytes(16, 16, fmt='PNG'))
    name = apply_icon_from_form(
        {'remove_icon': '1'},
        {},
        str(tmp_path),
        server_id=3,
        old_filename='icon_3_old.png',
    )
    assert name is None
    assert not old.exists()


def test_apply_icon_from_form_keeps_existing_when_unchanged(tmp_path):
    name = apply_icon_from_form({}, {}, str(tmp_path), server_id=1, old_filename='keep.png')
    assert name == 'keep.png'
    assert os.listdir(tmp_path) == []


def test_apply_icon_from_form_reads_uploaded_file(tmp_path):
    from werkzeug.datastructures import FileStorage

    upload = FileStorage(
        stream=io.BytesIO(_image_bytes(50, 20, fmt='JPEG')),
        filename='logo.jpg',
        content_type='image/jpeg',
    )
    name = apply_icon_from_form({}, {'server_icon': upload}, str(tmp_path), server_id=9, old_filename=None)
    assert name.endswith('.png')
    assert (tmp_path / name).is_file()
