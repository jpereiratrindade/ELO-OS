#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Explicit local bench target. Requires root and hidden Wi-Fi prompt locally.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VARIANT=
VERIFY_ONLY=0
case "${1:-}" in
    --verify-only) VERIFY_ONLY=1; VARIANT=${2:-}; [[ $# == 2 ]] || exit 2 ;;
    --variant) VARIANT=${2:-}; [[ $# == 2 ]] || exit 2 ;;
    '') ;;
    *) echo 'Uso: install-pi5-microsd.sh [--variant basic|vision | --verify-only basic|vision]' >&2; exit 2 ;;
esac
if [[ -z $VARIANT ]]; then
    [[ -t 0 ]] || { echo 'Terminal necessário para escolher imagem.' >&2; exit 1; }
    echo 'Qual imagem instalar?'
    echo '  1) Básica — sem câmera e sem reconhecimento facial'
    echo '  2) Facial — câmera USB e reconhecimento facial (adesão na interface)'
    read -r -p 'Escolha [1/2]: ' choice
    case "$choice" in 1) VARIANT=basic ;; 2) VARIANT=vision ;; *) echo 'Escolha inválida.' >&2; exit 2 ;; esac
fi
case "$VARIANT" in basic|vision) ;; *) echo 'Variante inválida.' >&2; exit 2 ;; esac
IMAGE_DIR="$ROOT/output/pi5-client-variants/$VARIANT"
IMAGE="$IMAGE_DIR/sdcard.img"
if [[ ! -f "$IMAGE_DIR/manifest.json" || ! -f "$IMAGE" ]]; then
    echo "Imagem da variante '$VARIANT' não encontrada em $IMAGE_DIR." >&2
    echo "Certifique-se de montar/gerar a variante antes da instalação." >&2
    exit 1
fi
EXPECTED_SHA=$(python3 - "$IMAGE_DIR/manifest.json" "$VARIANT" <<'PYMETA'
import json,re,sys
value=json.load(open(sys.argv[1]))
assert value['variant']==sys.argv[2]
assert re.fullmatch('[0-9a-f]{64}',value['sha256'])
print(value['sha256'])
PYMETA
)
python3 "$ROOT/scripts/pi5-preflight.py" --image "$IMAGE" --expected-sha256 "$EXPECTED_SHA"
if [[ $VERIFY_ONLY == 1 ]]; then exit 0; fi
TARGET_ID=/dev/disk/by-id/usb-Generic_STORAGE_DEVICE_000000000819-0:0
OWNER_HOME=/var/home/jpereiratrindade
PRIVATE="$OWNER_HOME/.config/elo-distribution"
PUBLIC_KEY="$OWNER_HOME/.ssh/id_ed25519_labeco.pub"
[[ $EUID == 0 ]] || { echo 'Execute com sudo no terminal local.' >&2; exit 1; }
[[ -t 0 ]] || { echo 'Terminal local necessário para senha Wi-Fi oculta.' >&2; exit 1; }
TARGET=$(readlink -e "$TARGET_ID")
check_target() {
    [[ $(readlink -e "$TARGET_ID") == "$TARGET" && -b "$TARGET" ]]
    [[ $(lsblk -bdnro SIZE "$TARGET") == 7948206080 ]]
    [[ $(lsblk -dnro SERIAL "$TARGET" | xargs) == 000000000819 ]]
    [[ $(lsblk -dnro TYPE "$TARGET" | xargs) == disk ]]
    [[ $(lsblk -dnro TRAN "$TARGET" | xargs) == usb ]]
    [[ $(lsblk -dnro RM "$TARGET" | xargs) == 1 ]]
}
check_image() { [[ $(sha256sum "$IMAGE" | cut -d' ' -f1) == "$EXPECTED_SHA" ]]; }
check_target
check_image
# Capture a valid Wi-Fi configuration before changing any byte on the card.
TEMP=$(mktemp -d /var/tmp/elo-microsd.XXXXXXXX)
MOUNTED=0
cleanup() {
    if [[ $MOUNTED == 1 ]] && ! umount "$TEMP/root"; then
        echo "Montagem ainda ativa em $TEMP/root; diretório preservado para diagnóstico." >&2
        return
    fi
    rm -rf "$TEMP"
}
trap cleanup EXIT
trap 'exit 1' INT TERM HUP
chmod 700 "$TEMP"
python3 - "$ROOT" "$TEMP/wifi.conf" <<'PY'
import getpass, importlib.util, os, sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('setup',root/'scripts/install-terminal.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
password=getpass.getpass('Senha Wi-Fi CPPSUL-VISITANTES (oculta): ')
data=setup.wifi_configuration('BR','CPPSUL-VISITANTES',password)
fd=os.open(sys.argv[2],os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'wb') as stream:stream.write(data)
PY
# Verify all inputs before unmounting or writing.
python3 - "$ROOT" "$PRIVATE" "$OWNER_HOME" "$PUBLIC_KEY" <<'PY'
from pathlib import Path
import sys,ssl,subprocess
sys.path.insert(0,str(Path(sys.argv[1])/'scripts'))
from elo_server import terminal_token
from elo_content import read_active
subprocess.run(['ssh-keygen','-l','-f',sys.argv[4]],check=True,stdout=subprocess.DEVNULL)
private=Path(sys.argv[2]);terminal_token(private/'pi5-terminal.token')
ssl.create_default_context(cafile=str(private/'server.crt'))
content=read_active(Path(sys.argv[3])/'.local/share/elo-client/content')
if content.get('version') not in ('4','5'):raise ValueError('Cache inicial precisa estar no modo automático')
PY
echo "Imagem: $VARIANT · destino: $TARGET · serial: 000000000819"
echo 'Gravação substituirá conteúdo do microSD; backup será salvo antes.'
read -r -p 'Digite GRAVAR para continuar: ' confirmation
[[ $confirmation == GRAVAR ]] || { echo 'Instalação cancelada.'; exit 1; }
mapfile -t PARTITIONS < <(lsblk -lnpo NAME,TYPE "$TARGET" | awk '$2 == "part" {print $1}')
for node in "$TARGET" "${PARTITIONS[@]}"; do
    if swapon --noheadings --raw --show=NAME | grep -Fxq "$node"; then echo 'Destino usado como swap.' >&2; exit 1; fi
    if findmnt -rn -S "$node" >/dev/null; then umount -- "$node"; fi
    ! findmnt -rn -S "$node" >/dev/null
 done
check_target
sfdisk --json "$TARGET" > "$TEMP/old-layout.json"
BACKUP_SIZE=$(python3 - "$TEMP/old-layout.json" <<'PY'
import json,sys
layout=json.load(open(sys.argv[1]))['partitiontable']
if layout['label']!='dos' or layout.get('sectorsize',512)!=512:raise ValueError('Layout inesperado')
parts=layout['partitions']
if not parts:raise ValueError('Partições antigas ausentes')
end=max(p['start']+p['size'] for p in parts)*512
if not 0<end<=7948206080:raise ValueError('Limites inválidos')
print(end)
PY
)
BACKUP_DIR="$ROOT/output/pi5-client/backup"
mkdir -p "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/before-$VARIANT-$(TZ=America/Sao_Paulo date +%Y%m%dT%H%M%S).img"
[[ ! -e "$BACKUP" ]]
echo "Backup do layout anterior: $BACKUP_SIZE bytes"
(umask 077; dd if="$TARGET" of="$BACKUP" bs=4M count="$BACKUP_SIZE" iflag=count_bytes conv=fsync status=progress)
sha256sum "$BACKUP" > "$BACKUP.sha256"
cp "$TEMP/old-layout.json" "$BACKUP.layout.json"
chmod 600 "$BACKUP" "$BACKUP.sha256" "$BACKUP.layout.json"
check_target
check_image
echo "Gravando imagem verificada em $TARGET ($TARGET_ID)"
dd if="$IMAGE" of="$TARGET" bs=4M conv=fsync status=progress
sync
blockdev --flushbufs "$TARGET"
cmp -n "$(stat -c %s "$IMAGE")" "$IMAGE" "$TARGET"
blockdev --rereadpt "$TARGET"
udevadm settle
check_target
mkdir "$TEMP/root"
mount -t ext4 -o rw,nosuid,nodev "${TARGET_ID}-part2" "$TEMP/root"
MOUNTED=1
python3 - "$ROOT" "$TEMP/root" "$PRIVATE" "$OWNER_HOME" "$TEMP/wifi.conf" "$PUBLIC_KEY" <<'PY'
from pathlib import Path
import importlib.util,sys
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('setup',root/'scripts/install-terminal.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
private=Path(sys.argv[3]);home=Path(sys.argv[4])
setup.provision('pi5',Path(sys.argv[2]),'https://10.163.80.176:8443/v1/presentation',
    private/'pi5-terminal.token',private/'server.crt',home/'.local/share/elo-client/content',wifi=Path(sys.argv[5]).read_bytes(),ssh_keys=[Path(sys.argv[6])])
PY
sync
umount "$TEMP/root"
MOUNTED=0
# Reread persisted configuration without journal replay or writes.
mount -t ext4 -o ro,noload,nosuid,nodev "${TARGET_ID}-part2" "$TEMP/root"
MOUNTED=1
python3 - "$ROOT" "$TEMP/root" "$VARIANT" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,str(Path(sys.argv[1])/'scripts'))
from elo_content import read_active
from elo_server import terminal_token
root=Path(sys.argv[2])
assert (root/'etc/elo-terminal/server.url').read_text().strip()=='https://10.163.80.176:8443/v1/presentation'
terminal_token(root/'etc/elo-terminal/terminal.token')
assert read_active(root/'var/lib/elo-client/content')['version'] in ('4','5')
assert (root/'etc/elo-client-variant').read_text().strip()==sys.argv[3]
if sys.argv[3]=='vision':
    assert (root/'etc/elo-terminal/camera.device').read_text().strip()=='/dev/video0'
    assert (root/'usr/share/elo-client/models/face_recognition_sface_2021dec_int8.onnx').is_file()
else:
    assert not (root/'etc/elo-terminal/camera.device').exists()
    assert not list((root/'usr/lib').glob('libopencv*'))
assert (root/'etc/elo-wifi.conf').stat().st_mode & 0o777==0o600
assert 'ssid=43505053554c2d5649534954414e544553' in (root/'etc/elo-wifi.conf').read_text()
assert (root/'etc/init.d/S50elo-client').stat().st_mode & 0o111
assert (root/'root/.ssh/authorized_keys').stat().st_mode & 0o777==0o600
assert (root/'usr/sbin/dropbear').exists()
assert (root/'usr/sbin/chronyd').exists()
assert (root/'usr/bin/elo-network-probe').exists()
print('PASS: configuração, credencial, Wi-Fi e cache automático relidos do microSD')
PY
umount "$TEMP/root"
MOUNTED=0
sync
printf 'PASS_FLASH_AUTOSTART %s %s\n' "$(date --iso-8601=seconds)" "$TARGET_ID" > "$ROOT/output/pi5-client/flash-result.txt"
echo 'PASS: imagem conferida antes do provisionamento; configurações persistidas e verificadas.'
echo 'MicroSD desmontado. Ejete leitor e insira cartão no Pi 5 desligado.'
