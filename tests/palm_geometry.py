"""Run with .venv/Scripts/python.exe tests/palm_geometry.py from project root."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.spatial.transform import Rotation
from src.tracking.hand_landmarker import _compute_palm_orientation
pts=np.zeros((21,3));pts[5]=[.03,-.08,0];pts[17]=[-.03,-.07,0]
base=_compute_palm_orientation(pts);axes=np.diag([1,-1,-1])
for angle in [-170,-100,0,100,170]:
 rotation=Rotation.from_euler('y',angle,degrees=True).as_matrix()
 actual=_compute_palm_orientation(pts@rotation.T)
 for key in ['direction','normal']:
  assert np.allclose(actual[key],axes@rotation@axes@np.array(base[key]))
assert _compute_palm_orientation(np.zeros((21,3))) is None
print('Palm frame full turns and degenerate rejection: PASS')
