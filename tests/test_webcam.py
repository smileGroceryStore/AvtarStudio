import unittest
from unittest.mock import MagicMock, patch
import cv2
from src.capture.webcam import WebcamCapture


class WebcamTests(unittest.TestCase):
    def test_latest_frame_timestamp_stays_with_consumed_frame(self):
        import numpy as np
        camera=WebcamCapture()
        frame=np.zeros((480,640,3),dtype=np.uint8)
        camera._latest,camera._new,camera._captured_at=frame,True,12.5
        got,fresh,stamp=camera.get_latest_packet()
        self.assertIs(got,frame)
        self.assertTrue(fresh)
        self.assertEqual(stamp,12.5)
        self.assertFalse(camera.get_latest()[1])
        self.assertEqual(camera.stats()['width'],640)

    @patch('src.capture.webcam.sys.platform', 'win32')
    def test_retry_backend_and_release_failed_device(self):
        failed, opened = MagicMock(), MagicMock()
        failed.isOpened.return_value = False
        opened.isOpened.return_value = True
        with patch('src.capture.webcam.cv2.VideoCapture', side_effect=[failed, opened]) as factory, patch('src.capture.webcam.threading.Thread'):
            camera = WebcamCapture(index=2)
            camera.start()
            self.assertEqual(factory.call_args_list[0].args, (2, cv2.CAP_DSHOW))
            self.assertEqual(factory.call_args_list[1].args, (2, cv2.CAP_MSMF))
            failed.release.assert_called_once()
            self.assertIs(camera._cap, opened)
            self.assertNotIn(cv2.CAP_PROP_FOURCC, [call.args[0] for call in opened.set.call_args_list])
            camera.stop()
            opened.release.assert_called_once()

    @patch('src.capture.webcam.sys.platform', 'win32')
    def test_all_backends_fail_with_actionable_message(self):
        candidates = [MagicMock() for _ in range(3)]
        for candidate in candidates:
            candidate.isOpened.return_value = False
        with patch('src.capture.webcam.cv2.VideoCapture', side_effect=candidates):
            with self.assertRaisesRegex(RuntimeError, '笔记本摄像头物理开关'):
                WebcamCapture().start()
        for candidate in candidates:
            candidate.release.assert_called_once()


if __name__ == '__main__':
    unittest.main()
