"""Local-only Avatar Studio. Camera access starts only after an explicit UI action."""
from __future__ import annotations
import asyncio
import json
import math
import os
import threading
import time
from pathlib import Path
from aiohttp import web

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('AVATAR_STUDIO_DATA', ROOT / 'data'))
DEFAULTS = dict(blinkSensitivity=1.0, sensitivity=1.0, smoothing=0.55, expression=1.3, zoom=1.0,
                height=0.0, idlePose='natural', avatarMode='3d', petColor='mint', background='studio', mirror=False, body=True, hands=True, clothingClearance=True)


class Studio:
    def __init__(self):
        DATA.mkdir(parents=True, exist_ok=True)
        try:
            saved = json.loads((DATA / 'settings.json').read_text('utf-8'))
        except (OSError, ValueError):
            saved = {}
        self.settings = DEFAULTS | {k: v for k, v in saved.items() if k in DEFAULTS}
        if self.settings['idlePose'] not in ('natural', 'sway'):
            self.settings['idlePose'] = 'natural'
        self.avatar = DATA / 'avatar.vrm' if (DATA / 'avatar.vrm').exists() else ROOT / 'assets/avatars/sample.vrm'
        self.name = saved.get('avatarName', '示例角色 · VRoid')
        self.version = 0
        self.blink_test_until = 0.
        self.running = False
        self.camera_index = 0
        self.calibrate = threading.Event()
        self.shutdown = threading.Event()
        self.status = 'ready'
        self.error = ''
        self.jpeg = None
        self.rig = {}
        self.fps = 0.0
        self.inference_ms = 0.0
        self.stage_ms = {}
        self.capture_stats = {}
        self.processing_age_ms = 0.
        self.lock = threading.Lock()
        self.clients = set()
        self.preview_clients = 0

    def snapshot(self):
        with self.lock:
            return dict(type='state', testBlink=time.monotonic()<self.blink_test_until, running=self.running, status=self.status, error=self.error,
                        avatarName=self.name, avatarVersion=self.version, hasAvatar=self.avatar.exists(),
                        cameraIndex=self.camera_index, settings=dict(self.settings), fps=round(self.fps, 1), inferenceMs=round(self.inference_ms, 1), stageMs=dict(self.stage_ms), camera=dict(self.capture_stats), processingAgeMs=round(self.processing_age_ms,1), rig=self.rig)

    def save(self):
        temporary = DATA / 'settings.tmp'
        temporary.write_text(json.dumps(self.settings | {'avatarName': self.name}, ensure_ascii=False), 'utf-8')
        temporary.replace(DATA / 'settings.json')

    def worker(self):
        try:
            self._tracking_worker()
        except Exception as exc:
            self.error = f'追踪模块初始化失败：{exc}'
            self.status = 'error'
            self.running = False

    def _tracking_worker(self):
        # Import tracking lazily: the workspace remains usable without a camera.
        import cv2
        import numpy as np
        from scipy.spatial.transform import Rotation
        from src.avatar.vrm_loader import load_vrm
        from src.capture.webcam import WebcamCapture
        from src.tracking.landmarker import FaceLandmarker, extract_rig
        from src.tracking.hand_landmarker import HandLandmarker, extract_hands
        from src.tracking.pose_landmarker import PoseTracker
        from src.rig.solver import RigSolver
        from src.rig.hand_smoothing import HandSmoother
        from src.tracking.parallel import ParallelTracking
        from src.tracking.arm_stabilizer import ArmStabilizer
        from src.main import _draw_landmarks, _draw_hand_landmarks, _draw_pose_landmarks, _state_to_ws

        trackers = None
        while not self.shutdown.wait(0.05):
            if not self.running:
                continue
            cap = None
            pipeline = None
            try:
                self.status, self.error = 'starting', ''
                if not trackers:
                    trackers = FaceLandmarker(), HandLandmarker(), PoseTracker(filter_directions=False)
                face, hand, pose = trackers
                version, index = self.version, self.camera_index
                solver = RigSolver(load_vrm(self.avatar), {'head':{'min_cutoff':2.5,'beta':.08}})
                cap = WebcamCapture(index=index)
                cap.start()
                self.calibrate.clear()
                start = previous = last_frame = time.monotonic()
                frames = 0
                hand_smoother = HandSmoother()
                arm_stabilizer = ArmStabilizer()
                pipeline = ParallelTracking()
                last_preview = time.monotonic() - 1
                last_metrics = time.monotonic()
                metrics_frames = 0
                self.status = 'calibrating'
                while self.running and not self.shutdown.is_set():
                    if version != self.version or index != self.camera_index:
                        break
                    if self.calibrate.is_set():
                        solver.recalibrate()
                        hand_smoother = HandSmoother()
                        arm_stabilizer.reset()
                        pose = PoseTracker(filter_directions=False)
                        old_pose = trackers[2]
                        old_pose._landmarker._detector.close()
                        trackers = face, hand, pose
                        self.calibrate.clear()
                    if hasattr(cap, 'get_latest_packet'):
                        frame, fresh, captured_at = cap.get_latest_packet()
                    else:
                        frame, fresh = cap.get_latest()
                        captured_at = time.monotonic()
                    now = time.monotonic()
                    if frame is None or not fresh:
                        if now - last_frame > 5:
                            raise RuntimeError('摄像头超过 5 秒未返回画面，请检查占用或切换设备编号。')
                        time.sleep(.005)
                        continue
                    last_frame = now
                    dt, previous = min(now - previous, .2), now
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    ts = time.monotonic_ns() // 1_000_000
                    detected, timings = pipeline.detect(face, hand, pose, rgb, ts,
                        hands=self.settings['hands'], body=self.settings['body'])
                    result, hand_result = detected['face'], detected.get('hands')
                    hands = hand_smoother.update(extract_hands(hand_result, detected.get('pose')) if hand_result else None, dt)
                    pose_result = detected.get('pose')
                    angles = pose.extract_angles(pose_result, dt, hands) if pose_result else None
                    if self.settings['body']:
                        angles = arm_stabilizer.update(angles, dt)
                    else:
                        arm_stabilizer.reset()
                    was_calibrated = solver.is_calibrated
                    state = solver.update(extract_rig(result, rgb.shape[1]/rgb.shape[0]), dt, blink_sensitivity=self.settings['blinkSensitivity'])
                    if solver.is_calibrated and not was_calibrated:
                        pose.calibrate_neutral()
                    self.status = 'tracking' if result.face_landmarks and solver.is_calibrated else ('calibrating' if result.face_landmarks else 'no-face')
                    rig = _state_to_ws(state, hands, angles)
                    rig['calibrated'] = solver.is_calibrated
                    rig['eyeSignal'] = state.get('eye_signal',{})
                    self.inference_ms = (time.monotonic() - now) * 1000
                    jpeg = None
                    if self.preview_clients and now - last_preview >= 1 / 15:
                        annotated = _draw_landmarks(frame, result)
                        if hand_result:
                            annotated = _draw_hand_landmarks(annotated, hand_result)
                        if pose_result:
                            annotated = _draw_pose_landmarks(annotated, pose_result)
                        ok, encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
                        jpeg = encoded.tobytes() if ok else None
                        last_preview = now
                    frames += 1
                    metrics_frames += 1
                    with self.lock:
                        self.stage_ms = timings
                        self.capture_stats = cap.stats() if hasattr(cap,'stats') else {}
                        self.processing_age_ms = max(0,(time.monotonic()-captured_at)*1000)
                        self.rig = rig
                        if jpeg:
                            self.jpeg = jpeg
                        if now - last_metrics >= .5:
                            self.fps = metrics_frames / (now - last_metrics)
                            last_metrics, metrics_frames = now, 0
                    time.sleep(max(0, 1 / 30 - (time.monotonic() - now)))
            except Exception as exc:
                self.error = str(exc)
                self.status = 'error'
                self.running = False
            finally:
                if pipeline:
                    pipeline.close()
                if cap:
                    cap.stop()
                with self.lock:
                    self.jpeg = None
                    self.rig = {}
                    self.fps = 0
                    self.inference_ms = 0
                    self.stage_ms = {}
                    self.capture_stats = {}
                    self.processing_age_ms = 0.
                if not self.running and self.status != 'error':
                    self.status = 'ready'
        if trackers:
            for tracker in trackers:
                detector = getattr(getattr(tracker, '_landmarker', tracker), '_detector', None)
                if detector:
                    detector.close()


def validate_settings(payload):
    result = {}
    for key, value in payload.items():
        if key not in DEFAULTS:
            raise web.HTTPBadRequest(text='未知设置')
        if key in ('mirror', 'body', 'hands', 'clothingClearance'):
            if type(value) is not bool:
                raise web.HTTPBadRequest(text='开关必须为布尔值')
        elif key in ('avatarMode', 'petColor'):
            choices = ('3d', '2d') if key == 'avatarMode' else ('mint', 'rose', 'blue')
            if value not in choices:
                raise web.HTTPBadRequest(text='不支持的角色选项')
        elif key == 'idlePose':
            if value not in ('natural', 'sway'):
                raise web.HTTPBadRequest(text='不支持的预设姿势')
        elif key == 'background':
            if value not in ('studio', 'green', 'transparent'):
                raise web.HTTPBadRequest(text='不支持的背景')
        else:
            lo, hi = {'blinkSensitivity': (.8, 1.8), 'sensitivity': (.2, 2), 'smoothing': (0, .95), 'expression': (.2, 3), 'zoom': (.5, 2), 'height': (-.5, .5)}[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
                raise web.HTTPBadRequest(text='设置超出范围')
        result[key] = value
    return result


def create_app(studio=None, shutdown_callback=None):
    s = studio or Studio()

    @web.middleware
    async def local_only(request, handler):
        origin = request.headers.get('Origin')
        if origin and origin != f'{request.scheme}://{request.host}':
            raise web.HTTPForbidden(text='仅接受同源操作')
        if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            raise web.HTTPForbidden(text='仅本机访问')
        return await handler(request)

    app = web.Application(client_max_size=100 * 1024 * 1024, middlewares=[local_only])

    async def index(request):
        return web.FileResponse(ROOT / 'dist/index.html')

    async def state(request):
        return web.json_response(s.snapshot(), headers={'Cache-Control': 'no-store'})

    async def control(request):
        data = await request.json()
        action = data.get('action')
        if action == 'start':
            index = data.get('cameraIndex', 0)
            if type(index) is not int or not 0 <= index <= 9:
                raise web.HTTPBadRequest(text='设备编号应为 0–9')
            if not s.avatar.exists():
                raise web.HTTPBadRequest(text='请先导入 VRM 模型')
            s.camera_index = index
            s.error = ''
            s.running = True
            s.status = 'starting'
        elif action in ('stop', 'shutdown'):
            s.running = False
            s.rig = {}
            s.jpeg = None
            s.status = 'stopping'
            if action == 'shutdown':
                def exit_server():
                    if shutdown_callback:
                        shutdown_callback()
                    else:
                        raise web.GracefulExit()
                asyncio.get_running_loop().call_later(.3, exit_server)
        elif action == 'test-blink':
            s.blink_test_until = time.monotonic()+1.2
        elif action == 'calibrate':
            if not s.running:
                raise web.HTTPBadRequest(text='请先开始捕捉')
            s.calibrate.set()
            s.status = 'calibrating'
        elif action == 'settings':
            s.settings.update(validate_settings(data.get('settings', {})))
            s.save()
        else:
            raise web.HTTPBadRequest(text='未知操作')
        return web.json_response(s.snapshot())

    def personal_models():
        folder = (DATA / 'library').resolve()
        try:
            entries = json.loads((folder / 'catalog.json').read_text('utf-8'))
        except (OSError, ValueError):
            return []
        result = []
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            key = str(entry.get('id', ''))
            filename = str(entry.get('file', ''))
            path = (folder / filename).resolve()
            if not key or not key.isascii() or not all(c.isalnum() or c == '-' for c in key):
                continue
            if path.parent != folder or path.suffix.lower() != '.vrm' or not path.is_file():
                continue
            result.append(dict(id='personal-'+key, name=str(entry.get('name', filename)),
                               file=filename, assetUrl='/api/library/'+key,
                               notice=str(entry.get('notice', '')), path=path))
        return result

    async def library(request):
        return web.json_response([{k:v for k,v in item.items() if k != 'path'} for item in personal_models()])

    async def library_file(request):
        item = next((x for x in personal_models() if x['id'] == 'personal-'+request.match_info['key']), None)
        if item is None:
            raise web.HTTPNotFound(text='个人角色不存在')
        return web.FileResponse(item['path'], headers={'Cache-Control':'no-store'})

    async def avatar(request):
        if not s.avatar.exists():
            raise web.HTTPNotFound(text='尚未导入角色')
        return web.FileResponse(s.avatar, headers={'Cache-Control': 'no-store'})

    async def upload(request):
        if s.running:
            raise web.HTTPConflict(text='请先停止捕捉，再更换角色')
        name = request.headers.get('X-Avatar-Name', 'custom.vrm')
        from urllib.parse import unquote
        name = Path(unquote(name)).name
        if not name.lower().endswith('.vrm'):
            raise web.HTTPBadRequest(text='请选择 .vrm 文件')
        blob = await request.read()
        temporary = DATA / 'upload.vrm'
        try:
            if len(blob) < 20 or blob[:4] != b'glTF':
                raise ValueError('不是有效的 VRM 二进制文件')
            temporary.write_bytes(blob)
            from src.avatar.vrm_loader import load_vrm
            model = await asyncio.to_thread(load_vrm, temporary)
            if not model.humanoid_bone_by_name.get('head') and 'head' not in model.humanoid_bone_by_name:
                raise ValueError('模型缺少 head 骨骼')
            if not model.humanoid_bone_by_name:
                raise ValueError('模型缺少 VRM 人形骨骼')
            temporary.replace(DATA / 'avatar.vrm')
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            raise web.HTTPBadRequest(text=f'导入失败：{exc}')
        s.avatar = DATA / 'avatar.vrm'
        s.name = name
        s.version += 1
        s.save()
        return web.json_response(s.snapshot())

    async def camera(request):
        response = web.StreamResponse(headers={'Content-Type': 'multipart/x-mixed-replace; boundary=frame', 'Cache-Control': 'no-store'})
        await response.prepare(request)
        s.preview_clients += 1
        try:
            while s.running:
                jpeg = s.jpeg
                if jpeg:
                    await response.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
                await asyncio.sleep(1 / 15)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            s.preview_clients -= 1
            if not s.preview_clients:
                s.jpeg = None
        return response

    async def websocket(request):
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        s.clients.add(ws)
        try:
            async for _ in ws:
                pass
        finally:
            s.clients.discard(ws)
        return ws

    async def broadcast():
        while True:
            if s.clients:
                payload = json.dumps(s.snapshot(), allow_nan=False)
                for ws in list(s.clients):
                    try:
                        await ws.send_str(payload)
                    except ConnectionError:
                        s.clients.discard(ws)
            await asyncio.sleep(1 / 30)

    async def lifecycle(app):
        thread = threading.Thread(target=s.worker, daemon=True, name='tracking')
        thread.start()
        task = asyncio.create_task(broadcast())
        yield
        s.running = False
        s.shutdown.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        for ws in list(s.clients):
            await ws.close()
        await asyncio.to_thread(thread.join, 5)

    app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/', index)
    app.router.add_get('/output', index)
    app.router.add_get('/widget', index)
    app.router.add_get('/api/state', state)
    app.router.add_post('/api/control', control)
    app.router.add_get('/api/library', library)
    app.router.add_get('/api/library/{key}', library_file)
    app.router.add_get('/api/avatar', avatar)
    app.router.add_post('/api/avatar', upload)
    app.router.add_get('/camera', camera)
    app.router.add_get('/ws', websocket)
    if (ROOT / 'dist/assets').exists():
        app.router.add_static('/assets/', ROOT / 'dist/assets')
    return app


if __name__ == '__main__':
    web.run_app(create_app(), host='127.0.0.1', port=8080)
