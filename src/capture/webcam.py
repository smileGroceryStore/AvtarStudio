"""Background-thread webcam capture with a latest-frame-only slot.

The capture thread reads continuously and keeps only the most recent frame;
stale frames are dropped so consumer latency stays bounded regardless of how
fast the downstream pipeline reads. ``cv2.VideoCapture.read`` allocates a fresh
array per call, so the reference returned to the consumer is never mutated by
the next capture.
"""
from __future__ import annotations

import threading
import time
import sys
from typing import Optional

import cv2
import numpy as np


class WebcamCapture:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480, fps: int = 30) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._latest: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._new = False
        self._captured_at = 0.
        self._capture_fps = 0.
        self._fps_frames = 0
        self._fps_start = time.monotonic()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        # Windows laptop drivers differ in their DirectShow/Media Foundation
        # support. Retry only the selected device, never another camera.
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == 'win32' else [cv2.CAP_ANY]
        for backend in backends:
            candidate = cv2.VideoCapture(self.index, backend)
            if candidate.isOpened():
                self._cap = candidate
                break
            candidate.release()
        if self._cap is None:
            raise RuntimeError(
                f"无法打开摄像头（设备 {self.index}）。请先打开 Windows 自带“相机”确认设备可用；"
                "若提示找不到摄像头，请检查笔记本摄像头物理开关或键盘摄像头快捷键。"
                "若相机能正常使用，请将其关闭，并检查 Windows 设置中的“允许桌面应用访问摄像头”，再重试。"
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        # Keep the camera's native pixel format; many integrated cameras do
        # not expose MJPG at their default resolution.
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        self._fps_start = time.monotonic()
        self._fps_frames = 0
        self._capture_fps = 0.
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="webcam", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                time.sleep(0.005)
                continue
            now = time.monotonic()
            with self._lock:
                self._captured_at = now
                self._fps_frames += 1
                if now-self._fps_start >= .5:
                    self._capture_fps = self._fps_frames/(now-self._fps_start)
                    self._fps_frames = 0
                    self._fps_start = now
                self._latest = frame
                self._new = True

    def get_latest(self) -> tuple[Optional[np.ndarray], bool]:
        """Return ``(frame_bgr, is_new)``.

        ``is_new`` is True only on the first call after a fresh frame arrived,
        so the consumer can skip redundant tracking work when re-using a frame.
        """
        frame, new, _ = self.get_latest_packet()
        return frame, new

    def get_latest_packet(self):
        """Atomically attach the driver's read-completion time to the frame."""
        with self._lock:
            frame, new = self._latest, self._new
            self._new = False
            return frame, new, self._captured_at

    def stats(self):
        with self._lock:
            shape = self._latest.shape if self._latest is not None else None
            return {'width': int(shape[1]) if shape else 0,
                    'height': int(shape[0]) if shape else 0,
                    'fps': round(self._capture_fps, 1)}

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._cap is not None:
            self._cap.release()
        self._cap = None
