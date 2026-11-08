#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only checks of the Pi 5 SD image before an operator writes media."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys

BASELINE_SHA256 = "a858973142ea7d6560389ee71b14dfbad828bc940f944e7aa6682fef7c4f32fb"
ROOT = Path(__file__).resolve().parents[1]


def inspect(image, expected_sha256):
    """Check identity, MBR bounds and filesystem signatures; never mount the image."""
    if not stat.S_ISREG(image.stat().st_mode):
        raise ValueError("Informe um arquivo de imagem regular, não um dispositivo")
    with image.open("rb") as disk:
        info = os.fstat(disk.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Informe um arquivo de imagem regular, não um dispositivo")
        size = info.st_size
        digest = hashlib.sha256()
        for chunk in iter(lambda: disk.read(1024 * 1024), b""):
            digest.update(chunk)
        actual = digest.hexdigest()
        if actual != expected_sha256:
            raise ValueError(f"SHA-256 divergente: esperado {expected_sha256}, obtido {actual}")
        disk.seek(0)
        mbr = disk.read(512)
        if size % 512 or len(mbr) != 512 or mbr[510:] != b"\x55\xaa":
            raise ValueError("Tamanho ou assinatura MBR inválidos")
        partitions = []
        for index in range(4):
            entry = mbr[446 + 16 * index:462 + 16 * index]
            kind = entry[4]
            start, count = struct.unpack_from("<II", entry, 8)
            if index >= 2:
                if any(entry):
                    raise ValueError("Layout P1 exige somente duas partições primárias")
                continue
            allowed = (0x0B, 0x0C) if index == 0 else (0x83,)
            if kind not in allowed or start < 1 or count < 1 or (start + count) * 512 > size:
                raise ValueError(f"Partição {index + 1}: tipo ou limites inválidos")
            if partitions and start < partitions[-1]["start_lba"] + partitions[-1]["sectors"]:
                raise ValueError("Partições sobrepostas ou fora de ordem")
            partitions.append({"partition": index + 1, "type": f"0x{kind:02x}",
                               "start_lba": start, "sectors": count})
        disk.seek(partitions[0]["start_lba"] * 512)
        fat = disk.read(512)
        fat_kind = ("FAT16" if fat[54:62] == b"FAT16   " else
                    "FAT32" if fat[82:90] == b"FAT32   " else None)
        if (fat[510:] != b"\x55\xaa" or fat_kind is None
                or struct.unpack_from("<H", fat, 11)[0] != 512):
            raise ValueError("Assinatura FAT de boot inválida")
        partitions[0]["filesystem_signature"] = fat_kind
        partitions[1]["filesystem_signature"] = "ext4"
        if partitions[1]["sectors"] * 512 < 2048:
            raise ValueError("Partição raiz pequena demais para o superbloco")
        disk.seek(partitions[1]["start_lba"] * 512 + 1024)
        superblock = disk.read(1024)
        if superblock[56:58] != b"\x53\xef" or not struct.unpack_from("<I", superblock, 96)[0] & 0x40:
            raise ValueError("Assinatura ext4 com extents ausente na raiz")
        after = os.fstat(disk.fileno())
        if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (info.st_size, info.st_mtime_ns, info.st_ctime_ns):
            raise ValueError("Imagem alterada durante a inspeção; pare o build e repita")
    return {"status": "PASS_IMAGE_PREFLIGHT", "physical_boot": "NOT_TESTED",
            "time_utc": datetime.now(timezone.utc).isoformat(), "image": str(image.resolve()),
            "image_source_revision": "be651aa" if actual == BASELINE_SHA256 else "NOT_RECORDED",
            "sha256": actual, "bytes": size, "partitions": partitions,
            "notes": (["MBR declara FAT32, mas assinatura do volume é FAT16; layout preservado para ensaio físico"]
                      if fat_kind == "FAT16" else []),
            "scope": "Hash, limites MBR e assinaturas FAT/ext4; não verifica arquivos, firmware ou boot"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=ROOT / "output/pi5/images/sdcard.img")
    parser.add_argument("--expected-sha256", default=BASELINE_SHA256,
                        help="hash registrado no inventário; padrão: baseline Pi 5 de 2026-11-08")
    args = parser.parse_args()
    expected = args.expected_sha256.lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        parser.error("SHA-256 esperado deve ter 64 dígitos hexadecimais")
    try:
        print(json.dumps(inspect(args.image, expected), indent=2, ensure_ascii=False))
    except (OSError, ValueError, struct.error) as error:
        print(f"FAIL_IMAGE_PREFLIGHT: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
