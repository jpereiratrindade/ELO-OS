# ELO/OS — aceitação por perfil e artefato

Versão do projeto: **0.1.0**. Estado em 2026-11-08: imagem Pi 5 compilada, console x86_64 verificado em QEMU, console ARM64 `virt` verificado com TCG. Build, boot, teste e homologação são estados distintos.

| Marco/gate | Plataforma e escopo | Estado | Evidência |
| --- | --- | --- | --- |
| P0 | Raspberry Pi OS Lite + UI exploratória | NOT TESTED | Sem ensaio |
| P1-A / Q0 | Estrutura, sintaxe, integração externa e Kconfig dos cinco perfis | PASS local/CI | `tests/smoke.sh`, `tests/config-smoke.py`; jobs Q0 não executam boot |
| P1-B | Build e inspeção da imagem Pi 5 ARM64 | PASS — BUILT | [Inventário Pi 5](../evidence/P1-BUILT-PI5-20261108.md) |
| P1-C / Q1X | Boot x86_64, KVM e TCG, snapshot | PASS — VERIFIED_QEMU_X86 | [Evidência x86](../evidence/P1-QEMU-X86-20261108.md), baseline `01574c6` |
| P1-D / Q1A | Boot ARM64 QEMU `virt` em TCG | PASS — BOOTED_QEMU_AARCH64, Q1A | [Evidência ARM64](../evidence/P1-QEMU-AARCH64-20261108.md), fonte `3737a9c`, dois boots e hashes |
| P1-E / Q2 | Boot e console físico Raspberry Pi 5 | NOT TESTED | [Roteiro físico](../../tests/boot/pi5-first-boot.md) |
| P1-F | 30 partidas físicas | NOT TESTED | Registro de ciclos ainda vazio |
| P2-C0 | Núcleo C++23 sem Qt, fixture, eventos offline e falhas injetadas | PASS histórico 202ab1d; acréscimos atuais NOT TESTED | [Evidência cliente](../evidence/P2-CLIENT-20261108.md); portas/ledger aguardam recompilação |
| P2-HGUI | Qt/QML no Fedora, apresentação e entrada reais | PASS histórico 202ab1d; acréscimos atuais NOT TESTED | [Evidência cliente](../evidence/P2-CLIENT-20261108.md); conectividade, retry, store e saúde novos aguardam desktop |
| P2-A64 | Núcleo AArch64, C++23 e experimento C++26 | PASS histórico — espaço de usuário; revisão atual NOT TESTED | [Evidência cliente](../evidence/P2-CLIENT-20261108.md); não é GPU/kernel |
| P2-STORE-HOST | Publicação atômica de fixture em diretório descartável | PASS protótipo host | [Evidência local](../evidence/P2-LOCAL-PROTOTYPES-20261108.md); não prova energia nem `/data` |
| P2-SUP-HOST | Supervisor com processo simulado, queda/travamento e backoff | PASS protótipo host | [Evidência local](../evidence/P2-LOCAL-PROTOTYPES-20261108.md); não é aplicação Qt real |
| P2-EVENTMODEL | Ledger C++ em memória e idempotência local | IMPLEMENTED / NOT TESTED | Fonte/testes preparados; sem transporte ou persistência |
| P2-QGUI | Qt Quick, VirtIO GPU, offline/reconexão e recuperação nas imagens | NOT TESTED | Build do laptop interrompido a pedido; [próxima validação no desktop](desktop-validation.md) |
| P2-PI5 | Qt6/QML, DRM/KMS e periféricos físicos | NOT TESTED | Não habilitado na imagem Pi 5 histórica |
| P3 | ELO Server/Thin Client, HTTPS, cache e offline | NOT TESTED | Contratos futuros |
| P4 | Rootfs RO, `/data`, energia e recuperação | NOT IMPLEMENTED | ADR-004/005 propostos; hoje rootfs virtual é RW com snapshot no host |
| P5 | Atualização e rollback | NOT IMPLEMENTED | ADR-008 proposto |

## Como atualizar os estados

Cada PASS se aplica ao perfil, hashes dos binários e método descritos no relatório. Uma alteração relevante exige novos testes; um commit apenas documental não invalida os hashes anteriores. Resultados x86_64 não promovem ARM64; resultados ARM64 `virt` não promovem Pi 5 físico.

CI verde em `.github/workflows/structure.yml` significa **Q0 + contratos do cliente**, sem build de kernel nem boot. Os jobs `client-core`/`client-qt` compilam e testam o cliente no host Ubuntu; Qt usa Xvfb e renderização por software. Os resultados Q1 e os ensaios de imagem gráfica são locais, com logs e relatórios em `output/`, ignorados no Git. Cada execução remota e seu commit ficam registrados no [workflow](https://github.com/jpereiratrindade/ELO-OS/actions/workflows/structure.yml). O estado de uma execução remota deve ser consultado no commit correspondente, sem transferir o resultado para outra revisão.

A revisão do plano e as diferenças de escopo estão em [implementation-review.md](implementation-review.md). Metas futuras continuam em [ELO-OS-BASES-001](../ELO-OS-BASES-001_v0.1.0.md).

Para o avanço do cliente, consulte [IMPL-002](../ELO-OS-IMPL-002_v0.1.0.md) e sua [revisão de escopo](p2-client-review.md). P2-QGUI completo inclui supervisão e falha/reinício; boot gráfico isolado não basta para promover esse gate integral.
