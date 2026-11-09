# Changelog — ELO/OS

## [Unreleased] — desenvolvimento após o scaffold

- 2026-11-09: desktop Silverblue 44 preparado com Toolbox `elo-os`; builds gráficos com 32 jobs e dois cenários por arquitetura aprovados (x86_64/KVM, ARM64/TCG), incluindo tela/teclado, queda/reconexão e SIGKILL/SIGSTOP. Núcleo ARM64 aprovado em C++23 e no subconjunto experimental C++26; cliente nativo também testado na sessão Fedora por QPA xcb. Harness offline corrigido para aceitar `sit0` inativo e verificar NICs ligadas a dispositivos/rotas. Evidências `P2-DESKTOP-{X86,AARCH64}-20261109.md`; Pi 5 físico pendente.
- Diagnóstico do host agora verifica módulos Perl básicos e `Time::Piece` quando a configuração exige OpenSSL, antecipando falha encontrada no build ARM64. Dependências e caminhos da Toolbox documentados.
- T-203/T-205: portas explícitas e adaptadores Linux/Qt para conteúdo, link local, relógio, frames e diagnósticos; conectividade observável e retry de falha recuperável. Contratos nativos C++23/Qt passaram no desktop em 2026-11-09.
- T-209: publicador de fixture local com tamanho/SHA-256, staging, fsync, bundle imutável e marcador atômico; falha após publicação reporta durabilidade incerta. Testes de host incluem corrupção, ENOSPC e leitores concorrentes. Sem `/data` ou protocolo.
- T-210: ledger C++ de teste em memória, chave/payload imutáveis, conflito explícito e reenvio limitado; contrato nativo C++23 passou no desktop em 2026-11-09.
- T-211: supervisor exclusivo dos perfis GUI, saúde por frames crescentes/PID/geração, backoff e orçamento de reinícios. Testes shell com processo simulado e integração Qt real passaram; smokes gráficos x86_64/KVM e ARM64/TCG verificaram queda/reconexão e SIGKILL/SIGSTOP.

- IMPL-002 incorporado sem alterações; núcleo portátil C++23, fixture local validada, eventos tipados e confirmação de apresentação antes de READY_LOCAL. Testes de falha/retry e eventos offline, frontend Qt/QML testado no Fedora e núcleo AArch64 executado em QEMU user; C++26 permanece experimento do subconjunto usado.
- Perfis gráficos QEMU opt-in isolados, Qt Quick por software/LinuxFB/DRM/VirtIO GPU, smoke de framebuffer/entrada sem NIC. Build/boot gráfico e integração da supervisão têm gates próprios; hardware Pi 5 pendente.
- CI acrescenta contratos do núcleo e Qt/Xvfb de host; regressão dos seis boots de console passou após extensão do lançador, sem alterar hashes históricos.
- `fsck.fat -n -v` repetido com código zero e hash FAT preservado; documento registra a saída apresentada pelo operador e a inspeção local.
- Pré-checagem Pi 5 somente leitura: SHA-256 esperado, limites MBR, assinaturas FAT/ext4 e relatório JSON; testes negativos no Q0 e modelo de evidência física. Boot físico continua pendente.
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
