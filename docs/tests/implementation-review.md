# Revisão de consistência — ELO-OS-IMPL-001 v0.1.1

Data: 2026-11-08. Base local: `ba13e84`, que já incorporava o plano v0.1.1 sobre o diagnóstico `01574c6`. Os dois planos são registros históricos: [v0.1.0](../ELO-OS-IMPL-001_v0.1.0.md) e [v0.1.1](../ELO-OS-IMPL-001_v0.1.1.md). A versão atual do software permanece `0.1.0`; revisão documental não cria release.

## Parecer

O plano é consistente com a constituição e com a base Linux/BusyBox: três perfis isolados, console antes de gráficos, sem serviços extras e promoção de estado apenas por evidência. É correto fechar a documentação x86 antes de atribuir sucesso ao ARM64. As seguintes adaptações evitam aplicar instruções históricas como se fossem fatos atuais:

- A ordem de adicionar o plano v0.1.1 já estava cumprida em `ba13e84`. Preservamos esse arquivo, sem reescrever a auditoria passada; o v0.1.0 foi recuperado de Downloads como histórico, sem executar suas instruções antigas.
- README, changelog e aceitação realmente estavam desatualizados. Foram separados os resultados do scaffold inicial, os builds e os ensaios posteriores.
- Os hashes Pi 5 e x86 foram conferidos diretamente e coincidem com o plano. As observações manuais de memória/PID 1 citadas nele não foram inventadas como parte do teste automatizado antigo; o teste atual coleta suas próprias evidências.
- O texto alterna `qemu-aarch64-virt` e `qemu-aarch64`; a interface implementada é **PROFILE=qemu-aarch64**, máquina QEMU **virt**, saída **output/qemu-aarch64**.
- Os exemplos de comandos “somente após merge” são sequência proposta de integração. A solicitação do mantenedor autoriza implementar e testar localmente antes da publicação; nenhum gate de boot é promovido só porque houve commit.
- A preparação física é entregue como roteiro, não como gravação ou execução fictícia. Nenhuma mídia foi selecionada, gravada ou reparticionada.

## Implementação e limites por tarefa

| Tarefa do plano | Tratamento nesta rodada |
| --- | --- |
| T-001–004 | Perfil ARM64 derivado do oficial, build isolado, launcher TCG e smoke parametrizado; estado executado consta na aceitação/evidência |
| T-005–006 | README/changelog/aceitação e inventários por artefato; hashes dos baselines preservados |
| T-007 | Arquivo comum movido byte a byte para `board/elo/common`; identidade específica em cada perfil. Nenhum serviço novo |
| T-008 | Doctor por perfil, PASS/WARN/FAIL, QEMU selecionável por caminho; não instala pacotes |
| T-009–010 | Auditoria da imagem real e do template upstream; cmdline/getty inventariados. Layout Pi 5 mantido; serial físico não testado |
| T-011 | ADR-004 preservado como proposta. Raiz virtual continua ext4 RW, sem `/data`, A/B ou reforma de armazenamento |
| T-012, T-018 | Q0 estático + configuração real dos três perfis, token read-only e checkout fixado por SHA. Q1 executado localmente; proteção de branch/CI de boot futura não foi alterada remotamente |
| T-013–014 | Qt, ELO real, offline, watchdog e atualização fora desta rodada de base |
| T-015 | Plano atual já versionado; histórico recuperado e fechamento x86 documentado |
| T-016 | Idle antes/depois do login, falha em respawn inesperado/panic, marcadores que o eco não consegue satisfazer, timeout e relatório de falha |
| T-017 | Mantenedor escolheu GPLv3.0 durante esta rodada: código próprio GPL-3.0-only, LICENSE e metadados do pacote atualizados; inventário inicial em `docs/licenses.md`, sem reatribuir licenças de terceiros |

Os requisitos de testes e documentação não adicionam programas ao convidado: o trabalho fica em scripts Python/shell do host. O rootfs permanece Linux + BusyBox e dependências já previstas; não foram ativados Qt, sudo, SSH, watchdog ou novos serviços.

## Diferenças ARM64 em relação ao upstream

A referência é `configs/qemu_aarch64_virt_defconfig` da release Buildroot 2026.08.1, revisão `7fdeadb3b9f12f78e5fccca914d7fef47090ab9a`. O [diff registrado](qemu-aarch64-upstream.diff) mostra todas as diferenças:

- Kernel, versão 6.18.7, configuração `board/qemu/aarch64-virt/linux.config`, patches/hashes e ext4 seguem upstream.
- Toolchain externa Bootlin ARM64 glibc stable, a mesma família já usada no Pi 5; remove-se a seleção de headers para toolchain interna.
- QEMU do host substitui o build de host-QEMU. O post-image upstream apenas produziria um launcher auxiliar; usamos `scripts/run-qemu.sh`, portanto esse hook e seus argumentos foram removidos.
- Hostname ELO, console `ttyAMA0`, overlays comum/específico e rootfs 120 MiB são ajustes do projeto.
- QEMU executa `virt`, Cortex-A53, TCG, VirtIO MMIO e PL011; o kernel/DTB BCM2712 e `sdcard.img` nunca são reaproveitados.

O host não tinha `qemu-system-aarch64`; a validação local usa o RPM oficial Fedora 44 `qemu-system-aarch64-core-10.2.2-1.fc44.x86_64`, com assinatura/digests verificados por `rpm -K`, extraído em `.cache/qemu-fedora/root/`. Nenhum pacote foi instalado no sistema; `QEMU=/caminho/do/binário` é a interface reproduzível para essa opção. Para uso regular, o operador pode instalar o pacote com DNF.

## Critério para avançar

Consultar a [matriz de aceitação](acceptance.md) e os relatórios em `docs/evidence/`. Não recompilar baselines por rotina; testes de regressão usam os arquivos existentes com snapshot e comparação de hashes. Qt e armazenamento persistente exigem etapas próprias após os ensaios da base. A licença do código próprio foi escolhida explicitamente pelo mantenedor. Proteção de branch, inventário jurídico completo da distribuição e homologação de hardware não foram presumidos como concluídos.

## Fechamento da rodada

O gate Q1A passou em dois boots TCG ARM64 sobre a fonte `3737a9c`, com árvore limpa e hashes antes/depois iguais. O [relatório ARM64](../evidence/P1-QEMU-AARCH64-20261108.md) vincula binários, configurações, método e observações. Q0 local e a regressão x86 KVM/TCG passaram; o build Pi 5 foi preservado. A CI histórica `01574c6` foi conferida diretamente no [GitHub Actions](https://github.com/jpereiratrindade/ELO-OS/actions/runs/42511486558): sucesso somente estrutural.

Entrega A fechada no escopo documental e local; entrega B demonstrada em ARM64 virtual; entrega C preparada como roteiro, com execução física ainda NOT TESTED. A arquitetura de armazenamento e os serviços de produção permanecem para etapas próprias.
