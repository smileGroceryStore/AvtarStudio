"""Fetch tracker weights and an optional sample avatar. No webcam access."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request
import shutil

ROOT = Path(__file__).resolve().parent
FILES = {
    'assets/models/face_landmarker.task': 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
    'assets/models/hand_landmarker.task': 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
    'assets/models/pose_landmarker_full.task': 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task',
    'assets/avatars/sample.vrm': 'https://raw.githubusercontent.com/hinzka/52blendshapes-for-VRoid-face/main/VRoid_V110_Male_v1.1.3.vrm',
}
for model in ('AvatarSample_A', 'AvatarSample_B', 'AvatarSample_C'):
    FILES[f'frontend/public/assets/models/{model}.vrm'] = f'https://raw.githubusercontent.com/madjin/vrm-samples/master/vroid/stable/{model}.vrm'
for model in ('Darkness_Shibu', 'Sakurada_Fumiriya', 'Victoria_Rubin'):
    FILES[f'frontend/public/assets/models/{model}.vrm'] = f'https://raw.githubusercontent.com/madjin/vrm-samples/master/vroid/beta/{model}.vrm'
FILES['frontend/public/assets/models/UnityChan.vrm'] = 'https://raw.githubusercontent.com/xelloss120/CharWebCam/master/DefaultModel/unitychan.vrm'

def fetch(item):
    name, url = item
    target = ROOT / name
    if target.exists() and target.stat().st_size > 1000:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.download')
    print('Downloading', name, flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
    temporary.replace(target)
    print('Ready:', name, flush=True)

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch, FILES.items()))
    for source, target in [('frontend/public/assets/models/AvatarSample_A.vrm', 'assets/avatars/AvatarSample_A.vrm'),
                           ('assets/avatars/sample.vrm', 'frontend/public/assets/models/sample.vrm')]:
        destination = ROOT / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(ROOT / source, destination)
