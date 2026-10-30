"""Persistent UI preferences (language, zoom) in the user profile config.json."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ALLOWED_LANGUAGES = frozenset({'ru', 'en', 'zh'})
# Шаги масштаба по порядку: меню «Вид» и Cmd+=/Cmd+− идут по ним от текущего значения
ZOOM_STEPS = ('50', '60', '70', '80', '90', '100', '110', '125', '150', '175', '200')
ALLOWED_ZOOMS = frozenset(ZOOM_STEPS)
DEFAULT_LANGUAGE = 'en'
DEFAULT_ZOOM = '100'
UI_CONFIG_KEY = 'ui'
# Кнопки главной страницы. «Проекты» и «Боты» — каталоги под свои проекты и Telegram-ботов:
# в новой установке они скрыты, включаются в настройках.
DEFAULT_FEATURES = {'dns': True, 'load': True, 'projects': False, 'bots': False}


def _config_path(app) -> str:
    return os.path.join(app.config.get('APP_DATA_DIR', '.'), 'config.json')


def _read_config(path: str) -> Dict[str, Any]:
    from .config_io import read_config
    try:
        return read_config(path)
    except (OSError, ValueError):
        # Defaults remain usable for rendering; an unversioned dict cannot be saved.
        logger.warning('UI configuration is unreadable; changes are disabled')
        return {}


def _write_config(path: str, data: Dict[str, Any]) -> bool:
    from .config_io import write_config
    try:
        return write_config(path, data)
    except (OSError, ValueError):
        logger.error('Configuration was not saved; reload or recover the profile')
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

    stored = config_data.get(UI_CONFIG_KEY)
    config_data[UI_CONFIG_KEY] = dict(stored if isinstance(stored, dict) else {},
                                      language=current['language'], zoom=current['zoom'])
    if not _write_config(path, config_data):
        return current

    logger.info(
        'Saved UI preferences language=%s zoom=%s to %s',
        current['language'],
        current['zoom'],
        path,
    )
    return current


def load_ui_features(app) -> Dict[str, bool]:
    """Which optional home-page tools are shown (DNS, server load, projects, bots)."""
    features = dict(DEFAULT_FEATURES)
    stored = _read_config(_config_path(app)).get(UI_CONFIG_KEY)
    saved = stored.get('features') if isinstance(stored, dict) else None
    if isinstance(saved, dict):
        features.update({name: bool(saved[name]) for name in DEFAULT_FEATURES if name in saved})
    return features


def save_ui_features(app, enabled) -> Dict[str, bool]:
    """Store the shown tools; names outside DEFAULT_FEATURES are ignored.

    Raises OSError (with the config path) when config.json cannot be written.
    """
    enabled = set(enabled or ())
    features = {name: name in enabled for name in DEFAULT_FEATURES}
    path = _config_path(app)
    config_data = _read_config(path)
    stored = config_data.get(UI_CONFIG_KEY)
    config_data[UI_CONFIG_KEY] = dict(stored if isinstance(stored, dict) else {}, features=features)
    if not _write_config(path, config_data):
        raise OSError(path)
    return features
