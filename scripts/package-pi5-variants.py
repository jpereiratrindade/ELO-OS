#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Package and register Pi 5 client image variants (basic and vision)."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
VARIANTS_DIR = ROOT / 'output/pi5-client-variants'


def get_image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def register_variant(variant: str, source_image: Path, description: str):
    if not source_image.is_file():
        raise FileNotFoundError(f"Imagem de origem não encontrada: {source_image}")
    
    target_dir = VARIANTS_DIR / variant
    target_dir.mkdir(parents=True, exist_ok=True)
    target_image = target_dir / 'sdcard.img'
    
    # Use hardlink if possible to save space and time; fallback to copy.
    if target_image.exists():
        if target_image.samefile(source_image):
            pass
        else:
            target_image.unlink()
            try:
                target_image.hardlink_to(source_image)
            except OSError:
                shutil.copyfile(source_image, target_image)
    else:
        try:
            target_image.hardlink_to(source_image)
        except OSError:
            shutil.copyfile(source_image, target_image)

    sha256 = get_image_sha256(target_image)
    manifest = {
        'variant': variant,
        'sha256': sha256,
        'bytes': target_image.stat().st_size,
        'packaged_at': datetime.now(timezone.utc).isoformat(),
        'source': str(source_image.resolve()),
        'description': description
    }
    manifest_path = target_dir / 'manifest.json'
    import json
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f"[{variant}] Imagem registrada: {target_image} (SHA-256: {sha256})")
    return sha256


def main():
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Detect vision image
    vision_sources = [
        ROOT / 'output/pi5-client-vision/images/sdcard.img',
        ROOT / 'output/pi5-client/images/sdcard.img'
    ]
    vision_found = None
    for src in vision_sources:
        if src.is_file():
            # Check if this output was actually vision
            cfg = src.parents[1] / '.config'
            if cfg.is_file() and 'BR2_PACKAGE_ELO_CLIENT_VISION=y' in cfg.read_text():
                vision_found = src
                break

    if vision_found:
        register_variant('vision', vision_found,
                         'Pi 5 client com suporte a câmera USB e reconhecimento facial opcional')
    else:
        print("[AVISO] Imagem 'vision' ainda não encontrada nos caminhos padrão.", file=sys.stderr)

    # Detect basic image
    basic_sources = [
        ROOT / 'output/pi5-client-basic/images/sdcard.img',
        ROOT / 'output/pi5-client/images/sdcard.img'
    ]
    basic_found = None
    for src in basic_sources:
        if src.is_file():
            cfg = src.parents[1] / '.config'
            if cfg.is_file() and 'BR2_PACKAGE_ELO_CLIENT_VISION=y' not in cfg.read_text():
                basic_found = src
                break

    if basic_found:
        register_variant('basic', basic_found,
                         'Pi 5 client básico sem suporte a câmera nem reconhecimento facial')
    else:
        print("[AVISO] Imagem 'basic' ainda não encontrada nos caminhos padrão.", file=sys.stderr)


if __name__ == '__main__':
    main()
