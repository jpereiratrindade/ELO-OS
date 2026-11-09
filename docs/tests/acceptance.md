# ELO/OS — aceitação por perfil e artefato

Versão do projeto: **0.1.0**. Estado em 2026-11-09: imagem Pi 5 compilada, consoles e apresentação gráfica x86_64/ARM64 verificados em QEMU. Novos appliances passaram com raiz RO, `/data` independente e recuperação virtual. Build, boot, teste e homologação são estados distintos.

| Marco/gate | Plataforma e escopo | Estado | Evidência |
| --- | --- | --- | --- |
| P0 | Raspberry Pi OS Lite + UI exploratória | NOT TESTED | Sem ensaio |
| P1-A / Q0 | Estrutura, sintaxe, integração externa e Kconfig dos sete perfis | PASS local; CI anterior cobre cinco | `tests/smoke.sh`, `tests/config-smoke.py`; jobs Q0 não executam boot |
| P1-B | Build e inspeção da imagem Pi 5 ARM64 | PASS — BUILT | [Inventário Pi 5](../evidence/P1-BUILT-PI5-20261108.md) |
| P1-C / Q1X | Boot x86_64, KVM e TCG, snapshot | PASS — VERIFIED_QEMU_X86 | [Evidência x86](../evidence/P1-QEMU-X86-20261108.md), baseline `01574c6` |
| P1-D / Q1A | Boot ARM64 QEMU `virt` em TCG | PASS — BOOTED_QEMU_AARCH64, Q1A | [Evidência ARM64](../evidence/P1-QEMU-AARCH64-20261108.md), fonte `3737a9c`, dois boots e hashes |
| P1-E / Q2 | Boot e console físico Raspberry Pi 5 | DEFERRED — NOT TESTED | Adiado pelo mantenedor em 2026-11-09; [roteiro físico](../../tests/boot/pi5-first-boot.md) |
| P1-F | 30 partidas físicas | DEFERRED — NOT TESTED | Registro de ciclos ainda vazio |
| P2-C0 | Núcleo C++23 sem dependência Qt, fixture, eventos offline e falhas injetadas | PASS desktop, fonte c456f0b | [Evidência desktop](../evidence/P2-DESKTOP-X86-20261109.md); portas e ledger exercitados pelo contrato do núcleo |
| P2-HGUI | Qt/QML no Fedora, apresentação e entrada reais | PASS desktop offscreen e sessão gráfica xcb, fonte c456f0b | [Evidência desktop](../evidence/P2-DESKTOP-X86-20261109.md); conectividade, retry, store, saúde e captura da sessão GNOME/Wayland via Xwayland |
| P2-A64 | Núcleo AArch64, C++23 e experimento C++26 | PASS espaço de usuário, fonte c456f0b | [Evidência ARM64 desktop](../evidence/P2-DESKTOP-AARCH64-20261109.md); contratos e três páginas nos dois padrões; C++26 apenas no subconjunto usado |
| P2-STORE-HOST | Publicação atômica de fixture em diretório descartável | PASS protótipo host | [Evidência local](../evidence/P2-LOCAL-PROTOTYPES-20261108.md); não prova energia nem `/data` |
| P2-SUP-HOST | Supervisor, queda/travamento e backoff | PASS processo simulado e Qt real offscreen | [Evidência desktop](../evidence/P2-DESKTOP-X86-20261109.md); política reduzida no host, política padrão nas imagens x86/ARM64 |
| P2-EVENTMODEL | Ledger C++ em memória e idempotência local | PASS nativo C++23, fonte c456f0b | [Evidência desktop](../evidence/P2-DESKTOP-X86-20261109.md); sem transporte ou persistência |
| P2-QGUI | Qt Quick, VirtIO GPU, offline/reconexão e recuperação nas imagens | PASS virtual — x86_64/KVM e ARM64/TCG | [x86_64](../evidence/P2-DESKTOP-X86-20261109.md), [ARM64](../evidence/P2-DESKTOP-AARCH64-20261109.md); dois cenários por arquitetura, frames, SIGKILL/SIGSTOP e hashes |
| P2-PI5 | Qt6/QML, DRM/KMS e periféricos físicos | NOT TESTED | Não habilitado na imagem Pi 5 histórica |
| P3 | ELO Server/Thin Client, HTTPS, cache e offline | NOT IMPLEMENTED | Contrato de distribuição Thin Client ainda não identificado/definido; [plano integral](../ELO-OS-IMPL-003_v0.1.0.md) |
| I1 / P4-V | Rootfs RO, `/data` independente e recuperação virtual | PASS virtual — x86_64/KVM e ARM64/TCG | [Evidência I1](../evidence/I1-APPLIANCE-20261109.md); seis cenários GUI, 16 boots de recuperação, ENOSPC e recusa de dados inválidos; hashes preservados |
| P4 | Energia física e recuperação de produção | NOT TESTED | ADR-004/005; perfis de console e gráficos P2 preservam raiz RW com snapshot no host |
| P5 | Atualização e rollback | NOT IMPLEMENTED | ADR-008 proposto |

## Como atualizar os estados

Cada PASS se aplica ao perfil, hashes dos binários e método descritos no relatório. Uma alteração relevante exige novos testes; um commit apenas documental não invalida os hashes anteriores. Resultados x86_64 não promovem ARM64; resultados ARM64 `virt` não promovem Pi 5 físico.

CI verde em `.github/workflows/structure.yml` significa **Q0 + contratos do cliente**, sem build de kernel nem boot. Os jobs `client-core`/`client-qt` compilam e testam o cliente no host Ubuntu; Qt usa Xvfb e renderização por software. Os resultados Q1 e os ensaios de imagem gráfica são locais, com logs e relatórios em `output/`, ignorados no Git. Cada execução remota e seu commit ficam registrados no [workflow](https://github.com/jpereiratrindade/ELO-OS/actions/workflows/structure.yml). O estado de uma execução remota deve ser consultado no commit correspondente, sem transferir o resultado para outra revisão.

A revisão do plano e as diferenças de escopo estão em [implementation-review.md](implementation-review.md). Metas futuras continuam em [ELO-OS-BASES-001](../ELO-OS-BASES-001_v0.1.0.md).

Para o avanço do cliente, consulte [IMPL-002](../ELO-OS-IMPL-002_v0.1.0.md) e sua [revisão de escopo](p2-client-review.md). P2-QGUI completo inclui supervisão e falha/reinício; boot gráfico isolado não basta para promover esse gate integral.
