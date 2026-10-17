import tempfile
import unittest
from pathlib import Path
from desktop_widget import DesktopControls


class FakeWindow:
    def __init__(self):
        self.native = True
        self.x, self.y, self.on_top = 20, 30, True
        self.hidden = self.destroyed = False
    def hide(self): self.hidden = True
    def show(self): self.hidden = False
    def restore(self): pass
    def resize(self, w, h): self.size = (w, h)
    def move(self, x, y): self.x, self.y = x, y
    def destroy(self): self.destroyed = True


class DesktopWidgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.control = DesktopControls(None, Path(self.temp.name))
        self.control._main = FakeWindow()
        self.control._widget = FakeWindow()
    def tearDown(self):
        self.temp.cleanup()
    def test_console_close_keeps_pet_but_explicit_quit_destroys_both(self):
        self.control._visible = True
        self.assertFalse(self.control._on_main_closing())
        self.assertTrue(self.control._main.hidden)
        self.assertFalse(self.control._widget.destroyed)
        self.control.quit()
        self.assertTrue(self.control._main.destroyed)
        self.assertTrue(self.control._widget.destroyed)
    def test_resize_pin_and_hidden_widget_shutdown(self):
        self.control.resize_widget(1)
        self.assertEqual(self.control._widget.size, (420, 620))
        self.control.resize_widget(1)
        self.assertEqual(self.control._widget.size, (420, 620))
        self.assertFalse(self.control.toggle_on_top()['onTop'])
        self.control.hide_widget()
        self.assertFalse(self.control._main.hidden)
        self.assertTrue(self.control._on_main_closing())
        self.assertTrue(self.control._widget.destroyed)
    def test_move_and_persist_position(self):
        self.control.move_widget(310, 240)
        self.assertEqual(self.control.save_widget_position(), {'x':310, 'y':240})
        import json
        saved = json.loads((Path(self.temp.name)/'widget.json').read_text('utf-8'))
        self.assertEqual((saved['x'],saved['y']), (310,240))
        with self.assertRaises(ValueError):
            self.control.move_widget(float('nan'), 0)

    def test_background_keeps_capture_and_restores_without_recreating_windows(self):
        from types import SimpleNamespace
        self.control._server = SimpleNamespace(studio=SimpleNamespace(running=True))
        class Tray:
            ready = True
            def stop(self): self.ready = False
        tray = self.control._tray = Tray()
        self.control._visible = True
        state = self.control.run_background()
        self.assertTrue(state['background'])
        self.assertFalse(state['visible'])
        self.assertTrue(self.control._server.studio.running)
        self.assertTrue(self.control._main.hidden)
        self.assertTrue(self.control._widget.hidden)
        self.assertFalse(self.control._on_main_closing())
        self.assertFalse(self.control._main.destroyed)
        self.control.show_console()
        self.assertFalse(self.control.state()['background'])
        self.assertFalse(self.control._main.hidden)
        self.control.quit()
        self.assertFalse(tray.ready)
        self.assertTrue(self.control._main.destroyed)

    def test_close_without_widget_keeps_tray_running(self):
        from types import SimpleNamespace
        self.control._widget = None
        self.control._tray = SimpleNamespace(ready=True)
        self.assertFalse(self.control._on_main_closing())
        self.assertTrue(self.control._main.hidden)
        self.assertFalse(self.control._quitting)

    def test_no_tray_cannot_hide_all_windows(self):
        with self.assertRaises(RuntimeError):
            self.control.run_background()
        self.assertFalse(self.control._main.hidden)

    def test_only_explicit_methods_are_exposed_to_js(self):
        self.assertTrue(all(name.startswith('_') for name in vars(self.control)))


if __name__ == '__main__':
    unittest.main()
