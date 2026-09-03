"""Region snip geometry — no GUI window is opened."""

import pytest

from desktop.snip import normalize_rect


def test_normalize_rect_orders_and_rejects_tiny_drags():
    assert normalize_rect(80, 40, 10, 10) == (10, 10, 80, 40)
    assert normalize_rect(5, 5, 6, 8) is None
