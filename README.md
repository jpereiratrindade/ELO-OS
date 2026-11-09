# ELO/OS — Linux embarcado mínimo para ELO Thin Client

> Faça simples. Depois deixe mais leve. **Sempre pronto. Sempre incompleto.**

**Versão de projeto:** `v0.1.0` · **Estado:** console, GUI e fundação de appliance RO + dados persistentes demonstrados em QEMU x86_64/ARM64; Pi 5 físico adiado · **Hardware:** Raspberry Pi 5, ARM64

O ELO/OS é uma árvore `br2-external` do Buildroot para compor uma distribuição-appliance Linux mínima. **Não é outro kernel**, nem o ELO Server, nem a aplicação ELO existente. A imagem Pi 5 foi compilada; a base x86_64 iniciou em QEMU com KVM e TCG, e a base ARM64 `virt` iniciou com TCG. Há uma apresentação local experimental em C++/Qt Quick, independente da rede. **Não afirma funcionamento gráfico nem confiabilidade homologados no hardware.**

## Decisões iniciais

- Buildroot **2026.08.1**, `raspberrypi5_defconfig` adaptado e fixado em `configs/elo_pi5_defconfig`.
- Linux + BusyBox; sem desktop. Pilha DRM/KMS + Qt 6/EGLFS como **caminho experimental P2**.
- Subconjunto de experiência offline local, com futura sincronização segura pelo ELO Server.
- Nenhuma credencial, segredo, certificado privado ou configuração de dispositivo no Git.

## Árvore

- `docs/`: constituição e ADRs versionados; critérios de aceitação.
- `configs/`: três perfis de console, dois gráficos P2 e dois appliances virtuais isolados.
- `board/elo/common/`: arquivos compartilhados; `board/elo/<perfil>/`: identidade e ajustes por plataforma.
- `package/elo-client/`: núcleo portátil C++ e apresentação Qt/QML **opcional, fora das imagens P1 de console**.
- `scripts/`: build, diagnóstico e inventário da imagem.
- `tests/`: verificações do repositório e roteiros de ensaio.

## Primeiro uso

Requisitos de host: Fedora/Linux com `git`, `make`, `gcc`, `g++`, `python3`, `rsync`, ferramentas comuns para Buildroot (veja [manual oficial](https://buildroot.org/downloads/manual/manual.html)) e Internet para obtenção de fontes e toolchain. O script baixa a release 2026.08.1 do repositório oficial **somente quando invocado**.

```bash
./tests/smoke.sh
./scripts/doctor.sh
./scripts/build.sh
./scripts/inspect-image.sh
```

O build pode baixar fontes e consumir recursos significativos.

O comando `./scripts/build.sh` cria `.cache/buildroot-2026.08.1/`, configura `output/pi5/` com `elo_pi5_defconfig` e chama o Buildroot. A saída esperada é `output/pi5/images/sdcard.img`, caso a versão/base/hardware suporte corretamente todas as dependências. **O script não grava mídia.**

### Primeiro marco: P1, console Linux

A imagem Pi 5 foi gerada e inspecionada; seu boot físico permanece pendente. A primeira imagem **não habilita o cliente Qt**: é uma base Pi 5 com identidade ELO/OS. Validar boot e console antes de adicionar a interface gráfica. Os arquivos `board/elo/pi5/genimage.cfg`, `post-image.sh` e `package/elo-client/` estão preparados para fases futuras e **não devem ser interpretados como integração homologada**.

Ensaios físicos adiados pelo mantenedor em 2026-11-09. Quando retomados, executar `python3 scripts/pi5-preflight.py` no Fedora e seguir o [roteiro de primeiro boot físico](tests/boot/pi5-first-boot.md). A checagem compara a imagem histórica com seu hash registrado e inspeciona partições e assinaturas sem gravar mídia. O [modelo de evidência](tests/boot/pi5-evidence-template.md) prepara o registro do primeiro boot e das 30 partidas.

### Segundo marco: P2, apresentação local

**Validação no desktop em 2026-11-09:** cliente C++23/Qt, adaptadores, ledger e supervisor passaram nos ensaios nativos, incluindo sessão gráfica Fedora. Imagens x86_64/KVM e ARM64/TCG passaram sem NIC e com perda/reconexão, incluindo SIGKILL/SIGSTOP e frames inspecionados. Núcleo ARM64 passou em C++23 e no subconjunto experimental C++26. Builds executados em Toolbox Fedora 44 com 32 jobs. Consulte as evidências [x86_64](docs/evidence/P2-DESKTOP-X86-20261109.md), [ARM64](docs/evidence/P2-DESKTOP-AARCH64-20261109.md) e o [roteiro de compilação e testes](docs/tests/desktop-validation.md). Os PASS históricos preservam seu escopo.

O núcleo C++ começa sem rede e oferece três páginas locais com navegação e reinício. O frontend Qt Quick observa os estados e encaminha teclado/botões. É uma apresentação básica de disponibilidade; ainda não implementa protocolo ELO, conteúdo do servidor, cache, identidade pessoal ou sincronização.

No Fedora com dependências Qt de desenvolvimento disponíveis:

```bash
./scripts/run-client.sh
# Opcional: ./scripts/run-client.sh --fullscreen
```

Build nativo em `build/client-fedora/`, separado do Buildroot. O padrão é C++23 portátil; C++26 é um perfil experimental explícito, avaliado pelo código e testes reais. Consulte o [contrato e comandos de teste do cliente](tests/client/README.md) e a [decisão arquitetural](docs/adr/ADR-009-local-client.md).

Para a bancada gráfica, use `PROFILE=qemu-x86_64-gui` ou `PROFILE=qemu-aarch64-gui` com `scripts/build.sh` e `scripts/run-qemu.sh`. Cada perfil tem saída própria em `output/`, Qt Quick por software, LinuxFB/DRM, VirtIO GPU e apresentação em tela cheia. O teste `tests/client/qemu-gui-smoke.py` cobre partida sem NIC, framebuffer/teclado e recuperação de processo; o cenário `QEMU_GUI_NETWORK=user` verifica perda/reconexão do link. Ambos passaram nas duas arquiteturas. No desktop Toolbox, exporte primeiro o perfil escolhido em `PROFILE` e informe também `OUTPUT_DIR="$PWD/output/toolbox/$PROFILE"`. Essa pilha não comprova EGLFS/V3D na Pi 5; não habilite o cliente no perfil físico antes de configurar e validar sua pilha gráfica.

### Construção integral: appliance virtual

O [plano IMPL-003](docs/ELO-OS-IMPL-003_v0.1.0.md) organiza fundação, identidade/isolamento, conteúdo e eventos duráveis, servidor, atualizações e operação. Contrato e integração de distribuição Thin Client ainda serão definidos; as rotas ilustrativas não representam integração existente.

Novos perfis `qemu-x86_64-appliance` e `qemu-aarch64-appliance` acrescentam raiz somente leitura, temporários em RAM e disco `/data` independente. A interface confirma apresentação antes da rede; disco ausente ou inválido recebe diagnóstico explícito. **I1 passou nas duas arquiteturas:** seis cenários GUI e 16 boots de recuperação, incluindo SIGKILL da VM, staging, ENOSPC e dados inválidos. Consulte [evidência I1](docs/evidence/I1-APPLIANCE-20261109.md), [compilação, disco virtual e testes](docs/tests/appliance-validation.md) e [aceitação](docs/tests/acceptance.md). Conteúdo persistente, fila durável, identidade/TLS e atualização têm etapas próprias; a fixture incorporada permanece apresentação de bancada.

### Desenvolvimento no Fedora com QEMU

O perfil `qemu-x86_64` permite desenvolver boot, serviços, rede e comportamento do sistema sem gravar o microSD. Ele usa os arquivos comuns ELO/OS da base P1, com identidade própria de plataforma. Seu boot foi verificado com KVM e TCG; os artefatos e resultados estão em [aceitação](docs/tests/acceptance.md). É uma compilação x86_64 separada: não executa a `sdcard.img` ARM64 nem valida firmware, drivers, GPU ou desempenho do Raspberry Pi 5.

```bash
# Se QEMU ainda não estiver instalado:
sudo dnf install qemu-system-x86-core

PROFILE=qemu-x86_64 ./scripts/build.sh
PROFILE=qemu-x86_64 ./scripts/inspect-image.sh
./scripts/run-qemu.sh
```

A saída fica em `output/qemu-x86_64/`; a imagem Pi 5 em `output/pi5/` é preservada. O lançador usa KVM quando acessível e emulação por software como alternativa (`QEMU_ACCEL=tcg ./scripts/run-qemu.sh`). A VM tem console no terminal e rede por NAT, sem privilégios de root ou portas expostas no host. Login de bancada: `root`, sem senha. Para sair: `Ctrl-a`, depois `x`; para desligar pelo console: `poweroff`.

O disco usa snapshot temporário: alterações feitas dentro da VM são descartadas ao sair. Para persistir mudanças do sistema, edite o overlay ou os pacotes no repositório e recompile com o mesmo comando. Para configurar pacotes: `PROFILE=qemu-x86_64 ./scripts/menuconfig.sh`. Qt ainda não está habilitado neste perfil; o lançador atual usa apenas console.

As imagens históricas Pi 5/x86 foram preservadas junto às suas configurações antigas. Antes do próximo rebuild desses perfis, reaplique a defconfig para carregar a nova divisão dos overlays, revisando antes qualquer personalização de menuconfig que queira conservar. Exemplo para x86: `make -C .cache/buildroot-2026.08.1 O="$PWD/output/qemu-x86_64" BR2_EXTERNAL="$PWD" elo_qemu_x86_64_defconfig`; para Pi 5 use `O="$PWD/output/pi5"` e `elo_pi5_defconfig`. Isso prepara uma nova construção; não é necessário para executar os binários históricos já testados.

No console, confira `uname -m`, `cat /proc/1/comm`, `cat /etc/elo-os-release`, `mount`, `ip -4 addr show` e `ip route`. A raiz é ext4 **RW** após o init; snapshot no host não é rootfs imutável. `sudo` não está instalado nem é necessário como root; `exit` encerra a sessão e retorna ao login, e `poweroff` desliga a VM. O roteiro está em [tests/boot/README.md](tests/boot/README.md). Continue usando `./scripts/build.sh` para gerar a imagem destinada ao Pi 5.

### ARM64 virtual, separado do Pi 5

O perfil `qemu-aarch64` usa o kernel ARM64 `virt` oficial do Buildroot, PL011 em `ttyAMA0` e disco VirtIO. No Fedora x86_64 ele usa TCG. Não reproduz os periféricos BCM2712 nem executa a `sdcard.img` física.

```bash
# Dependência do host, instalada pelo operador se necessária:
sudo dnf install qemu-system-aarch64-core
PROFILE=qemu-aarch64 ./scripts/doctor.sh
PROFILE=qemu-aarch64 JOBS=4 ./scripts/build.sh
PROFILE=qemu-aarch64 ./scripts/inspect-image.sh
PROFILE=qemu-aarch64 ./scripts/run-qemu.sh
PROFILE=qemu-aarch64 python3 tests/boot/qemu-smoke.py
```

Também é possível informar `QEMU=/caminho/do/binário` nos comandos de diagnóstico, execução e teste. A saída desse perfil fica somente em `output/qemu-aarch64/`. Build e dois boots ARM64 com TCG passaram, com PID 1, console, ext4, DHCP, shutdown, snapshot e hashes verificados; consulte [aceitação](docs/tests/acceptance.md) para o estado de cada artefato.

### Verificações rápidas (Q0) e teste de boot (Q1)

```bash
./tests/smoke.sh
python3 tests/config-smoke.py  # requer a release local Buildroot 2026.08.1
QEMU_ACCEL=kvm python3 tests/boot/qemu-smoke.py
QEMU_ACCEL=tcg python3 tests/boot/qemu-smoke.py
```

Q0 verifica estrutura, sintaxe e Kconfig dos sete perfis, sem compilar ou inicializar imagens. Q1 executa duas sessões reais no perfil escolhido, incluindo PID 1, console, ext4, DHCP, shutdown, estabilidade do login e hashes antes/depois. Logs e relatórios JSON ficam em `output/<perfil>/qemu-smoke-*`; timeout/falha produz código diferente de zero. Os testes devem rodar após o build, sem outra VM ou build no mesmo diretório de saída.

O [plano P1](docs/ELO-OS-IMPL-001_v0.1.1.md), sua [revisão](docs/tests/implementation-review.md) e o [roteiro físico](tests/boot/pi5-first-boot.md) separam os resultados virtuais dos ensaios de hardware. O [IMPL-002](docs/ELO-OS-IMPL-002_v0.1.0.md) foi preservado como plano P2; sua [revisão de escopo](docs/tests/p2-client-review.md) e a [evidência do cliente](docs/evidence/P2-CLIENT-20261108.md) distinguem o que já foi testado das etapas futuras de persistência, servidor e supervisão.

## Repositórios relacionados

- [ELO existente](https://github.com/jpereiratrindade/ELO)
- [Constituição do ELO](https://github.com/jpereiratrindade/ELO/blob/main/docs/constitution/ELO-CONSTITUTION-001.md)
- [Buildroot 2026.08.1](https://buildroot.org/download.html)

## Versão e status

`VERSION` identifica a versão do **projeto**, não a versão de uma imagem executada. As decisões de `docs/adr` têm status explícito; ADR-009 aceita a apresentação local experimental, e as propostas de hardware/produção continuam pendentes. Cada avanço só vira *demonstrado* com evidências e testes.

O código próprio do ELO/OS é licenciado sob **GPL-3.0-only**, conforme decisão do mantenedor em 2026-11-08; o texto integral está em [LICENSE](LICENSE). Kernel, Buildroot, Qt, firmware, toolchains e demais componentes de terceiros preservam suas licenças. O escopo e o inventário inicial estão em [licenças](docs/licenses.md).
