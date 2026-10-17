"""Windows notification-area controls, using the existing WinForms runtime."""
import logging
from desktop_menu_theme import apply_menu_theme


class DesktopTray:
    def __init__(self, controls, icon_path):
        self._controls = controls
        self._icon_path = str(icon_path)
        self._notify = self._menu = self._icon = None
        self._handlers = []
        self._popup = None
        self._popup_handlers = []
        self.ready = False

    def start(self):
        if self.ready:
            return
        def create():
            from System.Drawing import Icon
            from System.Windows.Forms import NotifyIcon, ContextMenuStrip, ToolStripMenuItem, ToolStripSeparator
            self._icon = Icon(self._icon_path)
            self._menu = ContextMenuStrip()
            for title, callback in (
                ('打开设置', self._controls.show_console),
                ('显示桌面挂件', self._controls.open_widget),
                ('隐藏窗口，后台运行', self._controls.run_background),
                ('退出映身', self._controls.quit),
            ):
                if title == '退出映身':
                    self._menu.Items.Add(ToolStripSeparator())
                item = ToolStripMenuItem(title)
                def clicked(sender, event, action=callback):
                    try:
                        action()
                    except Exception:
                        logging.exception('Tray action failed')
                self._handlers.append(clicked)
                item.Click += clicked
                self._menu.Items.Add(item)
            apply_menu_theme(self._menu)
            self._notify = NotifyIcon()
            self._notify.Icon = self._icon
            self._notify.Text = '映身 · 双击打开控制台'
            self._notify.ContextMenuStrip = self._menu
            def restore(sender, event):
                self._controls.show_console()
            self._handlers.append(restore)
            self._notify.DoubleClick += restore
            self._notify.Visible = True
            self.ready = True
        try:
            self._controls._on_ui(create)
        except Exception:
            self.stop()
            raise

    def show_widget_menu(self):
        def show():
            from System.Windows.Forms import ContextMenuStrip, ToolStripMenuItem, ToolStripSeparator, Cursor
            if self._popup:
                self._popup.Dispose()
            self._popup_handlers.clear()
            menu = self._popup = ContextMenuStrip()
            control = self._controls
            studio = control._server.studio
            def add(title, action, checked=False, enabled=True):
                item = ToolStripMenuItem(title)
                item.Checked = checked
                item.Enabled = enabled
                def clicked(sender, event):
                    try:
                        action()
                    except Exception:
                        logging.exception('Widget menu action failed')
                        control.show_console()
                self._popup_handlers.append(clicked)
                item.Click += clicked
                menu.Items.Add(item)
                return item
            add('打开设置…', control.show_console)
            add('停止捕捉' if studio.running else '开始捕捉',
                lambda: control._request_control('stop' if studio.running else 'start', cameraIndex=studio.camera_index))
            add('重新校准', lambda: control._request_control('calibrate'), enabled=studio.running)
            add('测试闭眼（1秒）', lambda: control._request_control('test-blink'))
            menu.Items.Add(ToolStripSeparator())
            add('放大挂件', lambda: control.resize_widget(1), enabled=control._size < 2)
            add('缩小挂件', lambda: control.resize_widget(-1), enabled=control._size > 0)
            add('始终置顶', control.toggle_on_top, checked=bool(control.state()['onTop']))
            add('镜像角色', lambda: control._request_control('settings',settings={'mirror': not studio.settings['mirror']}),
                checked=bool(studio.settings['mirror']))
            menu.Items.Add(ToolStripSeparator())
            add('收起挂件', control.hide_widget)
            add('转入后台', control.run_background)
            add('退出映身', control.quit)
            apply_menu_theme(menu)
            menu.Show(Cursor.Position)
        self._controls._on_ui(show)

    def stop(self):
        def dispose():
            self.ready = False
            if self._popup:
                self._popup.Dispose()
                self._popup = None
            self._popup_handlers.clear()
            if self._notify:
                self._notify.Visible = False
                self._notify.Dispose()
                self._notify = None
            if self._menu:
                self._menu.Dispose()
                self._menu = None
            if self._icon:
                self._icon.Dispose()
                self._icon = None
            self._handlers.clear()
        self._controls._on_ui(dispose)
