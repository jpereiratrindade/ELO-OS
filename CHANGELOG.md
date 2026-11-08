# Changelog — ELO/OS

## [Unreleased] — desenvolvimento após o scaffold

- 2026-11-08: imagem Pi 5 compilada e inspecionada; boot físico pendente.
- 2026-11-08: boot QEMU x86_64 verificado com KVM e TCG, em dois boots por modo; hashes registrados em `01574c6`.
- Plano documental v0.1.1 incorporado em `ba13e84`; versão do software mantida em `0.1.0`.
- Código próprio licenciado sob GPL-3.0-only por escolha do mantenedor; metadados e COPYING do pacote `elo-client` adicionados.
- Perfil ARM64 `virt` isolado, launcher TCG, overlays comuns e específicos; build e dois boots TCG verificados em 2026-11-08; hashes e escopo registrados em `docs/evidence/P1-QEMU-AARCH64-20261108.md`.
- Teste de boot ampliado com PID 1, console, ext4, DHCP sem IP fixo, estabilidade de getty, snapshots e hashes antes/depois.
- CI Q0 separa estrutura e configuração Kconfig; permissões de leitura e checkout fixado por commit. Não executa boot.
- Preparação do ensaio físico Pi 5, sem gravação de mídia ou alteração de alinhamento.

## [0.1.0] — 2026-11-08
- Documento constitutivo ELO-OS-BASES-001 v0.1.0.
- Árvore `br2-external` para Buildroot; perfil Pi 5 derivado de 2026.08.1.
- Scripts de inicialização do projeto, diagnóstico e inspeção.
- Demonstração Qt/QML como pacote opt-in para etapa P2 (ainda não testada no hardware).
- ADRs e critérios de aceitação. No commit inicial `be651aa`, nenhum build ou boot havia sido validado. Os resultados posteriores constam acima e nas evidências, sem constituir uma nova release.
