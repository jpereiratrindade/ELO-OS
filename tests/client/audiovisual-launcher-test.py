#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Exercise launcher defaults without opening a camera or starting a client."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / 'models'
        self.models.mkdir()
        for name in ('face_detection_yunet_2023mar.onnx',
                     'face_recognition_sface_2021dec_int8.onnx'):
            (self.models / name).touch()
        toolbox = self.root / 'toolbox'
        toolbox.write_text('#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
        toolbox.chmod(0o755)

    def launch(self, *args, **env):
        result = subprocess.run(
            [str(ROOT / 'scripts/run-audiovisual-client.sh'), *args],
            env={**os.environ, 'PATH': f'{self.root}:{os.environ["PATH"]}',
                 'ELO_CAMERA': '/dev/video0', 'ELO_VISION_MODEL_DIR': str(self.models), **env},
            check=True, text=True, capture_output=True)
        return json.loads(result.stdout), result.stderr

    def test_default_enables_preview_and_optional_recognition(self):
        args, _ = self.launch()
        self.assertEqual(args[args.index('--camera') + 1], '/dev/video0')
        self.assertIn('--detector-model', args)
        self.assertIn('--recognizer-model', args)
        self.assertIn('--recognition-store', args)
        self.assertNotIn('--attention-playback', args)

    def test_camera_can_be_disabled(self):
        args, _ = self.launch(ELO_CAMERA='off')
        self.assertNotIn('--camera', args)
        self.assertNotIn('--recognizer-model', args)

    def test_explicit_options_win(self):
        supplied = ['--camera=/dev/video7', '--detector-model=/custom/detector',
                    '--recognizer-model=/custom/recognizer', '--recognition-store=/private/visits']
        args, _ = self.launch(*supplied)
        self.assertEqual(args[-len(supplied):], supplied)
        self.assertNotIn('--camera', args)
        self.assertNotIn('--recognition-store', args)

    def test_missing_detector_keeps_playback_available(self):
        (self.models / 'face_detection_yunet_2023mar.onnx').unlink()
        args, warning = self.launch()
        self.assertNotIn('--camera', args)
        self.assertIn('detector ausente', warning)

    def test_detector_only_still_has_preview(self):
        (self.models / 'face_recognition_sface_2021dec_int8.onnx').unlink()
        args, _ = self.launch()
        self.assertIn('--camera', args)
        self.assertNotIn('--recognizer-model', args)
        self.assertNotIn('--recognition-store', args)


if __name__ == '__main__':
    unittest.main()
