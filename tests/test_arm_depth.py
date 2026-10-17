import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from src.tracking.pose_landmarker import PoseTracker

class ArmDepthTests(unittest.TestCase):
    def test_front_depth_and_hidden_wrist(self):
        with patch('src.tracking.pose_landmarker.PoseLandmarker'):
            tracker=PoseTracker()
        world=[NS(x=0.,y=.6,z=0.) for _ in range(33)]
        for i,xyz in {11:(.2,-.3,0),12:(-.2,-.3,0),13:(.3,0,-.1),14:(-.3,0,-.1),15:(.1,-.15,-.3),16:(-.1,-.15,-.3),23:(.15,.2,0),24:(-.15,.2,0)}.items():
            world[i]=NS(x=xyz[0],y=xyz[1],z=xyz[2])
        image=[NS(x=.5,y=.5,z=0,visibility=1.) for _ in range(33)]
        result=NS(pose_world_landmarks=[world],pose_landmarks=[image])
        pose=tracker.extract_angles(result,.04)
        for side in ('left','right'):
            shoulder,elbow,wrist=pose['armPoints'][side]['points']
            self.assertGreater(wrist[2],shoulder[2])
            self.assertGreater(pose['armDirections'][side+'LowerArm'][2],0)
        image[23].visibility=image[24].visibility=.1
        hidden_hips=tracker.extract_angles(result,.04)
        self.assertEqual(hidden_hips['torso'],0)
        self.assertIn('left',hidden_hips['armPoints'])
        image[15].visibility=.1
        pose=tracker.extract_angles(result,.04)
        self.assertNotIn('left',pose['armPoints'])
        self.assertNotIn('leftLowerArm',pose['armDirections'])

if __name__=='__main__':unittest.main()
