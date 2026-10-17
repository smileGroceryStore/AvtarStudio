import math
import unittest
from src.rig.hand_smoothing import HandSmoother


class HandTests(unittest.TestCase):
    def hand(self, twist=0, curl=0):
        return {'left': {'twist': twist, 'fingers': {'index': [curl, curl, curl]}}, 'right': None}

    def test_twist_crossing_pi_does_not_jump_through_zero(self):
        smooth = HandSmoother()
        smooth.update(self.hand(math.pi-.01), 1/30)
        result = smooth.update(self.hand(-math.pi+.01), 1/30)
        self.assertGreater(abs(result['left']['twist']), 3)

    def test_jitter_is_filtered_and_lost_hand_is_released(self):
        smooth = HandSmoother()
        smooth.update(self.hand(curl=.3), 1/30)
        value = smooth.update(self.hand(curl=.5), 1/30)['left']['fingers']['index'][0]
        self.assertGreater(value, .3)
        self.assertLess(value, .5)
        self.assertIsNone(smooth.update(None, 1/30)['left'])
        self.assertFalse(smooth.filters)


if __name__ == '__main__':
    unittest.main()
