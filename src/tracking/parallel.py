"""Run independent MediaPipe models on the same immutable RGB frame."""
import time
from concurrent.futures import ThreadPoolExecutor, wait


def _detect(tracker, frame, timestamp):
    start = time.perf_counter()
    result = tracker.detect(frame, timestamp)
    return result, (time.perf_counter() - start) * 1000


class ParallelTracking:
    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='landmarker')

    def detect(self, face, hand, pose, frame, timestamp, *, hands=True, body=True):
        selected = {'face': face}
        if hands: selected['hands'] = hand
        if body: selected['pose'] = pose
        futures = {name: self._pool.submit(_detect, tracker, frame, timestamp)
                   for name, tracker in selected.items()}
        # Always finish this frame before a detector is reset or closed, even
        # when another model fails. Never queue multiple frames per detector.
        wait(futures.values())
        results, timings = {}, {}
        for name, future in futures.items():
            results[name], elapsed = future.result()
            timings[name] = round(elapsed, 1)
        return results, timings

    def close(self):
        self._pool.shutdown(wait=True, cancel_futures=True)
