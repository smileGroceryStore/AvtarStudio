"""Compare model scheduling on a public fixture; never opens a camera."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json,time,statistics,cv2,numpy as np
from concurrent.futures import ThreadPoolExecutor
from src.tracking.landmarker import FaceLandmarker
from src.tracking.hand_landmarker import HandLandmarker
from src.tracking.pose_landmarker import PoseTracker
image=cv2.imdecode(np.frombuffer(Path('data/test-portrait.jpg').read_bytes(),np.uint8),cv2.IMREAD_COLOR)
image=cv2.cvtColor(cv2.resize(image,(640,480)),cv2.COLOR_BGR2RGB)
trackers=[FaceLandmarker(),HandLandmarker(),PoseTracker()]
rows={}
try:
 with ThreadPoolExecutor(max_workers=3) as pool:
  for names,group in [('face-body',[trackers[0],trackers[2]]),('face-body-hands',trackers)]:
   samples={'sequential':[],'parallel':[]}
   for iteration in range(25):
    for mode in ['sequential','parallel']:
     ts=time.monotonic_ns()//1_000_000;start=time.perf_counter()
     if mode=='sequential':results=[t.detect(image,ts) for t in group]
     else:results=[f.result() for f in [pool.submit(t.detect,image,ts) for t in group]]
     if iteration>=5:samples[mode].append((time.perf_counter()-start)*1000)
   rows[names]={k:{'meanMs':round(statistics.mean(v),2),'p95Ms':round(sorted(v)[int(.95*(len(v)-1))],2)} for k,v in samples.items()}
finally:
 for t in trackers:getattr(t,'_landmarker',t)._detector.close()
Path('test-results').mkdir(exist_ok=True)
Path('test-results/motion-scheduling.json').write_text(json.dumps(rows,indent=2),'utf-8')
print(json.dumps(rows))
