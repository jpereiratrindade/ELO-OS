# Cliente local — P2 experimental

O núcleo não usa Qt, sockets ou armazenamento. A apresentação incorporada permite começar, avançar, voltar e recomeçar. Ela não implementa o protocolo ELO ou conteúdo recebido do servidor. Consulte [ADR-009](../../docs/adr/ADR-009-local-client.md).

**Desktop validado em 2026-11-09:** contratos nativos C++23/Qt, sessão gráfica Fedora, ledger, supervisor Qt real e dois ensaios gráficos por arquitetura (x86_64/KVM e ARM64/TCG) passaram. Núcleo ARM64 aprovado em C++23 e no subconjunto experimental C++26. Consulte as evidências [x86_64](../../docs/evidence/P2-DESKTOP-X86-20261109.md), [ARM64](../../docs/evidence/P2-DESKTOP-AARCH64-20261109.md), o [roteiro da Toolbox](../../docs/tests/desktop-validation.md) e os [contratos locais](../../docs/client/local-contracts.md). Os PASS históricos pertencem à fonte 202ab1d.

## Verificações sem compilar C++/Qt/Buildroot

```bash
./tests/smoke.sh
```

Inclui testes de ativação Python (integridade, falhas, concorrência e marcador atômico) e supervisor shell com processo simulado (queda, travamento, geração, contador parado, backoff e parada). Não é teste da aplicação Qt real.

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
PROFILE=qemu-x86_64-gui QEMU_GUI_NETWORK=user python3 tests/client/qemu-gui-smoke.py

PROFILE=qemu-aarch64-gui JOBS=2 ./scripts/build.sh
PROFILE=qemu-aarch64-gui ./scripts/run-qemu.sh
PROFILE=qemu-aarch64-gui python3 tests/client/qemu-gui-smoke.py
PROFILE=qemu-aarch64-gui QEMU_GUI_NETWORK=user python3 tests/client/qemu-gui-smoke.py
```

Use `QEMU=/caminho/do/emulador` se necessário. Interação usa a janela GTK do QEMU; o console serial permanece no terminal. O smoke usa QMP local, VirtIO GPU, snapshots e display sem janela. O cenário padrão remove a NIC e exige apenas loopback/nenhuma rota; `QEMU_GUI_NETWORK=user` inicia com DHCP e testa queda/reconexão de link, preservando página e conteúdo. Ambos verificam identidade, cliente real, estado, framebuffer, setas/Home, recuperação após SIGKILL e SIGSTOP, desligamento e hashes. A recuperação começa na primeira página, sem persistir navegação. Não usa SSH ou portas TCP.

No Fedora, a bancada gráfica também precisa dos módulos VirtIO GPU/PCI e, para a janela interativa, GTK (`qemu-device-display-virtio-gpu`, `qemu-device-display-virtio-gpu-pci`, `qemu-ui-gtk`). Nesta máquina esses pacotes já estão instalados em 10.2.2-1.fc44. O ARM64 extraído em `.cache/qemu-fedora/root/usr/bin/` procura módulos sob seu prefixo extraído: para usar os módulos instalados da **mesma versão**, informe também `QEMU_MODULE_DIR=/usr/lib64/qemu`. Não misture módulos de versões diferentes. A presença dos dispositivos pode ser conferida com `QEMU_MODULE_DIR=/usr/lib64/qemu "$QEMU" -device virtio-gpu-pci,help`; o relatório registra o diretório efetivamente informado.

Logs, frames PPM e relatórios ficam em `output/<perfil>/gui-*`: `gui-smoke.json` para partida sem NIC e `gui-smoke-network.json` para perda/reconexão. Na Toolbox do desktop, com `PROFILE` já exportado, use `OUTPUT_DIR="$PWD/output/toolbox/$PROFILE"`; informe a mesma variável nos comandos. O teste offline exige ausência de NIC ligada a dispositivo e de rotas IPv4; permite o túnel inativo `sit0` do kernel. Timeout total padrão 240 s (`QEMU_BOOT_TIMEOUT`). Não executar durante build ou outra VM no mesmo diretório. `QEMU_ACCEL=tcg` permite repetir x86 sem KVM; ARM64 usa TCG neste host. O teste gráfico é separado de `tests/boot/qemu-smoke.py`, cujo contrato continua restrito aos perfis de console com DHCP. Os dois cenários passaram em x86_64/KVM e ARM64/TCG.

Os perfis gráficos têm rootfs de 256 MiB, 1 GiB de RAM virtual por padrão, fontes DejaVu Sans, Qt Quick e libdrm. O tamanho provisionado não é memória medida do cliente. A raiz permanece RW e o cliente inicia como root nesta bancada experimental. O supervisor usa PID/geração, frames crescentes, backoff e limite de reinícios; sua integração Qt/imagem foi testada em x86_64/KVM e ARM64/TCG com SIGKILL e SIGSTOP. Estados e hashes testados ficam na [matriz](../../docs/tests/acceptance.md).

## Iteração depois do primeiro build

Para mudanças em C++/QML, comece pelo build/teste nativo acima. Com o build e a VM do perfil encerrados, atualize somente o pacote local e depois regenere a imagem:

```bash
GUI_PROFILE=qemu-x86_64-gui  # ou qemu-aarch64-gui
make -C .cache/buildroot-2026.08.1 O="$PWD/output/$GUI_PROFILE" \
  BR2_EXTERNAL="$PWD" -j4 elo-client-rebuild
PROFILE="$GUI_PROFILE" JOBS=4 ./scripts/build.sh
PROFILE="$GUI_PROFILE" python3 tests/client/qemu-gui-smoke.py
```

`elo-client-rebuild` sincroniza novamente o `SITE_METHOD=local`, recompila/reinstala a aplicação e reutiliza dependências Qt já concluídas. O segundo comando é necessário para gerar um novo `rootfs.ext4`; reconstruir apenas o pacote não atualiza a imagem. Para mudanças nas opções CMake, use `elo-client-reconfigure` no lugar de `elo-client-rebuild`. Alterações de toolchain, configuração Qt ou dependências exigem revisar o procedimento de rebuild do Buildroot separadamente.

Não executar esses comandos enquanto houver outro make no mesmo `O=`. Não apontar o diretório de saída para os perfis de console/Pi 5 históricos. Cada imagem nova tem outro hash e precisa de seu próprio ensaio; o relatório anterior não a valida automaticamente.
