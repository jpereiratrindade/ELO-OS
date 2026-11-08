# Cliente local — P2 experimental

O núcleo não usa Qt, sockets ou armazenamento. A apresentação incorporada permite começar, avançar, voltar e recomeçar. Ela não implementa o protocolo ELO ou conteúdo recebido do servidor. Consulte [ADR-009](../../docs/adr/ADR-009-local-client.md).

## Fedora

Com CMake >= 3.25, Ninja, GCC e Qt 6 Core/Gui/Quick/Qml/Test de desenvolvimento disponíveis:

```bash
./scripts/run-client.sh
# Tela cheia opcional:
./scripts/run-client.sh --fullscreen
```

A compilação nativa fica em `build/client-fedora/`; não modifica imagens Buildroot. O frontend usa renderização por software por padrão (`QT_QUICK_BACKEND` pode ser informado explicitamente). Setas direita/esquerda navegam; Home recomeça. Os botões respondem ao mouse, Tab, Espaço e Enter. Fechar a janela encerra o processo.

## Contrato portátil, sem Qt

O padrão é C++23 portátil. `-DELO_CXX_STANDARD=26` seleciona um experimento sem downgrade silencioso: suporte é declarado somente para os recursos usados e testados, não para todo o padrão. A CI Ubuntu usa o perfil 23.

```bash
cmake -S package/elo-client/src -B build/client-core -DELO_BUILD_GUI=OFF -DELO_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build/client-core --parallel 2
ctest --test-dir build/client-core --output-on-failure
build/client-core/elo-client-core
```

Verifica BOOTING/READY_LOCAL, fixture válida e confirmação de apresentação como pré-condições, rejeição de fixture ausente/inválida/incompatível e timeout, falha fatal, retry explícito, navegação e limites, reset, perda/reconexão de rede sem perder conteúdo e isolamento entre instâncias. O catálogo de teste é injetado; o núcleo não faz I/O. O executável de console percorre as três páginas e termina; não é daemon nem substituto da UI.

## Interface Qt em tela virtual do host

```bash
cmake -S package/elo-client/src -B build/client-fedora -G Ninja -DELO_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build/client-fedora --parallel 2
mkdir -p output/client-fedora
QT_QUICK_BACKEND=software ELO_SCREENSHOT="$PWD/output/client-fedora/local-presentation.png" \
  xvfb-run -a -s '-screen 0 1280x800x24' ctest --test-dir build/client-fedora --output-on-failure
```

O teste Qt carrega o QML real, envia teclado e mouse, verifica atualização de texto e obtém um frame renderizado. A ativação da janela é explícita para que os eventos de teclado tenham foco na tela de teste. Xvfb testa a interface no Fedora; não é boot de imagem ELO/OS.

## Imagens gráficas QEMU separadas

```bash
PROFILE=qemu-x86_64-gui JOBS=2 ./scripts/build.sh
PROFILE=qemu-x86_64-gui ./scripts/run-qemu.sh
PROFILE=qemu-x86_64-gui python3 tests/client/qemu-gui-smoke.py

PROFILE=qemu-aarch64-gui JOBS=2 ./scripts/build.sh
PROFILE=qemu-aarch64-gui ./scripts/run-qemu.sh
PROFILE=qemu-aarch64-gui python3 tests/client/qemu-gui-smoke.py
```

Use `QEMU=/caminho/do/emulador` se necessário. Interação usa a janela GTK do QEMU; o console serial permanece no terminal. O smoke automatizado usa `QEMU_DISPLAY=none` e `QEMU_NETWORK=off`, QMP local em socket temporário, VirtIO GPU e snapshots. Verifica identidade/arquitetura, apenas loopback e nenhuma rota, processo real do cliente, estado local, conteúdo do núcleo e captura do framebuffer. Envia seta direita e Home pelo teclado virtual, exige mudança da tela e restauração da tela inicial, desliga e confere hashes dos artefatos. Não usa SSH ou portas TCP.

No Fedora, a bancada gráfica também precisa dos módulos VirtIO GPU/PCI e, para a janela interativa, GTK (`qemu-device-display-virtio-gpu`, `qemu-device-display-virtio-gpu-pci`, `qemu-ui-gtk`). Nesta máquina esses pacotes já estão instalados em 10.2.2-1.fc44. O ARM64 extraído em `.cache/qemu-fedora/root/usr/bin/` procura módulos sob seu prefixo extraído: para usar os módulos instalados da **mesma versão**, informe também `QEMU_MODULE_DIR=/usr/lib64/qemu`. Não misture módulos de versões diferentes. A presença dos dispositivos pode ser conferida com `QEMU_MODULE_DIR=/usr/lib64/qemu "$QEMU" -device virtio-gpu-pci,help`; o relatório registra o diretório efetivamente informado.

Logs, três frames PPM e relatório JSON ficam em `output/<perfil>/gui-*`; timeout por boot padrão de 240 s (`QEMU_BOOT_TIMEOUT`). Não executar durante build ou outra VM no mesmo diretório. `QEMU_ACCEL=tcg` permite repetir x86 sem KVM; ARM64 usa TCG neste host. O teste gráfico é separado de `tests/boot/qemu-smoke.py`, cujo contrato continua restrito aos perfis de console com DHCP.

Os perfis gráficos têm rootfs de 256 MiB, 1 GiB de RAM virtual por padrão, fontes DejaVu Sans, Qt Quick e libdrm. O tamanho provisionado não é memória medida do cliente. A raiz permanece RW e o cliente inicia como root apenas nesta bancada experimental. Não há supervisão automática após falha. Estados e hashes testados ficam na [matriz](../../docs/tests/acceptance.md).
