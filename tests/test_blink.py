import unittest
from pathlib import Path
import numpy as np
from src.rig.blink import BlinkTracker
from src.rig.solver import RigSolver
from src.avatar.vrm_loader import load_vrm

class BlinkTests(unittest.TestCase):
    def tracker(self,baseline=.2):
        tracker=BlinkTracker()
        for _ in range(30):tracker.calibrate({'eyeBlinkLeft':baseline,'eyeBlinkRight':baseline},{'left':.3,'right':.3})
        tracker.finish_calibration()
        return tracker
    def test_moderate_detector_score_can_fully_close_both_eyes(self):
        tracker=self.tracker(.2)
        for _ in range(4):weight=tracker.update({'eyeBlinkLeft':.65,'eyeBlinkRight':.65},None,1/30)
        self.assertGreater(weight['blinkLeft'],.98)
        self.assertGreater(weight['blinkRight'],.98)
        for _ in range(5):weight=tracker.update({'eyeBlinkLeft':.2,'eyeBlinkRight':.2},{'left':.3,'right':.3},1/30)
        self.assertLess(weight['blinkLeft'],.02)
    def test_lid_geometry_closes_eye_when_blendshape_underestimates_it(self):
        tracker=self.tracker()
        for _ in range(4):weight=tracker.update({'eyeBlinkLeft':.25,'eyeBlinkRight':.2},{'left':.06,'right':.3},1/30)
        self.assertGreater(weight['blinkLeft'],.98)
        self.assertLess(weight['blinkRight'],.05)
    def test_accidental_blink_during_calibration_does_not_raise_open_baseline(self):
        tracker=BlinkTracker()
        for i in range(30):tracker.calibrate({'eyeBlinkLeft':.9 if i==10 else .1})
        tracker.finish_calibration()
        self.assertAlmostEqual(tracker._baseline['Left'],.1)
    def test_wide_eye_outlier_does_not_redefine_open_eyes(self):
        tracker=self.tracker()
        tracker.update({'eyeBlinkLeft':.2,'eyeBlinkRight':.2},{'left':.9,'right':.9},.04)
        weight=tracker.update({'eyeBlinkLeft':.2,'eyeBlinkRight':.2},{'left':.3,'right':.3},.04)
        self.assertLess(weight['blinkLeft'],.05)

    def test_eye_geometry_is_aspect_and_head_yaw_invariant(self):
        from types import SimpleNamespace as NS
        from src.tracking.landmarker import extract_rig
        for aspect in (4/3,16/9):
            for angle in (0,np.pi/4):
                landmarks=[NS(x=0.,y=0.,z=0.) for _ in range(478)]
                for indices in [(362,263,386,374,385,380),(33,133,159,145,158,153)]:
                    for i,(x,y) in zip(indices,[(-.05,0),(.05,0),(-.01,-.015),(-.01,.015),(.01,-.015),(.01,.015)]):
                        landmarks[i]=NS(x=.5+x*np.cos(angle),y=.5+y*aspect,z=x*np.sin(angle))
                result=NS(face_landmarks=[landmarks],face_blendshapes=[],facial_transformation_matrixes=[])
                eye=extract_rig(result,aspect)['eye_openness']
                self.assertAlmostEqual(eye['left'],.3,places=5)
                self.assertAlmostEqual(eye['right'],.3,places=5)

    def test_solver_emits_closed_signal_after_calibration_without_changing_mouth(self):
        solver=RigSolver(load_vrm('assets/avatars/sample.vrm'),{'calibration':{'frames':3}})
        raw={'detected':True,'matrix':np.eye(4),'blendshapes':{'eyeBlinkLeft':.2,'eyeBlinkRight':.2,'jawOpen':.1},'eye_openness':{'left':.3,'right':.3}}
        for _ in range(3):solver.update(raw,.04)
        closed={**raw,'blendshapes':{**raw['blendshapes'],'eyeBlinkLeft':.65,'eyeBlinkRight':.65}}
        for _ in range(4):state=solver.update(closed,.04)
        self.assertGreater(state['expressions']['blinkLeft'],.98)
        self.assertEqual(state['expressions']['aa'],0)
        self.assertGreater(state['eye_signal']['closedRight'],.98)
        solver.recalibrate()
        self.assertFalse(solver.is_calibrated)

if __name__=='__main__':unittest.main()
