"""Consistent arm geometry for both 2D and VRM, with brief loss tolerance."""
import copy
import math
import numpy as np
from src.rig.one_euro import OneEuroFilter


def constrain_elbow(upper, lower, side):
    """Avoid an inferred forearm folding completely back through the shoulder."""
    dot = float(np.clip(np.dot(upper,lower),-1,1))
    minimum = math.cos(math.radians(160))
    if dot >= minimum:
        return lower
    pole = lower-upper*dot
    if np.linalg.norm(pole)<1e-5:
        forward = np.array([0.,0.,1.])
        pole = forward-upper*np.dot(forward,upper)
        if np.linalg.norm(pole)<1e-5:
            outward = np.array([1. if side=='left' else -1.,0.,0.])
            pole = outward-upper*np.dot(outward,upper)
    pole /= max(np.linalg.norm(pole),1e-6)
    return upper*minimum + pole*math.sin(math.radians(160))


class ArmStabilizer:
    def __init__(self, hold_seconds=.12):
        self.hold_seconds = hold_seconds
        self.reset()

    def reset(self):
        self._arms = {}
        self._base = None
        self._base_age = 0.

    def update(self, pose, dt):
        dt = max(.001, min(.25, dt))
        if pose is not None:
            self._base = copy.deepcopy(pose)
            self._base_age = 0.
        else:
            self._base_age += dt
        output = copy.deepcopy(pose or (self._base if self._base_age <= self.hold_seconds else {}) or {})
        output['armPoints'], output['armDirections'] = {}, {}
        for side in ('left', 'right'):
            output.pop(side+'UpperArm', None)
            output.pop(side+'LowerArm', None)
            state = self._arms.get(side)
            if state: state['age'] += dt
            entry = (pose or {}).get('armPoints', {}).get(side)
            valid = False
            if entry:
                points = np.asarray(entry.get('points'), dtype=float)
                if points.shape == (3, 3) and np.isfinite(points).all():
                    vectors = np.diff(points, axis=0)
                    lengths = np.linalg.norm(vectors, axis=1)
                    valid = bool(np.all((lengths > .05) & (lengths < .8)))
                    if valid:
                        units = vectors / lengths[:, None]
                        # Reject a single implausible reversal, but accept a
                        # large real movement once the next frame confirms it.
                        if state and np.min(np.sum(units*state['units'], axis=1)) < -.25:
                            previous = state['pending']
                            valid = previous is not None and np.min(np.sum(previous*units, axis=1)) > .85
                            state['pending'] = units.copy()
                        elif state:
                            state['pending'] = None
            if valid:
                if not state:
                    state = dict(age=0., units=units.copy(), pending=None, lengths=lengths.copy(),
                                 filters=[[OneEuroFilter(2.2, .6) for _ in range(3)] for _ in range(2)],
                                 span=OneEuroFilter(1.5, .1))
                    self._arms[side] = state
                state['age'] = 0.
                state['pending'] = None
                # Human bone length is stable: do not stretch the avatar when
                # depth estimation changes apparent segment lengths.
                a = 1-math.exp(-dt*.5)
                state['lengths'] += (lengths-state['lengths'])*a
                filtered = np.array([[f.filter(float(units[j,i]), dt) for i,f in enumerate(row)]
                                     for j,row in enumerate(state['filters'])])
                filtered /= np.maximum(np.linalg.norm(filtered, axis=1)[:,None], 1e-6)
                filtered[1] = constrain_elbow(filtered[0],filtered[1],side)
                state['units'] = filtered
                origin = points[0]
                elbow = origin + filtered[0]*state['lengths'][0]
                wrist = elbow + filtered[1]*state['lengths'][1]
                span = state['span'].filter(float(np.clip(entry.get('shoulderSpan', .4), .15, 1)), dt)
                state['points'] = dict(points=[origin.tolist(), elbow.tolist(), wrist.tolist()], shoulderSpan=span)
                state['directions'] = {side+'UpperArm':filtered[0].tolist(),side+'LowerArm':filtered[1].tolist()}
                state['quaternions'] = {side+part:pose[side+part] for part in ('UpperArm','LowerArm') if side+part in pose}
            if state and state['age'] <= self.hold_seconds:
                output['armPoints'][side] = copy.deepcopy(state['points'])
                output['armDirections'].update(copy.deepcopy(state['directions']))
                output.update(state['quaternions'])
            elif state:
                self._arms.pop(side, None)
        return output if pose is not None or output['armPoints'] else None
