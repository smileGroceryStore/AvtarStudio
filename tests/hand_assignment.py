import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace as S
from src.tracking.hand_landmarker import _hand_sides

def point(x,y=.5,visibility=1):return S(x=x,y=y,visibility=visibility)
def detected(xs,labels):return S(hand_landmarks=[[point(x)] for x in xs],handedness=[[S(category_name=label)] for label in labels])
def pose(left,right):
 landmarks=[point(0,visibility=0) for _ in range(33)];landmarks[15]=point(left);landmarks[16]=point(right)
 return S(pose_landmarks=[landmarks])
assert _hand_sides(detected([.2,.8],['Left','Left']),pose(.8,.2))==['right','left']
assert _hand_sides(detected([.2,.8],['Left','Right']),pose(.2,.8))==['left','right']
assert _hand_sides(detected([.8],['Right']),pose(.8,.2))==['left']
assert _hand_sides(detected([.2,.8],['Left','Right']))==['right','left']
print('Anatomical wrist matching, crossed hands, single-hand and unmirrored fallback: PASS')
