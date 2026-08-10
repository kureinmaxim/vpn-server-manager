"""Тесты обвязки pywebview.

GUI тут не поднимается — проверяется только то, что код зовёт существующие
методы pywebview. Именно этого не хватало, когда вызов webview.destroy_window()
из pywebview 2.x пережил переезд на 4.x и 6.x: AttributeError глотался общим
except, окно не закрывалось, а тестов на этот путь не было.
"""

from unittest.mock import Mock

import webview

from desktop.window import DesktopApp


def test_stop_destroys_window():
    app = DesktopApp()
    app.window = Mock()

    app.stop()

    app.window.destroy.assert_called_once_with()


def test_stop_without_window_does_not_raise():
    app = DesktopApp()
    assert app.window is None

    app.stop()  # не должно бросать


def test_stop_swallows_destroy_errors():
    """Ошибка закрытия не должна ронять выход из приложения."""
    app = DesktopApp()
    app.window = Mock()
    app.window.destroy.side_effect = RuntimeError('window already gone')

    app.stop()


def test_legacy_destroy_window_api_is_gone():
    """Фиксируем причину бага: функции webview.destroy_window больше не существует.

    Если она когда-нибудь вернётся в pywebview, тест напомнит пересмотреть
    комментарий в DesktopApp.stop().
    """
    assert not hasattr(webview, 'destroy_window')
