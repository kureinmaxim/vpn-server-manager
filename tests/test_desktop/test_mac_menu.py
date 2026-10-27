"""Масштаб в меню «Вид» окна macOS."""

import inspect
import sys
from unittest.mock import Mock

import pytest
import webview

from desktop import mac_menu


def test_localization_uses_pywebview_keys():
    known = set(webview.localization.original_localization)
    for language in ('ru', 'en', 'zh'):
        strings = mac_menu.localization(language)
        assert strings and set(strings) <= known
    assert mac_menu.localization('ru')['cocoa.menu.view'] == 'Вид'
    assert mac_menu.localization('fr') == mac_menu.localization('en')


def test_zoom_items_call_page_zoom():
    items = mac_menu.zoom_items('ru')
    assert [title for title, _, _ in items] == ['Увеличить', 'Уменьшить', 'Фактический размер']
    assert [key for _, key, _ in items] == ['=', '-', '0']
    assert all(script.startswith('window.vpnZoom && window.vpnZoom.') for _, _, script in items)


def test_install_is_noop_outside_macos(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert mac_menu.install(Mock(), 'en') is False


def test_webview_start_accepts_menu_arguments():
    params = inspect.signature(webview.start).parameters
    assert {'func', 'args', 'localization'} <= set(params)


@pytest.mark.skipif(sys.platform != 'darwin', reason='AppKit только на macOS')
def test_items_go_into_fullscreen_view_menu_once(monkeypatch):
    AppKit = pytest.importorskip('AppKit')
    app = AppKit.NSApplication.sharedApplication()
    saved = app.mainMenu()
    main_menu = AppKit.NSMenu.alloc().init()
    view = AppKit.NSMenu.alloc().initWithTitle_('View')
    view.addItemWithTitle_action_keyEquivalent_('Enter Full Screen', 'toggleFullScreen:', 'f')
    holder = AppKit.NSMenuItem.alloc().init()
    holder.setSubmenu_(view)
    main_menu.addItem_(AppKit.NSMenuItem.alloc().init())
    main_menu.addItem_(holder)
    app.setMainMenu_(main_menu)
    calls = []
    monkeypatch.setattr(mac_menu, '_evaluate', calls.append)
    try:
        mac_menu._add_items(AppKit, 'en')
        mac_menu._add_items(AppKit, 'en')  # повторный вызов не дублирует пункты
        titles = [item.title() for item in view.itemArray()]
        assert titles[:3] == ['Zoom In', 'Zoom Out', 'Actual Size']
        assert titles.count('Zoom In') == 1 and titles[-1] == 'Enter Full Screen'
        zoom_in = view.itemArray()[0]
        assert zoom_in.keyEquivalent() == '='
        assert zoom_in.keyEquivalentModifierMask() == AppKit.NSEventModifierFlagCommand
        mac_menu._run_script(str(zoom_in.representedObject()))
        assert calls == ['window.vpnZoom && window.vpnZoom.step(1)']
    finally:
        app.setMainMenu_(saved)
