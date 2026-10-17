"""Calibrated eyelid closure, independent of emotion gain and neutral subtraction."""
import math
import numpy as np


class BlinkTracker:
    def __init__(self): self.reset()

    def reset(self):
        self._samples={side:[] for side in ('Left','Right')}
        self._geometry={side:[] for side in ('Left','Right')}
        self._baseline={'Left':0.,'Right':0.}
        self._open={'Left':None,'Right':None}
        self._closed={'Left':False,'Right':False}
        self._weight={'Left':0.,'Right':0.}
        self.debug={}

    def calibrate(self, bs, openness=None):
        for side in ('Left','Right'):
            self._samples[side].append(float(bs.get('eyeBlink'+side,0)))
            value=(openness or {}).get(side.lower())
            if value is not None and math.isfinite(value) and value>.01:
                self._geometry[side].append(value)

    def finish_calibration(self):
        for side in ('Left','Right'):
            values=self._samples[side]
            self._baseline[side]=float(np.clip(np.percentile(values,20),0,.35)) if values else 0.
            values=self._geometry[side]
            self._open[side]=float(np.percentile(values,80)) if values else None

    def update(self, bs, openness, dt, sensitivity=1.):
        weights={};debug={}
        for side in ('Left','Right'):
            raw=float(np.clip(bs.get('eyeBlink'+side,0),0,1))
            baseline=self._baseline[side]
            score=float(np.clip((raw-baseline)/max(.18,.65-baseline),0,1))
            ratio=(openness or {}).get(side.lower())
            reference=self._open[side]
            if ratio is not None and math.isfinite(ratio) and ratio>.001:
                if raw < baseline+.12 and not self._closed[side]:
                    if reference is None or (reference < .08 and ratio > .12):
                        reference=self._open[side]=ratio
                    elif abs(ratio-reference) < reference*.25:
                        # Follow slow natural changes, not a single wide-eye
                        # spike that would make neutral eyes look closed.
                        reference += (ratio-reference)*min(.03,max(0,dt)*.15)
                        self._open[side]=reference
                if reference and reference>.02:
                    geometric=float(np.clip((.78-ratio/reference)/.48,0,1))
                    score=max(score,geometric)
            score=float(np.clip(score*sensitivity,0,1))
            if self._closed[side]:
                if score<.30:self._closed[side]=False
            elif score>.65:self._closed[side]=True
            target=1. if self._closed[side] else score
            alpha=1-math.exp(-max(.001,dt)*(40 if target>self._weight[side] else 30))
            self._weight[side]+=(target-self._weight[side])*alpha
            weights['blink'+side]=float(np.clip(self._weight[side],0,1))
            debug['raw'+side]=round(raw,3)
            debug['closed'+side]=round(weights['blink'+side],3)
        weights['blink']=max(weights.values())
        self.debug=debug
        return weights
