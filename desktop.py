"""Windows desktop entry point. Backend lifetime follows the native window."""
from __future__ import annotations
import argparse
import asyncio
import ctypes
import json
import logging
import os
import shutil
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def user_directory():
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'AvatarStudio'


def migrate_data(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    marker = destination / 'migration-v1.json'
    if marker.exists():
        return
    # Only migrate the user's saved settings/avatar; never copy camera frames.
    source = ROOT / 'data'
    for name in ('settings.json', 'avatar.vrm'):
        if (source / name).is_file() and not (destination / name).exists():
            shutil.copy2(source / name, destination / name)
    marker.write_text(json.dumps({'version': 1}), encoding='utf-8')


class DesktopServer:
    def __init__(self, port=8080):
        self.port = port
        self.ready = threading.Event()
        self.error = None
        self.loop = None
        self.finish = None
        self.studio = None
        self.thread = threading.Thread(target=self._run, daemon=True, name='desktop-server')

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'

    def start(self):
        self.thread.start()
        if not self.ready.wait(15):
            raise RuntimeError('本地服务启动超时，请查看日志。')
        if self.error:
            raise RuntimeError(str(self.error))

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._serve())
        except BaseException as exc:
            self.error = exc
            logging.exception('Desktop server failed')
            self.ready.set()
        finally:
            self.loop.close()

    async def _serve(self):
        from aiohttp import web
        from studio import Studio, create_app
        self.studio = Studio()
        self.finish = asyncio.Event()
        runner = web.AppRunner(create_app(self.studio, shutdown_callback=self.finish.set))
        await runner.setup()
        try:
            try:
                await web.TCPSite(runner, '127.0.0.1', self.port).start()
            except OSError:
                # Keep the browser prototype or another application's port intact.
                if self.port != 8080:
                    raise
                site = web.TCPSite(runner, '127.0.0.1', 0)
                await site.start()
                self.port = site._server.sockets[0].getsockname()[1]
            self.ready.set()
            await self.finish.wait()
        finally:
            await runner.cleanup()

    def stop(self):
        if self.studio:
            self.studio.running = False
            self.studio.shutdown.set()
        if self.loop and self.loop.is_running() and self.finish:
            self.loop.call_soon_threadsafe(self.finish.set)
        if self.thread.is_alive():
            self.thread.join(8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--background', action='store_true', help='Start hidden in the system tray')
    parser.add_argument('--widget', action='store_true', help='Open the desktop avatar and minimize the console')
    args = parser.parse_args()
    data = (args.data_dir or user_directory()).resolve()
    if args.data_dir:
        data.mkdir(parents=True, exist_ok=True)
    else:
        migrate_data(data)
    os.environ['AVATAR_STUDIO_DATA'] = str(data.resolve())
    log = open(data / 'desktop.log', 'a', encoding='utf-8', buffering=1)
    if getattr(sys, 'frozen', False):
        sys.stdout = sys.stderr = log
    logging.basicConfig(stream=log, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    mutex = None
    if sys.platform == 'win32' and not args.smoke_test:
        ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Local\\AvatarStudioDesktopV1')
        if ctypes.windll.kernel32.GetLastError() == 183:
            ctypes.windll.user32.MessageBoxW(None, '映身已经在运行，请切换到已打开的窗口。', '映身', 0x40)
            return
    server = DesktopServer(args.port)
    try:
        server.start()
        import webview
        from desktop_widget import DesktopControls
        controls = DesktopControls(server, data, testing=args.smoke_test)
        window = webview.create_window('映身 · Avatar Studio', server.url + '/?desktop=1', width=1440,
                                       height=960, min_size=(1000, 700), background_color='#020617', minimized=args.smoke_test, hidden=args.background,
                                       js_api=controls)
        controls._main = window
        window.events.minimized += controls._on_main_minimized
        window.events.closing += controls._on_main_closing
        window.events.closed += server.stop

        def smoke_test():
            native_frame = {}
            if sys.platform == 'win32':
                try:
                    window.events.shown.wait(15)
                    hwnd = int(window.native.Handle.ToInt64())
                    for attribute, value in ((20, 1), (35, 0x231D19), (36, 0xF1ECE8), (34, 0x443B34)):
                        color = ctypes.c_int(value)
                        native_frame[str(attribute)] = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            ctypes.c_void_p(hwnd), attribute, ctypes.byref(color), ctypes.sizeof(color))
                except Exception:
                    logging.warning('Native frame styling unavailable', exc_info=True)
            if sys.platform == 'win32':
                from desktop_tray import DesktopTray
                controls._tray = DesktopTray(controls, ROOT / 'desktop-assets/app.ico')
                try:
                    controls._tray.start()
                except Exception:
                    logging.exception('System tray initialization failed')
                    controls.show_console()
            if not args.smoke_test:
                if args.background and controls._tray and controls._tray.ready:
                    controls.run_background()
                elif args.widget:
                    controls.collapse_console()
                return
            result = {'success': False}
            try:
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    result = window.evaluate_js("({title:document.title, model:document.getElementById('modelStatus')?.textContent, connected:document.getElementById('connection')?.textContent, width:innerWidth, height:innerHeight, desktop:document.documentElement.classList.contains('desktop-mode')})") or {}
                    if '已加载' in result.get('model', '') and '已连接' in result.get('connected', ''):
                        result['success'] = True
                        break
                    time.sleep(.25)
                result['nativeFrame'] = native_frame
                result['bridgeReady'] = window.evaluate_js("typeof window.pywebview?.api?.open_widget==='function'")
                if not result['bridgeReady']:
                    raise RuntimeError('Desktop controls bridge unavailable')
                controls.open_widget()
                controls._widget.events.loaded.wait(20)
                controls._configure_transparency()
                widget_deadline = time.monotonic() + 25
                while time.monotonic() < widget_deadline:
                    widget_state = controls._widget.evaluate_js("({mode:document.documentElement.classList.contains('widget-mode'),background:getComputedStyle(document.body).backgroundColor,ready:document.documentElement.dataset.avatarReady==='true'})")
                    if widget_state and widget_state.get('ready'):
                        break
                    time.sleep(.25)
                native = controls._widget.native
                result['widget'] = dict(widget_state or {}, topmost=bool(native.TopMost),
                    frameless=str(native.FormBorderStyle) == 'None',
                    compositorAlpha=bool(native.TransparencyKey.IsEmpty))
                if not result['widget'].get('ready') or not all(result['widget'][k] for k in ('topmost','frameless','compositorAlpha')):
                    raise RuntimeError('Desktop widget validation failed')
                controls._widget.show()
                controls._widget.restore()
                time.sleep(.5)
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                user32.WindowFromPoint.argtypes = [wintypes.POINT]
                user32.WindowFromPoint.restype = wintypes.HWND
                user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
                user32.GetAncestor.restype = wintypes.HWND
                hwnd = native.Handle.ToInt64()
                rect = wintypes.RECT()
                user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
                # Render a known solid color in another app-owned window below
                # the widget, then sample a transparent corner. This verifies
                # actual DWM output as well as the browser's CSS alpha.
                from System.Windows.Forms import Form, FormBorderStyle, FormStartPosition
                from System.Drawing import Color
                backdrop = []
                def create_backdrop():
                    form = Form()
                    form.FormBorderStyle = getattr(FormBorderStyle, 'None')
                    form.ShowInTaskbar = False
                    form.StartPosition = FormStartPosition.Manual
                    form.Bounds = native.Bounds
                    form.BackColor = Color.FromArgb(255, 37, 75, 91)
                    form.TopMost = True
                    form.Show()
                    native.TopMost = False
                    native.TopMost = True
                    native.BringToFront()
                    backdrop.append(form)
                controls._on_ui(create_backdrop)
                time.sleep(.3)
                user32.GetDC.argtypes = [wintypes.HWND]
                user32.GetDC.restype = wintypes.HDC
                user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
                gdi32 = ctypes.windll.gdi32
                gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
                gdi32.GetPixel.restype = wintypes.DWORD
                dc = user32.GetDC(None)
                try:
                    pixel = gdi32.GetPixel(dc, rect.left + 2, (rect.top + rect.bottom)//2)
                    result['widget']['compositedPixel'] = hex(pixel)
                    result['widget']['nativeTransparent'] = pixel == 0x5b4b25
                finally:
                    user32.ReleaseDC(None, dc)
                if not result['widget']['nativeTransparent']:
                    raise RuntimeError('Native compositor transparency failed')
                if controls._pixel_input is None:
                    raise RuntimeError('Pixel input controller not initialized')
                mask_deadline = time.monotonic() + 10
                while controls._pixel_input.MaskInfo.startswith('0x0') and time.monotonic() < mask_deadline:
                    time.sleep(.1)
                result['widget']['maskBridge'] = controls._widget.evaluate_js("typeof window.pywebview?.api?.set_widget_hit_mask")
                def verify_pixel_input():
                    from System.Drawing import Point
                    corner = native.PointToScreen(Point(2,2))
                    center = native.PointToScreen(Point(native.ClientSize.Width//2,native.ClientSize.Height//2))
                    controls._pixel_input.Probe(corner.X,corner.Y)
                    blank_root = user32.GetAncestor(user32.WindowFromPoint(wintypes.POINT(corner.X,corner.Y)),2)
                    result['widget']['blankMousePassThrough'] = blank_root == backdrop[0].Handle.ToInt64()
                    display_dc = user32.GetDC(None)
                    try:
                        result['widget']['characterVisibleWhilePassing'] = gdi32.GetPixel(display_dc,center.X,center.Y) != 0x5b4b25
                    finally:
                        user32.ReleaseDC(None,display_dc)
                    controls._pixel_input.Probe(center.X,center.Y)
                    result['widget']['hitMask'] = controls._pixel_input.MaskInfo
                    result['widget']['centerPassThrough'] = controls._pixel_input.Transparent
                    result['widget']['inputStyles'] = controls._pixel_input.StyleInfo
                    backdrop[0].Close()
                    native.BringToFront()
                    root = user32.GetAncestor(user32.WindowFromPoint(wintypes.POINT(center.X,center.Y)),2)
                    result['widget']['nativeMouseHit'] = root == hwnd
                    result['widget']['hitDiagnostic'] = dict(root=int(root or 0), expected=int(hwnd),current=int(native.Handle.ToInt64()),bounds=str(native.Bounds),windowState=str(native.WindowState),visible=bool(native.Visible),point=[center.X,center.Y])
                    controls._pixel_input.ClearProbe()
                controls._on_ui(verify_pixel_input)
                if not result['widget']['blankMousePassThrough']:
                    raise RuntimeError('Transparent blank area did not pass mouse input to underlying window')
                if not result['widget']['characterVisibleWhilePassing']:
                    raise RuntimeError('Character disappeared while blank area was mouse-transparent')
                if not result['widget']['nativeMouseHit']:
                    raise RuntimeError('Widget native mouse hit test failed')
                logging.info("Widget smoke: controls.resize_widget(-1)")
                origin = controls.widget_position()
                controls.move_widget(origin['x'] + 30, origin['y'] + 20)
                moved = controls.save_widget_position()
                result['widget']['moveVerified'] = moved == {'x': origin['x'] + 30, 'y': origin['y'] + 20}
                if not result['widget']['moveVerified']:
                    raise RuntimeError('Widget move failed')
                controls.move_widget(origin['x'], origin['y'])
                controls.resize_widget(-1)
                logging.info("Widget smoke: controls.resize_widget(1)")
                controls.resize_widget(1)
                logging.info("Widget smoke: controls.toggle_on_top()")
                controls.toggle_on_top()
                logging.info("Widget smoke: controls.toggle_on_top()")
                controls.toggle_on_top()
                logging.info("Widget smoke: controls.hide_widget()")
                controls.hide_widget()
                controls.open_widget()
                logging.info('Widget smoke: hide console')
                result['widget']['consoleCanHide'] = controls._on_main_closing() is False and not server.studio.shutdown.is_set()
                result['tray'] = {'ready': bool(controls._tray and controls._tray.ready)}
                if not result['tray']['ready']:
                    raise RuntimeError('System tray was not created')
                controls.run_background()
                result['tray']['backgroundHidden'] = not window.native.Visible and not native.Visible
                result['tray']['serverAlive'] = not server.studio.shutdown.is_set()
                controls._on_ui(lambda: controls._tray._menu.Items[0].PerformClick())
                result['tray']['restoreConsole'] = bool(window.native.Visible)
                controls._on_ui(lambda: controls._tray._menu.Items[1].PerformClick())
                result['tray']['restoreWidget'] = bool(native.Visible)
                controls._on_ui(lambda: controls._tray._menu.Items[2].PerformClick())
                result['tray']['menuBackground'] = not window.native.Visible and not native.Visible
                result['tray']['closeKeepsBackground'] = controls._on_main_closing() is False and not controls._quitting
                if not all(result['tray'].values()):
                    raise RuntimeError('System tray background/restore validation failed')
                controls.open_widget()
                controls.show_widget_menu()
                popup = controls._tray._popup
                result['widget']['contextMenu'] = popup.Items.Count == 13
                def capture_menu(menu, name, show=False):
                    from System.Drawing import Bitmap, Rectangle
                    from System.Drawing.Imaging import ImageFormat
                    from System.Windows.Forms import Cursor
                    if show: menu.Show(Cursor.Position)
                    menu.PerformLayout()
                    bitmap=Bitmap(menu.Width,menu.Height)
                    try:
                        menu.DrawToBitmap(bitmap,Rectangle(0,0,menu.Width,menu.Height))
                        bitmap.Save(str(data / name),ImageFormat.Png)
                    finally:
                        bitmap.Dispose()
                        if show: menu.Close()
                result['widget']['menuTheme'] = popup.Renderer.GetType().Name == 'AvatarMenuRenderer'
                if not result['widget']['menuTheme']:
                    raise RuntimeError('Native context menu theme failed')
                controls._on_ui(lambda: capture_menu(popup,'widget-menu.png'))
                controls._on_ui(lambda: capture_menu(controls._tray._menu,'tray-menu.png',True))

                result['widget']['pureView'] = controls._widget.evaluate_js("document.querySelectorAll('#widgetTools,#widgetGrip,#outputError').length===0 && document.body.innerText.trim()===''")
                controls._on_ui(lambda: popup.Items[7].PerformClick())
                controls._on_ui(lambda: popup.Items[7].PerformClick())
                controls._on_ui(lambda: popup.Items[0].PerformClick())
                result['widget']['contextSettings'] = bool(window.native.Visible)
                controls._on_ui(lambda: popup.Items[3].PerformClick())
                result['widget']['blinkTestWithoutCamera'] = server.studio.snapshot()['testBlink'] and not server.studio.running
                controls._on_ui(lambda: popup.Close())
                if not all(result['widget'][key] for key in ('contextMenu','pureView','contextSettings','blinkTestWithoutCamera')):
                    raise RuntimeError('Pure widget context menu validation failed')
                # Verify frozen native libraries and embedded weights as well
                # as the window; this uses a blank frame, never a camera.
                import numpy as np
                from src.tracking.landmarker import FaceLandmarker
                from src.tracking.hand_landmarker import HandLandmarker
                from src.tracking.pose_landmarker import PoseTracker
                trackers = []
                try:
                    blank = np.zeros((480, 640, 3), dtype=np.uint8)
                    for factory in (FaceLandmarker, HandLandmarker, PoseTracker):
                        tracker = factory()
                        trackers.append(tracker)
                        tracker.detect(blank, 100)
                    result['nativeTrackers'] = 'face, hands, pose initialized and inferred'
                    from src.tracking.parallel import ParallelTracking
                    parallel = ParallelTracking()
                    try:
                        _, timings = parallel.detect(*trackers, blank, 200)
                        result['parallelTracking'] = sorted(timings)
                    finally:
                        parallel.close()
                finally:
                    for tracker in trackers:
                        getattr(tracker, '_landmarker', tracker)._detector.close()
            except Exception as exc:
                result['success'] = False
                result['error'] = str(exc)
            finally:
                (data / 'desktop-smoke.json').write_text(json.dumps(result, ensure_ascii=False), 'utf-8')
                controls.quit()

        webview.start(smoke_test, gui='edgechromium', debug=False, private_mode=False,
                      storage_path=str(data / 'webview'), icon=str(ROOT / 'desktop-assets/app.ico'))
    except Exception as exc:
        logging.exception('Desktop startup failed')
        if args.smoke_test:
            (data / 'desktop-smoke.json').write_text(json.dumps({'success': False, 'error': str(exc)}), 'utf-8')
        elif sys.platform == 'win32':
            ctypes.windll.user32.MessageBoxW(None, f'启动失败：{exc}\n\n日志：{data / "desktop.log"}\n若缺少 WebView2，请安装 Microsoft Edge WebView2 Runtime。', '映身', 0x10)
        else:
            raise
    finally:
        server.stop()
        if mutex:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))


if __name__ == '__main__':
    main()
