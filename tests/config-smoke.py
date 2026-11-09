#!/usr/bin/env python3
"""Q0: load actual Buildroot Kconfig, without compiling kernels or rootfs."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BR = Path(os.environ.get("BUILDROOT_DIR", ROOT / ".cache/buildroot-2026.08.1")).resolve()
PROFILES = {"pi5-client": ("elo_pi5_client_defconfig", "aarch64", None),
            "pi5": ("elo_pi5_defconfig", "aarch64", None),
            "qemu-x86_64": ("elo_qemu_x86_64_defconfig", "x86_64", "ttyS0"),
            "qemu-aarch64": ("elo_qemu_aarch64_defconfig", "aarch64", "ttyAMA0"),
            "qemu-x86_64-gui": ("elo_qemu_x86_64_gui_defconfig", "x86_64", "ttyS0"),
            "qemu-aarch64-gui": ("elo_qemu_aarch64_gui_defconfig", "aarch64", "ttyAMA0"),
            "qemu-x86_64-appliance": ("elo_qemu_x86_64_appliance_defconfig", "x86_64", "ttyS0"),
            "qemu-aarch64-appliance": ("elo_qemu_aarch64_appliance_defconfig", "aarch64", "ttyAMA0")}


def main():
    if not (BR / "Makefile").is_file():
        raise SystemExit("Defina BUILDROOT_DIR apontando para Buildroot 2026.08.1")
    if "export BR2_VERSION := 2026.08.1\n" not in (BR / "Makefile").read_text():
        raise SystemExit("Release Buildroot incorreta")
    with tempfile.TemporaryDirectory(prefix="elo-config-q0-") as temp:
        for profile, (defconfig, arch, console) in PROFILES.items():
            out = Path(temp) / profile
            proc = subprocess.run(["make", "-C", str(BR), f"O={out}", f"BR2_EXTERNAL={ROOT}", defconfig],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if proc.returncode:
                raise RuntimeError(proc.stdout)
            text = (out / ".config").read_text()
            expected = [f"BR2_{arch}=y", 'BR2_TARGET_GENERIC_HOSTNAME="elo-os"',
                        'BR2_SYSTEM_DHCP="eth0"', "BR2_TARGET_ROOTFS_EXT2_4=y",
                        f'BR2_DEFCONFIG="{ROOT}/configs/{defconfig}"',
                        "BR2_TOOLCHAIN_EXTERNAL_BOOTLIN=y"]
            if console:
                expected += [f'BR2_TARGET_GENERIC_GETTY_PORT="{console}"',
                             'BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="6.18.7"']
                if 'BR2_PACKAGE_HOST_QEMU=y' in text or 'BR2_PACKAGE_RPI_FIRMWARE=y' in text:
                    raise RuntimeError(f"{profile}: QEMU host/firmware RPi indevido")
            for line in expected:
                if line not in text.splitlines():
                    raise RuntimeError(f"{profile}: símbolo perdido pelo Kconfig: {line}")
            appliance = profile.endswith("-appliance")
            gui = profile.endswith("-gui") or appliance or profile == "pi5-client"
            if gui:
                for line in ("BR2_PACKAGE_ELO_CLIENT=y", "BR2_PACKAGE_QT6BASE_LINUXFB=y",
                             "BR2_PACKAGE_QT6DECLARATIVE_QUICK=y",
                             "BR2_PACKAGE_DEJAVU_SANS=y",
                             'BR2_TARGET_ROOTFS_EXT2_SIZE="512M"' if profile == "pi5-client" else 'BR2_TARGET_ROOTFS_EXT2_SIZE="256M"'):
                    if line not in text.splitlines():
                        raise RuntimeError(f"{profile}: requisito gráfico perdido: {line}")
            if gui and profile != "pi5-client" and "BR2_PACKAGE_LIBDRM=y" not in text.splitlines():
                raise RuntimeError(f"{profile}: libdrm ausente")
            if profile == "pi5-client":
                for line in ("BR2_PACKAGE_BRCMFMAC_SDIO_FIRMWARE_RPI_WIFI=y",
                             "BR2_PACKAGE_WIRELESS_REGDB=y", "BR2_PACKAGE_IW=y",
                             "BR2_PACKAGE_WPA_SUPPLICANT_NL80211=y",
                             "BR2_PACKAGE_WPA_SUPPLICANT_CLI=y",
                             "BR2_PACKAGE_WPA_SUPPLICANT_PASSPHRASE=y",
                             "BR2_PACKAGE_RPI_FIRMWARE_INSTALL_DTB_OVERLAYS=y"):
                    if line not in text.splitlines():
                        raise RuntimeError(f"{profile}: requisito fisico perdido: {line}")
            if appliance:
                if '# BR2_TARGET_GENERIC_REMOUNT_ROOTFS_RW is not set' not in text.splitlines():
                    raise RuntimeError(f'{profile}: rootfs deve permanecer somente leitura')
                for symbol, suffix in [('BR2_PACKAGE_BUSYBOX_CONFIG_FRAGMENT_FILES', 'busybox.fragment'),
                                       ('BR2_ROOTFS_POST_BUILD_SCRIPT', 'post-build.sh')]:
                    if not any(line.startswith(symbol + '=') and f'/board/elo/appliance/{suffix}' in line
                               for line in text.splitlines()):
                        raise RuntimeError(f'{profile}: integração appliance ausente: {symbol}')
            forbidden = ["BR2_PACKAGE_OPENSSH=y", "BR2_PACKAGE_DROPBEAR=y", "BR2_PACKAGE_SUDO=y"]
            if gui:
                forbidden += ["BR2_PACKAGE_QT6BASE_NETWORK=y", "BR2_PACKAGE_QT6BASE_OPENGL=y",
                              "BR2_PACKAGE_XORG7=y", "BR2_PACKAGE_WESTON=y"]
            else:
                forbidden += ["BR2_PACKAGE_ELO_CLIENT=y", "BR2_PACKAGE_QT6BASE=y"]
            for line in forbidden:
                if line in text.splitlines():
                    raise RuntimeError(f"{profile}: pacote fora do escopo: {line}")
            overlay = next(line for line in text.splitlines() if line.startswith("BR2_ROOTFS_OVERLAY="))
            if '/board/elo/common/rootfs-overlay' not in overlay or f'/board/elo/{profile}/rootfs-overlay' not in overlay:
                raise RuntimeError(f"{profile}: overlays comum/específico ausentes")
            wrong = "pi5" if profile != "pi5" else "qemu-aarch64"
            env = {**os.environ, "PROFILE": wrong, "OUTPUT_DIR": str(out), "BUILDROOT_DIR": str(BR)}
            rejected = subprocess.run([str(ROOT / "scripts/build.sh")], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if rejected.returncode == 0 or "não pertence ao perfil" not in rejected.stdout:
                raise RuntimeError(f"Reuso entre perfis não foi bloqueado: {rejected.stdout}")
            print(f"PASS Q0-config: {profile}; Kconfig e rejeição de O= incompatível")
    print("Q0-config não executa build nem boot")


if __name__ == "__main__":
    main()
