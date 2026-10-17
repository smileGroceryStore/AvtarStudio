import unittest,threading,copy
import numpy as np
from src.tracking.arm_stabilizer import ArmStabilizer
from src.tracking.parallel import ParallelTracking


def pose(upper=(.08,-.3,.02),lower=(-.1,-.1,.25)):
    a=np.array(upper,dtype=float);b=a+np.array(lower,dtype=float)
    return {'armPoints':{'left':{'points':[[0,0,0],a.tolist(),b.tolist()],'shoulderSpan':.4}}}

class MotionOptimizationTests(unittest.TestCase):
    def test_same_frame_models_really_overlap(self):
        barrier=threading.Barrier(3)
        frame=object()
        class Tracker:
            def detect(self,image,ts):
                self.assertions=(image is frame,ts==100)
                barrier.wait(timeout=2)
                return 1
        trackers=[Tracker() for _ in range(3)];pipeline=ParallelTracking()
        try:
            results,timings=pipeline.detect(*trackers,frame,100)
            self.assertEqual(set(results),{'face','hands','pose'})
            self.assertTrue(all(all(t.assertions) for t in trackers))
            self.assertTrue(all(v>=0 for v in timings.values()))
        finally:pipeline.close()

    def test_short_loss_holds_but_long_loss_relaxes(self):
        s=ArmStabilizer();p=s.update(pose(),.04)
        self.assertEqual(s.update(None,.04)['armPoints'],p['armPoints'])
        self.assertIsNotNone(s.update(None,.04))
        self.assertIsNone(s.update(None,.05))

    def test_depth_scale_noise_does_not_stretch_arm(self):
        s=ArmStabilizer();a=s.update(pose(),.04)
        altered=pose((.16,-.6,.04),(-.2,-.2,.5))
        b=s.update(altered,.04)
        length=lambda p:np.linalg.norm(np.diff(np.array(p['armPoints']['left']['points']),axis=0),axis=1)
        self.assertTrue(np.all(length(b)<length(a)*1.03))

    def test_single_reversal_is_rejected_but_confirmed_motion_recovers(self):
        s=ArmStabilizer();a=s.update(pose(),.033)
        flipped=pose((-.08,.3,-.02),(.1,.1,-.25))
        b=s.update(flipped,.033)
        self.assertEqual(a['armDirections'],b['armDirections'])
        for _ in range(12):b=s.update(flipped,.033)
        self.assertGreater(b['armDirections']['leftUpperArm'][1],0)

    def test_adaptive_filter_reduces_stationary_jitter(self):
        s=ArmStabilizer();raw=[];stable=[]
        for i in range(90):
            x=.08+.025*(-1 if i%2 else 1)
            p=pose((x,-.3,.02));out=s.update(p,1/30)
            raw.append(x/np.linalg.norm([x,-.3,.02]));stable.append(out['armDirections']['leftUpperArm'][0])
        self.assertLess(np.std(stable[15:]),np.std(raw[15:])*.6)

    def test_elbow_does_not_reverse_through_shoulder(self):
        s=ArmStabilizer()
        out=s.update(pose((0,-.3,0),(0,.3,0)),.04)
        upper=out['armDirections']['leftUpperArm'];lower=out['armDirections']['leftLowerArm']
        self.assertGreaterEqual(float(np.dot(upper,lower)),np.cos(np.radians(160))-1e-6)
        self.assertGreater(lower[2],0)

    def test_disabled_models_are_not_run(self):
        class Tracker:
            def detect(self,*args):return 'face'
        class Disabled:
            def detect(self,*args):raise AssertionError('disabled model ran')
        p=ParallelTracking()
        try:
            result,_=p.detect(Tracker(),Disabled(),Disabled(),object(),100,hands=False,body=False)
            self.assertEqual(result,{'face':'face'})
        finally:p.close()

if __name__=='__main__':unittest.main()
