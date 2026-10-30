"""Solid palette pairs only; not a claim of whole-page WCAG conformance."""
from pathlib import Path
import re

import pytest

CSS = (Path(__file__).resolve().parents[2] / 'static/css/accessibility.css').read_text()


def ratio(foreground, background):
    def luminance(value):
        channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in channels]
        return sum(x * weight for x, weight in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted([luminance(foreground), luminance(background)])
    return (b + .05) / (a + .05)


def palette(selector):
    block = re.search(re.escape(selector) + r'\s*\{([^}]+)', CSS).group(1)
    return dict(re.findall(r'--a11y-([\w-]+):\s*(#[0-9a-f]{6})', block))


@pytest.mark.parametrize('theme,surfaces', [
    ('light', ['#f0f7f6', '#ffffff']),
    ('dark', ['#0d1a26', '#1a2938']),
    ('minecraft', ['#1e1610', '#3a2f24']),
])
def test_solid_primary_and_status_text_contrast(theme, surfaces):
    colors = palette('[data-bs-theme="light"]' if theme == 'light' else '[data-bs-theme="dark"]')
    if theme == 'minecraft':
        colors.update(palette('html[data-skin="minecraft"]'))
    for background in ('primary-bg', 'primary-hover'):
        assert ratio(colors['primary-text'], colors[background]) >= 4.5
    for status in ('success', 'info', 'warning', 'danger', 'secondary', 'primary-outline'):
        assert ratio(colors['on-secondary'], colors[status]) >= 4.5
        for background in surfaces:
            assert ratio(colors[status], background) >= 4.5, (theme, status, background)
    assert ratio(colors['on-secondary'], colors['secondary']) >= 4.5
    primary_surface = {'light': '#008060', 'dark': '#00bfa5', 'minecraft': '#5b8c3e'}[theme]
    assert ratio(colors['primary-surface-text'], primary_surface) >= 4.5
    assert ratio('#ffffff', '#198754') >= 4.5
