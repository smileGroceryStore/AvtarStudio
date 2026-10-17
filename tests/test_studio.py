import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from aiohttp.test_utils import TestClient, TestServer
import studio


class FixtureCamera:
    """Run the production worker with a public portrait instead of a real webcam."""
    def __init__(self, **kwargs):
        import cv2
        import numpy as np
        self.image = cv2.imdecode(np.frombuffer(Path('data/test-portrait.jpg').read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    def start(self):
        pass
    def get_latest(self):
        return self.image, True
    def stop(self):
        pass


class StudioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(studio, 'DATA', Path(self.tmp.name))
        self.data_patch.start()
        self.camera_patch = patch('src.capture.webcam.WebcamCapture', FixtureCamera)
        self.camera_patch.start()
        self.studio = studio.Studio()
        self.client = TestClient(TestServer(studio.create_app(self.studio)))
        await self.client.start_server()
    async def asyncTearDown(self):
        await self.client.close()
        self.camera_patch.stop()
        self.data_patch.stop()
        self.tmp.cleanup()
    async def command(self, action, **extra):
        response = await self.client.post('/api/control', json={'action': action, **extra})
        self.assertEqual(response.status, 200, await response.text())
        return await response.json()
    async def wait_for(self, predicate):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = self.studio.snapshot()
            if predicate(state):
                return state
            self.assertNotEqual(state['status'], 'error', state['error'])
            await asyncio.sleep(.1)
        self.fail('Timed out: ' + str(self.studio.snapshot()))

    async def test_worker_start_calibrate_stop_and_shared_output(self):
        self.assertFalse(self.studio.running)
        socket = await self.client.ws_connect('/ws')
        await self.command('start', cameraIndex=0)
        state = await self.wait_for(lambda s: s['status'] == 'tracking')
        self.assertIsNone(self.studio.jpeg, 'Hidden camera preview should not encode frames')
        self.studio.preview_clients = 1
        await self.wait_for(lambda s: self.studio.jpeg is not None)
        self.assertTrue(state['rig']['calibrated'])
        self.assertGreater(state['fps'], 0)
        self.assertEqual(set(state['stageMs']), {'face','hands','pose'})
        self.assertGreaterEqual(state['processingAgeMs'],0)
        self.assertTrue(self.studio.jpeg.startswith(b'\xff\xd8'))
        packet = await socket.receive_json()
        self.assertEqual(packet['type'], 'state')
        await self.command('calibrate')
        await self.wait_for(lambda s: s['status'] == 'calibrating')
        await self.wait_for(lambda s: s['status'] == 'tracking')
        await self.command('stop')
        await self.wait_for(lambda s: s['status'] == 'ready')
        self.assertIsNone(self.studio.jpeg)
        self.assertEqual(self.studio.rig, {})
        await socket.close()

    async def test_blink_test_does_not_open_camera_and_setting_persists(self):
        state=await self.command('test-blink')
        self.assertTrue(state['testBlink'])
        self.assertFalse(state['running'])
        await self.command('settings',settings={'blinkSensitivity':1.4})
        self.assertEqual(studio.Studio().settings['blinkSensitivity'],1.4)
        response=await self.client.post('/api/control',json={'action':'settings','settings':{'blinkSensitivity':5}})
        self.assertEqual(response.status,400)

    async def test_validation_and_persistence(self):
        await self.command('settings', settings={'zoom':1.25,'mirror':True})
        self.assertEqual(studio.Studio().settings['zoom'],1.25)
        for settings in ({'zoom':99}, {'hands':'true'}, {'unknown':1}):
            response=await self.client.post('/api/control',json={'action':'settings','settings':settings})
            self.assertEqual(response.status,400)
        response=await self.client.post('/api/control',json={'action':'start','cameraIndex':-1})
        self.assertEqual(response.status,400)
        response=await self.client.post('/api/avatar',data=b'bad',headers={'X-Avatar-Name':'bad.vrm'})
        self.assertEqual(response.status,400)
        response=await self.client.post('/api/control',json={'action':'stop'},headers={'Origin':'https://example.com'})
        self.assertEqual(response.status,403)


if __name__ == '__main__':
    unittest.main()
