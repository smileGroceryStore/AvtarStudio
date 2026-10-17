"""Filter fingers and circular wrist twist without retaining lost hands."""
import math
from src.rig.one_euro import OneEuroFilter


class HandSmoother:
    def __init__(self):
        self.filters = {}

    def _filter(self, key, value, dt):
        return self.filters.setdefault(key, OneEuroFilter(3.0, .08)).filter(value, dt)

    def update(self, hands, dt):
        result = {}
        for side in ('left', 'right'):
            hand = hands.get(side) if hands else None
            if not hand:
                self.filters = {k: v for k, v in self.filters.items() if k[0] != side}
                result[side] = None
                continue
            filtered = dict(hand)
            filtered['fingers'] = {
                finger: [self._filter((side, finger, j), max(0, min(2, value)), dt)
                         for j, value in enumerate(angles)]
                for finger, angles in hand.get('fingers', {}).items()
            }
            twist = hand.get('twist', 0)
            filtered['twist'] = math.atan2(self._filter((side, 'sin'), math.sin(twist), dt),
                                           self._filter((side, 'cos'), math.cos(twist), dt))
            result[side] = filtered
        return result
