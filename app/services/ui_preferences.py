"""Persistent UI preferences (language, zoom) in the user profile config.json."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ALLOWED_LANGUAGES = frozenset({'ru', 'en', 'zh'})
ALLOWED_ZOOMS = frozenset({'60', '80', '100'})
DEFAULT_LANGUAGE = 'en'
DEFAULT_ZOOM = '80'
UI_CONFIG_KEY = 'ui'


def _config_path(app) -> str:
    return os.path.join(app.config.get('APP_DATA_DIR', '.'), 'config.json')


def _read_config(path: str) -> Dict[str, Any]:
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning('Failed to read UI preferences from %s: %s', path, exc)
        return {}


def _write_config(path: str, data: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        return True
    except OSError as exc:
        logger.error('Failed to write UI preferences to %s: %s', path, exc)
        return False


def normalize_language(value: Optional[str], default: str = DEFAULT_LANGUAGE) -> str:
    language = (value or '').strip().lower()
    return language if language in ALLOWED_LANGUAGES else default


def normalize_zoom(value: Optional[str], default: str = DEFAULT_ZOOM) -> str:
    zoom = str(value or '').strip()
    if zoom.endswith('%'):
        zoom = zoom[:-1]
    return zoom if zoom in ALLOWED_ZOOMS else default


def load_ui_preferences(app) -> Dict[str, str]:
    """Load language and zoom from the user profile, with safe defaults."""
    default_language = normalize_language(
        app.config.get('BABEL_DEFAULT_LOCALE'),
        DEFAULT_LANGUAGE,
    )
    prefs = {
        'language': default_language,
        'zoom': DEFAULT_ZOOM,
    }
    stored = _read_config(_config_path(app)).get(UI_CONFIG_KEY)
    if not isinstance(stored, dict):
        return prefs

    if 'language' in stored:
        prefs['language'] = normalize_language(stored.get('language'), default_language)
    if 'zoom' in stored:
        prefs['zoom'] = normalize_zoom(stored.get('zoom'), DEFAULT_ZOOM)
    return prefs


def save_ui_preferences(app, *, language: Optional[str] = None, zoom: Optional[str] = None) -> Dict[str, str]:
    """Merge and persist UI preferences into config.json. Returns the stored values."""
    path = _config_path(app)
    config_data = _read_config(path)
    current = load_ui_preferences(app)

    if language is not None:
        current['language'] = normalize_language(language, current['language'])
    if zoom is not None:
        current['zoom'] = normalize_zoom(zoom, current['zoom'])

    config_data[UI_CONFIG_KEY] = {
        'language': current['language'],
        'zoom': current['zoom'],
    }
    if not _write_config(path, config_data):
        return current

    logger.info(
        'Saved UI preferences language=%s zoom=%s to %s',
        current['language'],
        current['zoom'],
        path,
    )
    return current
