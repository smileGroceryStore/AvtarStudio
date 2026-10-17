"""Native, transparent desktop avatar window sharing the local tracking server."""
import json
import logging
import sys
from pathlib import Path

SIZES = [(260, 380), (340, 500), (420, 620)]


class DesktopControls:
    def __init__(self, server, data: Path, testing=False):
        self._server, self._data, self._testing = server, data, testing
        self._main = self._widget = None
        self._visible = False
        self._tray = None
        self._background = False
        self._quitting = False
        self._pixel_input = None
        try:
            self._settings = json.loads((data / 'widget.json').read_text('utf-8'))
        except (OSError, ValueError):
            self._settings = {}
        self._size = max(0, min(2, int(self._settings.get('size', 1))))

    def _configure_transparency(self):
        if sys.platform != 'win32':
            return
        try:
            from System import Action
            from System.Drawing import Color
            native = self._widget.native

            def configure():
                # Use compositor alpha, not a color-keyed layered Form. The
                # latter can make the entire GPU WebView surface click-through.
                import ctypes
                native.TransparencyKey = Color.Empty
                native.BackColor = Color.Black
                margins = (ctypes.c_int * 4)(-1, -1, -1, -1)
                status = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                    ctypes.c_void_p(native.Handle.ToInt64()), ctypes.byref(margins))
                if status != 0:
                    raise RuntimeError(f'DWM transparency failed: {status}')
                for control in native.Controls:
                    if hasattr(control, 'DefaultBackgroundColor'):
                        control.DefaultBackgroundColor = Color.Transparent
                from desktop_hit_test import install_pixel_input
                if self._pixel_input is None:
                    self._pixel_input = install_pixel_input(native)
            native.Invoke(Action(configure))
        except Exception:
            logging.exception('Widget transparency configuration failed')

    def _save(self):
        if self._widget and self._widget.native:
            try:
                self._settings.update(x=self._widget.x, y=self._widget.y)
            except Exception:
                pass
        self._settings.update(size=self._size, onTop=self._widget.on_top if self._widget else True)
        temporary = self._data / 'widget.tmp'
        temporary.write_text(json.dumps(self._settings), 'utf-8')
        temporary.replace(self._data / 'widget.json')

    def state(self):
        return {'visible': self._visible, 'size': self._size, 'background': self._background,
                'onTop': self._widget.on_top if self._widget else True}

    def open_widget(self):
        import webview
        if self._widget:
            self._widget.show()
            self._widget.restore()
        else:
            width, height = SIZES[self._size]
            self._widget = webview.create_window('映身 · 桌面挂件', self._server.url + '/widget',
                js_api=self, width=width, height=height, min_size=(220, 300),
                x=int(self._settings.get('x', 80)), y=int(self._settings.get('y', 140)),
                frameless=True, easy_drag=False, transparent=True, shadow=False,
                on_top=bool(self._settings.get('onTop', True)), resizable=False,
                background_color='#010203', minimized=self._testing)
            self._widget.events.loaded += self._configure_transparency
            self._widget.events.closing += self._on_widget_closing
        self._visible = True
        return self.state()

    def _on_widget_closing(self):
        if self._quitting:
            return True
        self.hide_widget()
        return False

    def _on_main_closing(self):
        if self._quitting:
            return True
        if self._visible or (self._tray and self._tray.ready):
            self._background = True
            self._save()
            self._main.hide()
            return False
        if self._widget:
            self._quitting = True
            self._widget.destroy()
        return True

    def hide_widget(self):
        self._save()
        self._visible = False
        if self._widget:
            self._widget.hide()
        self.show_console()
        return self.state()

    def show_console(self):
        self._background = False
        if self._main:
            self._main.show()
            self._main.restore()
        return self.state()

    def collapse_console(self):
        self.open_widget()
        self._main.minimize()
        return self.state()

    def run_background(self):
        if not self._tray or not self._tray.ready:
            raise RuntimeError('系统托盘尚未就绪，请稍后再试')
        self._save()
        self._background = True
        self._visible = False
        if self._widget:
            self._widget.hide()
        if self._main:
            self._main.hide()
        return self.state()

    def _on_main_minimized(self):
        if not self._quitting and self._tray and self._tray.ready:
            self._background = True
            self._main.hide()

    def _on_ui(self, callback):
        window = self._widget or self._main
        if sys.platform == 'win32' and window and hasattr(window.native, 'Invoke'):
            from System import Action
            window.native.Invoke(Action(callback))
        else:
            callback()

    def resize_widget(self, step):
        if type(step) is not int or step not in (-1, 1):
            raise ValueError('Invalid size step')
        self._size = max(0, min(2, self._size + step))
        if self._widget:
            self._on_ui(lambda: self._widget.resize(*SIZES[self._size]))
        self._save()
        return self.state()

    def move_widget(self, x, y):
        import math
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in (x, y)):
            raise ValueError('Invalid widget position')
        if self._widget:
            self._on_ui(lambda: self._widget.move(round(x), round(y)))
        return {'x': self._widget.x, 'y': self._widget.y}

    def widget_position(self):
        return {'x': self._widget.x, 'y': self._widget.y} if self._widget else {'x': 80, 'y': 140}

    def set_widget_hit_mask(self, width, height, pixels):
        if (type(width) is not int or type(height) is not int or not 1 <= width <= 256
                or not 1 <= height <= 384 or not isinstance(pixels, str)
                or len(pixels) != width * height or set(pixels) - {'0', '1'}):
            raise ValueError('Invalid widget hit mask')
        if self._pixel_input is not None:
            self._on_ui(lambda: self._pixel_input.SetMask(width, height, pixels))
            return True
        return False

    def save_widget_position(self):
        self._save()
        return self.widget_position()

    def _request_control(self, action, **extra):
        import urllib.request
        request = urllib.request.Request(self._server.url + '/api/control',
            data=json.dumps({'action': action, **extra}).encode('utf-8'),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)

    def show_widget_menu(self):
        if self._tray and self._tray.ready:
            self._tray.show_widget_menu()
        else:
            self.show_console()
        return self.state()

    def toggle_on_top(self):
        if self._widget:
            self._on_ui(lambda: setattr(self._widget, 'on_top', not self._widget.on_top))
        self._save()
        return self.state()

    def quit(self):
        if self._quitting:
            return
        self._save()
        self._quitting = True
        if self._tray:
            self._tray.stop()
        if self._widget:
            self._widget.destroy()
        if self._main:
            self._main.destroy()
