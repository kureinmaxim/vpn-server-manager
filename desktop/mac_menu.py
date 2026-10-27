"""Масштаб в меню «Вид» окна macOS: Увеличить ⌘=, Уменьшить ⌘−, Фактический размер ⌘0.

pywebview сам строит меню «Вид» (только «Полноэкранный режим») и не умеет назначать клавиши
своим пунктам, поэтому пункты масштаба добавляются в его меню напрямую через AppKit.
Сам масштаб меняет страница: пункт вызывает window.vpnZoom из templates/layout.html,
так что шаги, сохранение и подсказка те же, что у лупы в шапке.
"""

import logging
import sys
import threading

logger = logging.getLogger(__name__)

# Подписи стандартного меню pywebview и пунктов масштаба на языке интерфейса
MENU_LABELS = {
    'ru': {
        'cocoa.menu.about': 'О программе',
        'cocoa.menu.services': 'Службы',
        'cocoa.menu.view': 'Вид',
        'cocoa.menu.hide': 'Скрыть',
        'cocoa.menu.hideOthers': 'Скрыть остальные',
        'cocoa.menu.showAll': 'Показать все',
        'cocoa.menu.quit': 'Завершить',
        'cocoa.menu.fullscreen': 'Полноэкранный режим',
        'zoom.in': 'Увеличить',
        'zoom.out': 'Уменьшить',
        'zoom.reset': 'Фактический размер',
    },
    'en': {
        'cocoa.menu.view': 'View',
        'cocoa.menu.fullscreen': 'Enter Full Screen',
        'zoom.in': 'Zoom In',
        'zoom.out': 'Zoom Out',
        'zoom.reset': 'Actual Size',
    },
    'zh': {
        'cocoa.menu.about': '关于',
        'cocoa.menu.services': '服务',
        'cocoa.menu.view': '显示',
        'cocoa.menu.hide': '隐藏',
        'cocoa.menu.hideOthers': '隐藏其他',
        'cocoa.menu.showAll': '全部显示',
        'cocoa.menu.quit': '退出',
        'cocoa.menu.fullscreen': '进入全屏幕',
        'zoom.in': '放大',
        'zoom.out': '缩小',
        'zoom.reset': '实际大小',
    },
}


def _labels(language):
    return MENU_LABELS.get(language) or MENU_LABELS['en']


def localization(language):
    """Подписи стандартного меню pywebview (ключи cocoa.menu.*) для webview.start."""
    return {key: value for key, value in _labels(language).items() if key.startswith('cocoa.')}


def zoom_items(language):
    """(подпись, клавиша вместе с ⌘, JS) для пунктов масштаба."""
    labels = _labels(language)
    return [
        (labels['zoom.in'], '=', 'window.vpnZoom && window.vpnZoom.step(1)'),
        (labels['zoom.out'], '-', 'window.vpnZoom && window.vpnZoom.step(-1)'),
        (labels['zoom.reset'], '0', 'window.vpnZoom && window.vpnZoom.reset()'),
    ]


_evaluate = None       # window.evaluate_js окна приложения
_target = None         # цель пунктов меню; держим ссылку, иначе её соберёт сборщик мусора
_target_class = None   # класс Objective-C регистрируется один раз на процесс


def _run_script(script):
    if _evaluate is None:
        return
    try:
        _evaluate(script)
    except Exception as exc:  # окно закрывается или страница ещё грузится
        logger.debug('Масштаб из меню не применён: %s', exc)


def _make_target(AppKit):
    global _target_class
    if _target_class is None:
        class ZoomMenuTarget(AppKit.NSObject):
            def runZoom_(self, sender):
                # evaluate_js ждёт ответа страницы — не держим главный поток
                threading.Thread(target=_run_script, args=(str(sender.representedObject()),),
                                 daemon=True).start()

        _target_class = ZoomMenuTarget
    return _target_class.alloc().init()


def _view_menu(AppKit, title):
    """Меню «Вид» pywebview (в нём «Полноэкранный режим»), иначе новое меню после меню приложения."""
    main_menu = AppKit.NSApp.mainMenu()
    if main_menu is None:
        main_menu = AppKit.NSMenu.alloc().init()
        AppKit.NSApp.setMainMenu_(main_menu)
    for item in main_menu.itemArray():
        submenu = item.submenu()
        if submenu is None:
            continue
        if any(str(entry.action() or '') == 'toggleFullScreen:' for entry in submenu.itemArray()):
            return submenu
    menu = AppKit.NSMenu.alloc().initWithTitle_(title)
    holder = AppKit.NSMenuItem.alloc().init()
    holder.setSubmenu_(menu)
    main_menu.insertItem_atIndex_(holder, min(1, main_menu.numberOfItems()))
    return menu


def _add_items(AppKit, language):
    global _target
    # Вкладок у окна нет: без этого macOS дописывает в «Вид» «Показать панель вкладок»
    AppKit.NSWindow.setAllowsAutomaticWindowTabbing_(False)
    # «Полноэкранный режим» уже есть от pywebview — второй такой пункт macOS не добавляет
    AppKit.NSUserDefaults.standardUserDefaults().setBool_forKey_(False, 'NSFullScreenMenuItemEverywhere')
    menu = _view_menu(AppKit, _labels(language)['cocoa.menu.view'])
    if any(str(entry.action() or '') == 'runZoom:' for entry in menu.itemArray()):
        return
    _target = _make_target(AppKit)
    for index, (title, key, script) in enumerate(zoom_items(language)):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, 'runZoom:', key)
        item.setKeyEquivalentModifierMask_(AppKit.NSEventModifierFlagCommand)
        item.setTarget_(_target)
        item.setRepresentedObject_(script)
        menu.insertItem_atIndex_(item, index)
    menu.insertItem_atIndex_(AppKit.NSMenuItem.separatorItem(), len(zoom_items(language)))


def install(window, language):
    """Добавить пункты масштаба в меню «Вид». Вызывать после запуска webview (func у webview.start)."""
    global _evaluate
    if sys.platform != 'darwin':
        return False
    try:
        import AppKit
        from PyObjCTools import AppHelper
    except ImportError:
        logger.info('PyObjC недоступен — меню масштаба не добавлено')
        return False
    _evaluate = window.evaluate_js

    def add():
        try:
            _add_items(AppKit, language)
        except Exception as exc:
            logger.warning('Не удалось добавить масштаб в меню «Вид»: %s', exc)

    # Меню AppKit меняется только в главном потоке
    AppHelper.callAfter(add)
    return True
