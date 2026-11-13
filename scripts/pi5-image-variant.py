#!/usr/bin/env python3
"""Install verified optional vision assets into a Pi client image."""
import hashlib
import os
from pathlib import Path
import shutil
import sys

MODELS = {
    'face_detection_yunet_2023mar.onnx': '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',
    'face_recognition_sface_2021dec_int8.onnx': '2b0e941e6f16cc048c20aee0c8e31f569118f65d702914540f7bfdc14048d78a',
}


def prepare(config, target, models):
    vision = 'BR2_PACKAGE_ELO_CLIENT_VISION=y' in config.read_text().splitlines()
    directory = target / 'usr/share/elo-client/models'
    camera = target / 'etc/elo-terminal/camera.device'
    if vision:
        # Validate every input before changing the target.
        for name, digest in MODELS.items():
            if hashlib.sha256((models / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Modelo inválido: {name}')
        directory.mkdir(parents=True, exist_ok=True)
        for name in MODELS:
            shutil.copyfile(models / name, directory / name)
            (directory / name).chmod(0o644)
        camera.parent.mkdir(parents=True, exist_ok=True)
        camera.write_text('/dev/video0\n')
        camera.chmod(0o600)
    else:
        if directory.exists():
            shutil.rmtree(directory)
        camera.unlink(missing_ok=True)
        # Buildroot cannot remove obsolete packages from a reused target safely.
        if list((target / 'usr/lib').glob('libopencv*')):
            raise ValueError('Target básico contém OpenCV antigo; use um OUTPUT_DIR limpo')
    (target / 'etc/elo-client-variant').write_text('vision\n' if vision else 'basic\n')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    prepare(Path(os.environ['BR2_CONFIG']), Path(sys.argv[1]),
            Path(os.environ.get('ELO_VISION_MODELS_DIR', root.parent / 'elo/build/models')))
