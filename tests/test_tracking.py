"""Real CPU inference using Google's portrait fixture; never opens a webcam."""
import json
import unittest
from pathlib import Path
import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from src.avatar.vrm_loader import load_vrm
from src.tracking.landmarker import FaceLandmarker, extract_rig
from src.tracking.hand_landmarker import HandLandmarker, extract_hands
from src.tracking.pose_landmarker import PoseTracker
from src.rig.solver import RigSolver
from src.main import _state_to_ws


class TrackingTests(unittest.TestCase):
    def test_real_inference_and_loss_recovery(self):
        fixture = Path('data/test-portrait.jpg')
        if not fixture.exists():
            self.skipTest('Download https://storage.googleapis.com/mediapipe-assets/portrait.jpg to data/test-portrait.jpg')
        image = cv2.imdecode(np.frombuffer(fixture.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face, hand, pose = FaceLandmarker(), HandLandmarker(), PoseTracker()
        try:
            model = load_vrm('assets/avatars/sample.vrm')
            solver = RigSolver(model, {'calibration': {'frames': 3}})
            for ts in (100, 140, 180, 220):
                raw = extract_rig(face.detect(rgb, ts))
                self.assertTrue(raw['detected'])
                self.assertEqual(len(raw['blendshapes']), 52)
                state = solver.update(raw, .04)
            self.assertTrue(solver.is_calibrated)
            hands = extract_hands(hand.detect(rgb, 100))
            body = pose.extract_angles(pose.detect(rgb, 100), .04, hands)
            # Fixture's elbows are below the shoulders. MediaPipe world Y is
            # down, so VRM's upper-arm direction must point DOWN after mapping.
            for side, rest in [('left', [1, 0, 0]), ('right', [-1, 0, 0])]:
                self.assertLess(Rotation.from_quat(body[side + 'UpperArm']).apply(rest)[1], 0)
            packet = _state_to_ws(state, hands, body)
            json.dumps(packet, allow_nan=False)
            for side, rest in [('left', [1, 0, 0]), ('right', [-1, 0, 0])]:
                self.assertLess(body['armDirections'][side + 'UpperArm'][1], 0)
            # Simulate a changed head pose and open mouth after calibration.
            moving = dict(raw)
            moving['matrix'] = raw['matrix'].copy()
            moving['matrix'][:3, :3] = raw['matrix'][:3, :3] @ Rotation.from_euler('y', .4).as_matrix()
            moving['blendshapes'] = raw['blendshapes'] | {'jawOpen': 1}
            moved = solver.update(moving, .04)
            self.assertGreater(moved['expressions']['aa'], 0)
            self.assertGreater(np.linalg.norm(Rotation.from_matrix(moved['head_delta']).as_rotvec()), 0)
            lost = solver.update({'detected': False}, .05)
            self.assertAlmostEqual(np.linalg.det(lost['head_delta']), 1, places=5)
            json.dumps(_state_to_ws(lost), allow_nan=False)
            solver.recalibrate()
            self.assertFalse(solver.is_calibrated)
        finally:
            face._detector.close()
            hand._detector.close()
            pose._landmarker._detector.close()


if __name__ == '__main__':
    unittest.main()
