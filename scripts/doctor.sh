#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-pi5}
source "$ROOT/scripts/profiles.sh"
failed=0
printf 'ELO/OS :: Diagnóstico · PROFILE=%s · ARCH=%s\nBR2_EXTERNAL=%s\nO=%s\n' "$PROFILE" "$ARCH" "$ROOT" "$OUT_DIR"
for tool in git make gcc g++ python3 rsync tar awk sed xz gzip base64 bzip2 patch perl cpio unzip file; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf 'PASS: %s\n' "$tool"
  else
    printf 'FAIL: %s ausente\n' "$tool"
    failed=1
  fi
done
if command -v perl >/dev/null 2>&1; then
  perl_modules=(Data::Dumper English ExtUtils::MakeMaker Thread::Queue FindBin IPC::Cmd)
  selected_config="$OUT_DIR/.config"
  [[ -f "$selected_config" ]] || selected_config="$ROOT/configs/$DEFCONFIG"
  if grep -Eq '^BR2_(LINUX_KERNEL_NEEDS_HOST_OPENSSL|PACKAGE_(HOST_)?(LIB)?OPENSSL)=y$' "$selected_config"; then
    perl_modules+=(Time::Piece)
  fi
  for module in "${perl_modules[@]}"; do
    if perl -e "require $module" >/dev/null 2>&1; then
      printf 'PASS: módulo Perl %s\n' "$module"
    else
      printf 'FAIL: módulo Perl %s ausente; dependências em docs/tests/desktop-validation.md\n' "$module"
      failed=1
    fi
  done
fi
if [[ -f "$BR_DIR/Makefile" ]]; then
  if grep -qx "export BR2_VERSION := $VERSION" "$BR_DIR/Makefile"; then
    echo "PASS: Buildroot $VERSION em $BR_DIR"
  else
    echo "FAIL: Buildroot em $BR_DIR não é $VERSION"
    failed=1
  fi
else
  echo "WARN: Buildroot ainda não baixado em $BR_DIR; build.sh baixa a release fixa"
fi
if [[ -f "$OUT_DIR/.config" ]]; then
  if check_profile_config; then echo 'PASS: configuração pertence ao perfil'; else failed=1; fi
else
  echo 'WARN: perfil ainda não configurado'
fi
if [[ "$PROFILE" == qemu-* ]]; then
  if [[ "$ARCH" == aarch64 ]]; then
    binary=${QEMU:-qemu-system-aarch64}; package=qemu-system-aarch64-core
  else
    binary=${QEMU:-qemu-system-x86_64}; package=qemu-system-x86-core
  fi
  if command -v "$binary" >/dev/null 2>&1; then
    "$binary" --version | head -1
    echo 'PASS: emulador disponível'
  else
    echo "FAIL: $binary ausente; Fedora: sudo dnf install $package (ou informe QEMU=/caminho/do/binário)"
    failed=1
  fi
  if [[ "$ARCH" == x86_64 && $(uname -m) == x86_64 && -r /dev/kvm && -w /dev/kvm ]]; then
    echo 'PASS: KVM acessível; TCG também pode ser selecionado'
  else
    echo 'WARN: este perfil usa emulação por software TCG neste host'
  fi
fi
for artifact in "${artifacts[@]}"; do
  if [[ -f "$OUT_DIR/images/$artifact" ]]; then
    echo "PASS: artefato presente: $artifact (presença não comprova boot)"
  else
    echo "WARN: artefato ainda ausente: $artifact"
  fi
done
exit "$failed"
