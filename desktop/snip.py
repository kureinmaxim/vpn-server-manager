"""Select a rectangle on the desktop and return it as PNG bytes."""
from __future__ import annotations

import io
import logging
import os
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)

MIN_RECT_PX = 8


def normalize_rect(x1, y1, x2, y2, min_size: int = MIN_RECT_PX):
    """Return (left, top, right, bottom) or None if the drag is too small."""
    left, right = sorted((int(x1), int(x2)))
    top, bottom = sorted((int(y1), int(y2)))
    if (right - left) < min_size or (bottom - top) < min_size:
        return None
    return (left, top, right, bottom)


def _enable_dpi_awareness() -> None:
    if sys.platform != 'win32':
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _virtual_screen() -> tuple[int, int, int, int]:
    """left, top, width, height of the virtual desktop."""
    if sys.platform == 'win32':
        import ctypes

        user32 = ctypes.windll.user32
        left = int(user32.GetSystemMetrics(76))
        top = int(user32.GetSystemMetrics(77))
        width = int(user32.GetSystemMetrics(78))
        height = int(user32.GetSystemMetrics(79))
        if width > 0 and height > 0:
            return left, top, width, height
    return 0, 0, 0, 0


def _overlay_select_and_grab() -> bytes | None:
    """Freeze the desktop, let the user drag a rectangle, return PNG or None."""
    import tkinter as tk

    from PIL import ImageGrab, ImageTk

    _enable_dpi_awareness()
    left, top, width, height = _virtual_screen()
    grab_kwargs = {'all_screens': True}
    if width > 0 and height > 0:
        screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height), **grab_kwargs)
    else:
        screenshot = ImageGrab.grab(**grab_kwargs)
        left, top = 0, 0
        width, height = screenshot.size

    result: dict = {'box': None}
    start = {'x': 0, 'y': 0}

    root = tk.Tk()
    root.withdraw()
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes('-topmost', True)
    win.geometry(f'{width}x{height}+{left}+{top}')
    win.configure(cursor='cross')

    canvas = tk.Canvas(win, highlightthickness=0, cursor='cross', bg='black')
    canvas.pack(fill='both', expand=True)

    display = screenshot
    scale_x = screenshot.width / max(width, 1)
    scale_y = screenshot.height / max(height, 1)
    if screenshot.size != (width, height):
        display = screenshot.resize((width, height))
        scale_x = screenshot.width / max(width, 1)
        scale_y = screenshot.height / max(height, 1)

    photo = ImageTk.PhotoImage(display)
    canvas.create_image(0, 0, anchor='nw', image=photo)
    dim_id = canvas.create_rectangle(0, 0, width, height, fill='#000000', stipple='gray50', outline='')
    rect_id = canvas.create_rectangle(0, 0, 0, 0, outline='#00e5c0', width=2)
    hint_id = canvas.create_text(
        width // 2,
        36,
        text='Select area  ·  Esc cancels',
        fill='#ffffff',
        font=('Segoe UI', 16, 'bold'),
    )
    canvas.image = photo

    def _finish(box):
        result['box'] = box
        win.destroy()
        root.destroy()

    def on_press(event):
        start['x'], start['y'] = event.x, event.y
        canvas.coords(rect_id, event.x, event.y, event.x, event.y)

    def on_drag(event):
        canvas.coords(rect_id, start['x'], start['y'], event.x, event.y)
        canvas.itemconfigure(dim_id, state='hidden')

    def on_release(event):
        box = normalize_rect(start['x'], start['y'], event.x, event.y)
        if box is None:
            canvas.itemconfigure(dim_id, state='normal')
            return
        src = (
            int(box[0] * scale_x),
            int(box[1] * scale_y),
            int(box[2] * scale_x),
            int(box[3] * scale_y),
        )
        _finish(src)

    def on_escape(_event=None):
        _finish(None)

    canvas.bind('<ButtonPress-1>', on_press)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)
    win.bind('<Escape>', on_escape)
    canvas.bind('<Escape>', on_escape)
    win.focus_force()
    canvas.focus_set()
    root.mainloop()

    box = result['box']
    if not box:
        return None
    crop = screenshot.crop(box)
    out = io.BytesIO()
    crop.save(out, format='PNG')
    return out.getvalue()


def capture_region() -> bytes | None:
    """Run the snip overlay in a child process so tkinter is not on the WebView thread."""
    if os.environ.get('VPN_SNIP_INPROCESS') == '1':
        return _overlay_select_and_grab()

    script = os.path.abspath(__file__)
    handle, path = tempfile.mkstemp(suffix='.png')
    os.close(handle)
    try:
        kwargs = {
            'args': [sys.executable, script, path],
            'timeout': 600,
            'check': False,
        }
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo
        proc = subprocess.run(**kwargs)
        if proc.returncode != 0:
            return None
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            return None
        with open(path, 'rb') as handle:
            return handle.read()
    except subprocess.TimeoutExpired:
        logger.warning('Screen snip timed out')
        return None
    except Exception:
        logger.exception('Screen snip failed')
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return 2
    png = _overlay_select_and_grab()
    if not png:
        return 1
    with open(argv[0], 'wb') as handle:
        handle.write(png)
    return 0


if __name__ == '__main__':
    sys.exit(main())
