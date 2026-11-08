# ELO/OS — aceitação por perfil e artefato

Versão do projeto: **0.1.0**. Estado em 2026-11-08: imagem Pi 5 compilada, console x86_64 verificado em QEMU, console ARM64 `virt` verificado com TCG. Build, boot, teste e homologação são estados distintos.

| Marco/gate | Plataforma e escopo | Estado | Evidência |
| --- | --- | --- | --- |
| P0 | Raspberry Pi OS Lite + UI exploratória | NOT TESTED | Sem ensaio |
| P1-A / Q0 | Estrutura, sintaxe, integração externa e Kconfig dos três perfis | PASS local | `tests/smoke.sh`, `tests/config-smoke.py`; CI executa somente Q0 |
| P1-B | Build e inspeção da imagem Pi 5 ARM64 | PASS — BUILT | [Inventário Pi 5](../evidence/P1-BUILT-PI5-20261108.md) |
| P1-C / Q1X | Boot x86_64, KVM e TCG, snapshot | PASS — VERIFIED_QEMU_X86 | [Evidência x86](../evidence/P1-QEMU-X86-20261108.md), baseline `01574c6` |
| P1-D / Q1A | Boot ARM64 QEMU `virt` em TCG | PASS — BOOTED_QEMU_AARCH64, Q1A | [Evidência ARM64](../evidence/P1-QEMU-AARCH64-20261108.md), fonte `3737a9c`, dois boots e hashes |
| P1-E / Q2 | Boot e console físico Raspberry Pi 5 | NOT TESTED | [Roteiro físico](../../tests/boot/pi5-first-boot.md) |
| P1-F | 30 partidas físicas | NOT TESTED | Registro de ciclos ainda vazio |
| P2 | Qt6/QML, DRM/KMS e periféricos | NOT TESTED | Demo opt-in, fora das imagens P1 |
| P3 | ELO Server/Thin Client, HTTPS, cache e offline | NOT TESTED | Contratos futuros |
| P4 | Rootfs RO, `/data`, energia e recuperação | NOT IMPLEMENTED | ADR-004/005 propostos; hoje rootfs virtual é RW com snapshot no host |
| P5 | Atualização e rollback | NOT IMPLEMENTED | ADR-008 proposto |

## Como atualizar os estados

Cada PASS se aplica ao perfil, hashes dos binários e método descritos no relatório. Uma alteração relevante exige novos testes; um commit apenas documental não invalida os hashes anteriores. Resultados x86_64 não promovem ARM64; resultados ARM64 `virt` não promovem Pi 5 físico.

CI verde em `.github/workflows/structure.yml` significa **Q0**, sem build de kernel nem boot. Os resultados Q1 são ensaios locais com logs e relatórios em `output/`, ignorados no Git. Cada execução remota e seu commit ficam registrados no [workflow Q0](https://github.com/jpereiratrindade/ELO-OS/actions/workflows/structure.yml). O estado de uma execução remota deve ser consultado no commit correspondente, sem transferir o resultado para outra revisão.

A revisão do plano e as diferenças de escopo estão em [implementation-review.md](implementation-review.md). Metas futuras continuam em [ELO-OS-BASES-001](../ELO-OS-BASES-001_v0.1.0.md).
