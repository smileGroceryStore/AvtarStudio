"""MediaPipe HandLandmarker wrapper (CPU, VIDEO mode, 2 hands).

Outputs per detection:
  * Per-joint finger angles [0,1] (0=straight, 1=fully curled)
  * Handedness (Left/Right, swapped for un-mirrored feed)

Finger angles are computed from WORLD landmarks (3D, meters, correct scale)
rather than image landmarks (where Z has a different scale, distorting angles).
"""
from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = _PROJECT_ROOT / "assets" / "models" / "hand_landmarker.task"

# Landmark indices
_WRIST = 0
_THUMB_CMC, _THUMB_MCP, _THUMB_IP, _THUMB_TIP = 1, 2, 3, 4
_INDEX_MCP, _INDEX_PIP, _INDEX_DIP, _INDEX_TIP = 5, 6, 7, 8
_MIDDLE_MCP, _MIDDLE_PIP, _MIDDLE_DIP, _MIDDLE_TIP = 9, 10, 11, 12
_RING_MCP, _RING_PIP, _RING_DIP, _RING_TIP = 13, 14, 15, 16
_LITTLE_MCP, _LITTLE_PIP, _LITTLE_DIP, _LITTLE_TIP = 17, 18, 19, 20


def ensure_model() -> Path:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 0:
        return MODEL_PATH
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"[hand] downloading model to {MODEL_PATH} ...", flush=True)
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


class HandLandmarker:
    def __init__(
        self,
        num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        model_path = str(ensure_model())
        base_options = mp_python.BaseOptions(model_asset_buffer=Path(model_path).read_bytes())
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, rgb_frame: np.ndarray, timestamp_ms: int) -> Any:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        return self._detector.detect_for_video(image, timestamp_ms)


def _joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Flexion angle at joint *b* given consecutive points a→b→c. Returns radians.

    Straight finger: segments a→b and b→c point the same way → 0.
    Curled finger: segments bend up to ~π.
    """
    v1 = b - a
    v2 = c - b
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-8 or n2 < 1e-8:
        return 0.0
    cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.arccos(cos_a))


def _compute_finger_angles(pts: np.ndarray) -> dict[str, list[float]]:
    """Per-joint flexion angles for each finger. 0=straight, 1=curled.

    *pts* must be 3D points with correct scale (world landmarks, not image).
    Returns {finger: [joint_angles...]} where joint order is proximal→distal.
    """
    w = pts[_WRIST]
    return {
        "thumb": [
            _joint_angle(w, pts[_THUMB_CMC], pts[_THUMB_MCP]),
            _joint_angle(pts[_THUMB_CMC], pts[_THUMB_MCP], pts[_THUMB_IP]),
            _joint_angle(pts[_THUMB_MCP], pts[_THUMB_IP], pts[_THUMB_TIP]),
        ],
        "index": [
            _joint_angle(w, pts[_INDEX_MCP], pts[_INDEX_PIP]),
            _joint_angle(pts[_INDEX_MCP], pts[_INDEX_PIP], pts[_INDEX_DIP]),
            _joint_angle(pts[_INDEX_PIP], pts[_INDEX_DIP], pts[_INDEX_TIP]),
        ],
        "middle": [
            _joint_angle(w, pts[_MIDDLE_MCP], pts[_MIDDLE_PIP]),
            _joint_angle(pts[_MIDDLE_MCP], pts[_MIDDLE_PIP], pts[_MIDDLE_DIP]),
            _joint_angle(pts[_MIDDLE_PIP], pts[_MIDDLE_DIP], pts[_MIDDLE_TIP]),
        ],
        "ring": [
            _joint_angle(w, pts[_RING_MCP], pts[_RING_PIP]),
            _joint_angle(pts[_RING_MCP], pts[_RING_PIP], pts[_RING_DIP]),
            _joint_angle(pts[_RING_PIP], pts[_RING_DIP], pts[_RING_TIP]),
        ],
        "little": [
            _joint_angle(w, pts[_LITTLE_MCP], pts[_LITTLE_PIP]),
            _joint_angle(pts[_LITTLE_MCP], pts[_LITTLE_PIP], pts[_LITTLE_DIP]),
            _joint_angle(pts[_LITTLE_PIP], pts[_LITTLE_DIP], pts[_LITTLE_TIP]),
        ],
    }


def _compute_palm_orientation(pts: np.ndarray) -> dict | None:
    """Palm frame in the same canonical world axes as PoseTracker."""
    index = pts[_INDEX_MCP] - pts[_WRIST]
    little = pts[_LITTLE_MCP] - pts[_WRIST]
    direction = (index + little) * .5
    normal = np.cross(index, little)
    d, n = np.linalg.norm(direction), np.linalg.norm(normal)
    if d < 1e-6 or n < 1e-8 or n / max(np.linalg.norm(index)*np.linalg.norm(little), 1e-8) < .08:
        return None
    axes = np.array([1., -1., -1.])
    return dict(direction=(direction / d * axes).tolist(), normal=(normal / n * axes).tolist())


def _compute_palm_twist(pts: np.ndarray, is_left: bool) -> float:
    # Legacy consumer fallback; atan2 distinguishes front/back over a full turn.
    palm = _compute_palm_orientation(pts)
    if palm is None:
        return 0.0
    normal = palm['normal']
    return float(np.arctan2(normal[1], normal[2]))


def _hand_sides(result, pose_result=None):
    """Match image wrists to anatomical Pose wrists, including crossed hands."""
    count = len(result.hand_landmarks)
    fallback = []
    for i in range(count):
        categories = result.handedness[i] if result.handedness and i < len(result.handedness) else []
        label = categories[0].category_name.lower() if categories else 'right'
        fallback.append('right' if label == 'left' else 'left')
    poses = getattr(pose_result, 'pose_landmarks', None)
    if not poses or count not in (1, 2):
        return fallback
    wrists = {}
    for side, index in [('left', 15), ('right', 16)]:
        point = poses[0][index]
        if getattr(point, 'visibility', 1.) >= .4:
            wrists[side] = np.array([point.x, point.y])
    from itertools import permutations
    options = []
    for assignment in permutations(wrists, count):
        distances = [float(np.linalg.norm(np.array([result.hand_landmarks[i][0].x, result.hand_landmarks[i][0].y])-wrists[side])) for i, side in enumerate(assignment)]
        if max(distances) <= .22:
            options.append((sum(distances), assignment))
    if not options:
        return fallback
    options.sort(key=lambda item: item[0])
    if len(options)>1 and options[1][0]-options[0][0]<.015:
        return fallback
    return list(options[0][1])


def extract_hands(result: Any, pose_result: Any = None) -> dict[str, dict | None]:
    """Parse HandLandmarkerResult into per-hand finger angles.

    Returns ``{"left": {...}|None, "right": {...}|None}`` where each hand dict
    has ``"fingers"`` (dict of joint angles per finger, 0=straight 1=curled).
    """
    out: dict[str, dict | None] = {"left": None, "right": None}
    if not result.hand_landmarks:
        return out

    world_lms_list = getattr(result, "hand_world_landmarks", None) or []

    sides = _hand_sides(result, pose_result)
    for i, lms in enumerate(result.hand_landmarks):
        side = sides[i]

        # Use world landmarks for angle computation (correct 3D scale).
        # Fall back to image landmarks if world landmarks unavailable.
        if i < len(world_lms_list) and len(world_lms_list[i]) >= 21:
            wl = world_lms_list[i]
            pts = np.array(
                [[lm.x, lm.y, lm.z] for lm in wl], dtype=np.float32
            )
        else:
            pts = np.array(
                [[lm.x, lm.y, lm.z] for lm in lms], dtype=np.float32
            )

        out[side] = {
            "fingers": _compute_finger_angles(pts),
            "palm": _compute_palm_orientation(pts),
            "twist": _compute_palm_twist(pts, is_left=(side == "left")),
        }

    return out
