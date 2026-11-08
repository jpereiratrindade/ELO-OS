---
document_id: ELO-OS-IMPL-001
title: "ELO/OS — Plano de execução Caveman Full: fechamento do P1 x86_64, validação ARM64 e preparação física"
version: 0.1.1
status: action-required
created: 2026-11-08
revised: 2026-11-08
system: ELO/OS
repository: https://github.com/jpereiratrindade/ELO-OS
repository_branch_baseline: main
repository_commit_baseline: 01574c60d06d82070f82d0ef969bef020c694c7e
buildroot_version: 2026.08.1
host_target: "Fedora 44 / x86_64"
virtual_target_validated: "QEMU system/x86_64 - KVM e TCG"
virtual_target_next: "QEMU system/aarch64 -machine virt (TCG)"
physical_target: "Raspberry Pi 5 / BCM2712 / aarch64"
software_version: 0.1.0
related_documents:
  - ELO-OS-BASES-001_v0.1.0.md
  - ELO-OS-IMPL-001_v0.1.0.md
  - ELO-CONSTITUTION-001
principles:
  - "Faça simples. Depois deixe mais leve."
  - "Sempre pronto. Sempre incompleto."
---

# ELO/OS — Plano de execução **CAVEMAN FULL**

**Documento:** `ELO-OS-IMPL-001` · **Revisão:** `v0.1.1`  
**Estado:** `ACTION REQUIRED` — ordem para a equipe, **não** declaração de conclusão integral.  
**Base auditada:** `main`, commit `01574c6` (08/11/2026).  
**Versão do software:** `0.1.0` — a revisão deste MD **não é** uma nova release do sistema.  
**Instalação de trabalho:** `~/dev/cpp/elo-os`, Fedora 44.  
**Escopo:** concluir a governança do primeiro boot x86_64, executar a trilha ARM64 virtual e preparar a validação física da Pi 5 sem quebrar os artefatos já demonstrados.

> **FAÇA SIMPLES. DEPOIS DEIXE MAIS LEVE.**  
> **SEMPRE PRONTO. SEMPRE INCOMPLETO.**  
> **REGRA CAVEMAN:** FAZER → MEDIR → PROVAR → REGISTRAR.  
> **REGRA EPISTÊMICA:** BUILD ≠ BOOT ≠ TESTE ≠ HOMOLOGAÇÃO.  
> **REGRA OPERACIONAL:** NÃO APAGAR O QUE JÁ FUNCIONA PARA INVESTIGAR O QUE AINDA NÃO FUNCIONA.

---

## 0. ORDEM DIRETA PARA A EQUIPE — LEITURA DE 60 SEGUNDOS

### O que foi alcançado

1. **Raspberry Pi 5 ARM64:** `sdcard.img` compilada e inspecionada. **Boot físico pendente.**
2. **Fedora 44 / QEMU x86_64:** Linux 6.18.7 inicializou via KVM; shell, PID 1, ext4, DHCP e desligamento foram observados diretamente.
3. **Teste automatizado QEMU:** o relatório versionado registra **dois boots com KVM e dois com TCG**, incluindo snapshot descartável. Não converter esse resultado em validação ARM64.
4. **Git:** `01574c6` registra as evidências; a automação de GitHub passou **apenas nas verificações estruturais**.
5. **Problema documental:** `README.md`, `CHANGELOG.md` e `docs/tests/acceptance.md` ainda apresentam informações de fase *scaffold* e não refletem integralmente os resultados.

### O que fazer agora

1. **FECHAR** o marco `P1-QEMU-X86`: consolidar relatório, comandos, hashes, logs, limites, erros benignos e estado em `docs/tests/acceptance.md`.
2. **CORRIGIR** README/CHANGELOG sem atribuir ao sistema capacidades não testadas.
3. **INCORPORAR** este documento versionado em `docs/`, preservando o `v0.1.0` como histórico, ou estabelecer política explícita de supersessão.
4. **FORTALECER** as verificações Q0; não anunciar CI verde como boot aprovado.
5. **CONSTRUIR** o perfil independente `qemu-aarch64-virt` em `output/qemu-aarch64`, com kernel da máquina `virt`, sem reaproveitar `output/pi5`.
6. **PROVAR** boot ARM64, PID 1, console `ttyAMA0`, rootfs, identidade, rede e snapshot em QEMU TCG no Fedora 44.
7. **PREPARAR** o primeiro teste físico do Pi 5, em trilha separada.
8. **NÃO** habilitar Qt, persistência A/B, SSH exposto, watchdog ou novos serviços durante o fechamento dos testes de base.

**Definição de sucesso da próxima rodada:** documentação coerente + perfil virtual ARM64 reproduzível e inicializado + preservação comprovada dos resultados Pi 5 e QEMU x86_64. **Não** significa produto pronto para uso contínuo.

---

## 1. FATOS, PROVAS E LIMITES — NÃO REINTERPRETAR

### 1.1. Linha do tempo auditável

| Data | Commit/artefato | Evidência | Estado permitido |
|---|---|---|---|
| 08/11/2026 | `be651aa` | Scaffold inicial, 41 arquivos, smoke estrutural | `SCAFFOLDED` |
| 08/11/2026 | `output/pi5/images/sdcard.img` | Buildroot terminou; `fdisk`, `file`, SHA-256 e configuração inspecionados | `BUILT_PI5` |
| 08/11/2026 | `a7cf2d9` | Perfil QEMU x86_64, launcher, testes e diretórios isolados | `SCAFFOLDED_QEMU_X86` |
| 08/11/2026 | Execução manual QEMU | Kernel 6.18.7, KVM, ext4, PID 1, DHCP, login, inspeção e `poweroff` | `BOOTED_QEMU_X86`, itens funcionais observados |
| 08/11/2026 | `01574c6` | Registro de dois boots KVM e dois TCG, hashes e snapshot | `VERIFIED_QEMU_X86` dentro do escopo dos testes descritos |

**Proveniência:** os eventos de terminal foram apresentados pelo operador; a execução automatizada KVM/TCG e seus hashes constam em `tests/boot/README.md` na revisão `01574c6`. O revisor deste MD não executou esses testes no host; seu estado depende da evidência local registrada e deverá ser reavaliado se o código/imagens mudarem.

### 1.2. Raspberry Pi 5 — compilado, não inicializado fisicamente

| Item | Evidência observada | Limite |
|---|---|---|
| Buildroot | Release `2026.08.1` | Configuração Pi 5 própria |
| Imagem | `sdcard.img`, 159.384.064 bytes (~152 MiB) | Imagem de disco, **não** consumo RAM |
| Boot FAT | 32 MiB, LBA 1–65536 | Alinhamento incomum a auditar |
| Rootfs | 120 MiB, LBA 65537–311296 | Não existe `/data` independente |
| Kernel | `Image`, ~24 MiB, ARM64 | Não houve prova de execução física |
| Sistema raiz | ext4 (`rootfs.ext4` é symlink para `rootfs.ext2`) | Nome do arquivo não altera formato real |
| PID 1 esperado | `/sbin/init -> ../bin/busybox` | Link presente não prova boot |
| Getty | `/dev/console` e `tty1` em `inittab` | Acesso serial físico ainda não verificado |
| Cmdline | `root=/dev/mmcblk0p2 rootwait console=tty1 console=ttyAMA10,115200` | Alvo físico microSD; não reutilizar em QEMU virt |

**SHA-256 da `sdcard.img` observada:**

```text
a858973142ea7d6560389ee71b14dfbad828bc940f944e7aa6682fef7c4f32fb
```

**Regra:** esse hash identifica **aquela construção local**, não todas as imagens `v0.1.0` possíveis.

### 1.3. QEMU x86_64 — boot realmente observado

Trechos discriminantes do console disponibilizado pelo operador:

```text
Hypervisor detected: KVM
Kernel command line: rootwait root=/dev/vda console=ttyS0
virtio_blk virtio1: [vda] 245760 512-byte logical blocks (120 MiB)
VFS: Mounted root (ext4 filesystem) readonly on device 254:0.
Run /sbin/init as init process
EXT4-fs (vda): re-mounted ... r/w.
Starting network: udhcpc: lease of 10.0.2.15 obtained from 10.0.2.2
Welcome to Buildroot
elo-os login: root
# cat /proc/1/comm
init
# cat /etc/elo-os-release
NAME="ELO/OS"
VERSION="0.1.0"
STATUS="development"
PLATFORM="qemu-x86_64"
# poweroff
Requesting system poweroff
reboot: Power down
```

**O que isso prova:** o convidado x86_64 conseguiu inicializar kernel, detectar disco virtio, montar ext4, executar BusyBox `init`, apresentar login, obter DHCP na rede NAT e desligar. **Não** prova firmware, GPU, touchscreen, estabilidade ou desempenho da Raspberry Pi 5.

**Memória em repouso medida pelo operador:** `free -m` informou ~486 MiB totais, ~13 MiB usados e nenhum swap. Trata-se de observação de bancada, **não** meta de desempenho, teste de carga, medição de energia ou consumo da futura aplicação Qt/ELO.

**Hashes de artefatos x86_64 registrados em `tests/boot/README.md`:**

```text
69c987643bca326ec0cd462c74a89b8832c854de8e76e34b4a2d179387a819b9  bzImage
653336607ad0c8ea876ae87489a60c2a9719639f326185bcedd0273dc21596d4  rootfs.ext4
```

### 1.4. Estados explicitamente pendentes

- `BOOTED_QEMU_AARCH64`: **não demonstrado**.
- `BOOTED_PI5`: **não demonstrado**.
- Qt6/QML via DRM/KMS/EGLFS: **não demonstrado**.
- Cliente ELO real, manifesto HTTPS, offline funcional, cache e idempotência: **não demonstrados**.
- Rootfs operacional sempre somente leitura, partição `/data` RW, tolerância a queda de energia, watchdog, rollback: **não demonstrados**.
- Integridade de build reproduzível bit a bit e cadeia de suprimentos homologada: **não demonstradas**.
- Segurança de produção: **não demonstrada** (`root` sem senha na VM é apenas condição de bancada).

---

## 2. ESTADOS E GATES — UMA LINGUAGEM PARA NÃO CONFUNDIR MARCOS

Os estados são **por perfil + artefato + commit**, não adjetivos globais do projeto.

| Estado | Significado | Evidência mínima |
|---|---|---|
| `PROPOSED` | Ideia ou ADR sem integração testada | Documento |
| `SCAFFOLDED` | Código/configuração presente e verificações sintáticas | Commit + Q0 |
| `BUILT` | Compilação bem-sucedida, artefatos e checksum | Exit code + hashes |
| `BOOTED_QEMU_X86` | Boot do alvo virtual x86_64 | Log de kernel/PID 1/login |
| `VERIFIED_QEMU_X86` | Testes específicos KVM/TCG concluídos | Relatório, logs, hashes e critérios |
| `BOOTED_QEMU_AARCH64` | Boot do alvo `virt` ARM64 | Log TCG ARM64, `uname -m=aarch64` |
| `BOOTED_PI5` | Boot no hardware Pi 5 | Registro de ensaio físico |
| `VERIFIED_PI5` | Testes físicos definidos para o marco aprovados | Matriz + evidências |
| `PRODUCTION` | Produto operacional homologado | Bloqueado por critérios futuros |

### Gate Q0 — Repositório

Sintaxe, arquivos, integração Kconfig, scripts, lint, revisão documental. **CI estrutural verde NÃO implica kernel compilado.**

### Gate Q1X — QEMU x86_64

Build, boot, PID 1, login, identidade, rede, desligamento e snapshot para artefatos x86_64 especificados. **Demonstrado**, conforme evidências de 08/11/2026.

### Gate Q1A — QEMU aarch64/virt

Exatamente o mesmo núcleo de comportamentos, agora na arquitetura ARM64. **Pendente.**

### Gate Q2 — Pi 5 físico

Boot da mídia, console real, drivers, ciclos de partida, alimentação e hardware. **Pendente.**

**Promover somente o gate que foi exercitado.** `KVM PASS` não equivale a `AARCH64 PASS`. `TCG x86_64 PASS` tampouco equivale a `TCG aarch64 PASS`.

---

## 3. DECISÃO ARQUITETURAL — UM PROJETO, TRÊS PERFIS

```text
                              ELO/OS
                        br2-external ELO_OS
                                 |
            +--------------------+--------------------+
            |                    |                    |
      elo_pi5_defconfig   elo_qemu_x86_64_defconfig   elo_qemu_aarch64_defconfig
            |                    |                    |
       output/pi5/         output/qemu-x86_64/       output/qemu-aarch64/
            |                    |                    |
      BCM2712 + SD          x86_64 + virtio          ARM64 virt + virtio
      firmware RPi          kernel 6.18.7           kernel ARM64 virt
            |                    |                    |
      Raspberry Pi 5        QEMU no Fedora 44       QEMU TCG no Fedora 44
      BOOT PENDENTE         BOOT DEMONSTRADO         A CRIAR E TESTAR
```

**Decisões obrigatórias:**

- `BR2_EXTERNAL` comum; `O=` **exclusivo** para cada arquitetura.
- Nunca usar `sdcard.img` da Pi 5 diretamente com `qemu-system-aarch64 -M virt`.
- Nunca carregar a `.config` BCM2712 no kernel ARM64 `virt`.
- Virtual x86_64 pode usar **KVM** no Fedora x86_64; ARM64 `virt` usa **TCG** nesse host.
- Em QEMU x86_64: `root=/dev/vda`, `console=ttyS0`; em ARM64 `virt`: `root=/dev/vda`, `console=ttyAMA0`; na Pi 5 o root é `mmcblk0p2` na imagem atual.
- Compartilhar semântica de identidade, serviços e testes; **não** supor equivalência entre drivers, DTB, GPU, bootloader ou métricas de tempo.
- Uma falha em ambiente virtual **não** autoriza afirmar falha do hardware; o inverso também vale.

**Por que x86_64 primeiro foi razoável?** Permitiu demonstrar init/rede/armazenamento rapidamente usando KVM. O plano ARM64 original permanece obrigatório, mas é **próxima etapa**, não motivo para invalidar a evidência x86_64.

---

## 4. LIÇÕES DO TESTE MANUAL — NÃO CONFUNDIR EXPLORAÇÃO COM FALHA

### 4.1. `sudo poweroff` falhou: resultado esperado

```text
-sh: sudo: not found
```

O convidado foi construído como sistema mínimo, sem `sudo`. Como o login já era `root`, a saída correta era `poweroff` diretamente. **Não adicionar `sudo` ao rootfs apenas para silenciar essa mensagem.** Documentar isso no roteiro de bancada.

### 4.2. `exit` voltou ao login: resultado esperado

`exit` encerra **a sessão de shell**, e `getty` oferece novo login. Não é desligamento nem reboot. Para desligar o convidado: `poweroff` como root. `Ctrl-a` e depois `x` fecha o QEMU pelo monitor, mas preferir encerramento limpo para testes de filesystem.

### 4.3. `ls -l` em `/root` informou `total 0`: não é erro

O diretório estava vazio. Isso não mede o conteúdo do root filesystem `/`. Usar `ls /` para inspecionar a raiz do sistema.

### 4.4. `pgrep -af` apresentou enorme quantidade de processos não relacionados

A expressão usada incluía `ld`, `make`, `gcc` e outros termos em uma busca por **linha de comando inteira**. Isso produziu coincidências no Firefox, VS Code, scripts e serviços que continham essas sequências. **O relatório resultante não indica que o Buildroot estava executando todos esses processos.**

Diagnóstico recomendado, sem sinalizar ou matar processos:

```bash
# Obter apenas as linhas de processos QEMU; o grep não aparece em seu próprio resultado.
ps -eo pid,ppid,stat,comm,args | grep -E '[q]emu-system-(x86_64|aarch64)' || true

# Observar a etapa no log, quando existir:
tail -n 30 /tmp/elo-os-qemu-build.log

# Testar presença dos artefatos (ausência durante o build não significa falha):
ls -lh output/qemu-x86_64/images/ 2>/dev/null || true
```

`grep` aqui é um auxílio; ele pode coincidir com uma linha de processo que **mencione** QEMU sem executá-lo. Se houver dúvida, conferir `comm`, PID, pai e log. Preferir registrar o PID do processo controlado quando um teste automatizado o inicia.

### 4.5. Mensagens repetidas de `Welcome to Buildroot` e `elo-os login:`

O login funcionou mesmo com banners repetidos. **Não classificar automaticamente como falha**, mas adicionar ensaio de estabilidade do prompt serial: iniciar sem digitação, verificar ausência de reinícios espontâneos de `getty`, aferir se a repetição decorre de entrada no console, retorno de sessões ou respawn anormal. Só abrir defeito com reprodução e log.

### 4.6. Ext4 iniciou RO e foi remontado RW

```text
VFS: Mounted root (ext4 filesystem) readonly
EXT4-fs (vda): re-mounted ... r/w
/dev/root on / type ext4 (rw,relatime)
```

Este é o estado **real** do P1 QEMU x86_64. `/tmp` e `/run` já aparecem como `tmpfs`, mas **a raiz NÃO é imutável**. A proteção das imagens ocorre no **host**, porque o launcher usa `snapshot=on`: escritas do convidado são descartadas entre sessões. Snapshot virtual **não substitui** uma arquitetura de rootfs RO + `/data` persistente no Pi 5.

### 4.7. Consumo de memória: medição inicial, sem exagero

`free -m` mostrou ~13 MiB usados, ~486 MiB totais disponíveis. Não interpretar como limite máximo, memória comprometida do QEMU, consumo sob carga, consumo da interface gráfica ou energia usada. Registrar kernel, pacotes, instante da medição e comando para futuras comparações.

### 4.8. Desligamento observado

O log mostrou parada de serviços, remontagem do ext4 em leitura, ACPI S5 e `reboot: Power down`. Isso é **evidência positiva de encerramento da VM**. Não comprova resiliência a quedas abruptas de energia.

---

## 5. AUDITORIA DE GIT E DOCUMENTAÇÃO — CORREÇÕES IMEDIATAS

**Base remota consultada:** `main@01574c6`. Os resultados relatados são do repositório, não de uma execução local da revisão deste MD.

| Caminho | Achado | Ordem |
|---|---|---|
| `tests/boot/README.md` | Relata KVM 2× e TCG 2×, hashes e critérios; conserva checkboxes físicos não atualizados | **PRESERVAR** prova virtual, desambiguar físico |
| `docs/tests/acceptance.md` | Ainda diz “apenas scaffold” | **CORRIGIR AGORA** |
| `CHANGELOG.md` | Ainda declara “nenhum build ou boot validado” | **CORRIGIR AGORA**, datando fatos |
| `README.md` | Cabeçalho continua `design-candidate / scaffold` | **REFORMULAR** como composição funcional experimental |
| `.github/workflows/structure.yml` | Executa somente `tests/smoke.sh` | **ROTULAR Q0**, ampliar verificação progressivamente |
| `scripts/run-qemu.sh` | Snapshots, NAT e KVM/TCG; login root sem senha | **MANTER NA BANCADA**, bloquear uso como perfil de produção |
| `docs/ELO-OS-IMPL-001_v0.1.1.md` | Não consta na árvore remota auditada | **ADICIONAR** somente após revisão desta entrega |
| `configs/elo_qemu_aarch64_defconfig` | Ainda não existe | **CRIAR NO PR ARM64** |
| `output/pi5`, `output/qemu-x86_64` | Saídas locais ignoradas no Git | **PRESERVAR** e registrar hashes; não versionar binários grandes |

**IMPORTANTE:** não retomar silenciosamente `README` antigo e alterar o fato histórico. A versão `0.1.0` do software não exige que o changelog esconda ensaios realizados depois do commit inicial. Registrar evidência com data e plataforma, mantendo a distinção entre teste e release.

### Contrato mínimo de atualização de `docs/tests/acceptance.md`

```text
P0       Raspberry Pi OS Lite + UI exploratória      NOT TESTED
P1-A     Estrutura/CI estática                       PASS
P1-B     Build da imagem Pi 5 ARM64                 PASS (build apenas)
P1-C     Boot QEMU x86_64: KVM/TCG                  PASS (escopo testado)
P1-D     Boot QEMU ARM64 virt                       NOT TESTED
P1-E     Boot físico Raspberry Pi 5                 NOT TESTED
P1-F     30 partidas físicas                         NOT TESTED
P2       Qt6/QML, DRM/KMS e periféricos             NOT TESTED
P3       ELO Server/Thin Client, offline            NOT TESTED
P4       Rootfs RO, /data, recuperação              NOT TESTED
P5       Update/rollback                            NOT TESTED
```

O relatório deve incluir **commit e SHA dos binários usados**. Estados mudam se a configuração relevante mudar; nada de herdar `PASS` de outra imagem.

### Regra de versionamento

- `ELO-OS-IMPL-001 v0.1.1`: revisão **documental**.
- `VERSION` continua `0.1.0` até decisão explícita de release.
- `01574c6` é o commit de referência do diagnóstico, **não** uma tag de release.
- Um novo commit de documentação não altera automaticamente o estado do kernel nem dos testes binários.

---

## 6. MATRIZ DE TRABALHO — PRIORIDADE, STATUS, ACEITE

| ID | Prio. | Estado em `01574c6` | Tarefa concreta | Critério de aceite |
|---|---|---|---|---|
| T-001 | P0 | **PENDENTE** | Criar perfil `elo_qemu_aarch64_defconfig` a partir de `qemu_aarch64_virt_defconfig` upstream 2026.08.1 | Configuração ARM64 `virt` válida, sem tocar Pi 5 |
| T-002 | P0 | **PARCIAL** | Generalizar `build.sh` para ARM64, com `O=` isolado e diagnóstico de conflito | `PROFILE=qemu-aarch64` gera artefatos próprios |
| T-003 | P0 | **X86 CONCLUÍDO / ARM PENDENTE** | Lançador ARM64 TCG serial, rede NAT, snapshot | Prompt de login ARM64 sem alterar imagens base |
| T-004 | P0 | **X86 CONCLUÍDO / ARM PENDENTE** | Estender smoke de boot para ARM64 | Teste login, PID 1, identidade, ext4, DHCP, poweroff |
| T-005 | P0 | **PENDENTE** | Corrigir README, CHANGELOG, acceptance, boot checklist | Nenhuma contradição entre `BUILT`, `BOOTED`, `VERIFIED` |
| T-006 | P0 | **PARCIAL** | Consolidar inventários Pi 5 e QEMU x86_64 | Hash, data, commit, perfil e origem do artefato |
| T-007 | P1 | **PENDENTE** | Separar `board/elo/common` de overlays por plataforma | Mesmo núcleo comum; identidade específica correta por alvo |
| T-008 | P1 | **PARCIAL** | Expandir `doctor.sh` por perfil e requisitos do Buildroot | `PASS/WARN/FAIL` justificado, sem instalar nada sozinho |
| T-009 | P1 | **PENDENTE** | Auditar alinhamento LBA e `genimage.cfg` real da Pi 5 | Parecer documentado; mudança só com teste físico |
| T-010 | P1 | **PARCIAL** | Auditar cmdline, serial e getty por plataforma | Console funcional e log, sem confundir ttyS0/ttyAMA0/ttyAMA10 |
| T-011 | P1 | **PROPOSTO** | Especificar rootfs RO + `/data` RW | ADR e testes futuros; **não marcar implementado** |
| T-012 | P1 | **PARCIAL** | Expandir CI: Q0 + config; Q1 opcional de boot | Gates distintos, sem “verde” enganoso |
| T-013 | P2 | **PENDENTE** | Qt6/QML e DRM/KMS no hardware | Primeiro garantir boot físico; ensaio gráfico independente |
| T-014 | P2 | **PROPOSTO** | ELO Server, idempotência, offline, recovery, atualizações | Contratos e ensaios próprios; não introduzir nesta rodada |
| T-015 | P0 | **PENDENTE** | Integrar este documento e fechamento P1 x86_64 | MD versionado em Git, histórico e PR com evidência |
| T-016 | P1 | **PENDENTE** | Tornar teste de console robusto contra respawn/duplicação | Sem falso PASS por prompt espúrio ou eco de comando |
| T-017 | P1 | **PENDENTE** | Definir licença e inventário de dependências | Licença de código clara, sem confundir licenças de terceiros |
| T-018 | P1 | **PENDENTE** | Segurança de GitHub Actions e revisão de PR | Permissões mínimas, pinning avaliado, gates antes de merge |

**Não negociar prioridades ao sabor da facilidade.** Um atalho x86_64 para demonstrar processos foi útil; não vira substituto do ARM64 nem do Pi 5.

**Cada tarefa deve apontar para:** issue/PR + commit + teste + resultado + evidência ou limitação explicitada. Sem prova, `NOT TESTED`.

---

## 7. SPRINT IMEDIATA — FECHAR O QUE JÁ FUNCIONA ANTES DE CRIAR MAIS

### P0-A — Congelamento observacional x86_64

1. Registrar baseline `01574c6` e cópias dos sumários de teste já aprovados.
2. Confirmar `bzImage`/`rootfs.ext4` por SHA-256 com os valores da seção 1.3.
3. Salvar informações de Buildroot, kernel, toolchain, QEMU e arquitetura do host.
4. Identificar a diferença entre observação manual (log apresentado) e teste automatizado (relatório versionado).
5. Atualizar `docs/tests/acceptance.md` e `CHANGELOG.md` antes de introduzir outra arquitetura.
6. Anexar breve registro `docs/evidence/P1-QEMU-X86-20261108.md`, sem imagens/binários gigantes ou dados sensíveis.

**Pronto quando:** equipe consegue apontar o commit e hashes exatos, executar o roteiro e explicar o que foi validado e o que não foi.

### P0-B — Corrigir mensagens para operador

- `README`: indicar que o perfil QEMU x86_64 tem boot comprovado; Pi 5 ainda requer teste físico.
- `tests/boot/README`: corrigir checkboxes físicos de “imagem gerada”/“hash registrado” quando comprovados; não marcar como feito o que depende de hardware.
- Documentar `root` sem senha **somente para bancada local**, `sudo` ausente, `exit` retornando a `getty`, `poweroff` como saída correta.
- Ao mencionar `snapshot=on`, explicar que raiz RW no convidado não é raiz somente leitura.

**Pronto quando:** uma pessoa que só lê o README entende a condição real de cada alvo.

### P0-C — Travar consistência mínima

- `tests/smoke.sh` valida sintaxe de scripts, existência de ambos os perfis existentes e coerência de referências.
- `python3 -m py_compile tests/boot/qemu-smoke.py` ou equivalente na CI Q0.
- Configuração `.config` de um perfil não pode ser reutilizada por outro.
- Falhar cedo se faltar `bzImage` ou `rootfs.ext4` quando o usuário solicitar boot x86_64.
- Exibir `PROFILE`, `BR2_EXTERNAL`, `O=`, release Buildroot e paths antes da compilação.

**Pronto quando:** CI continua rápida e honesta, rotulada **Q0**; compilação/boot ficam em gates separados.

---

## 8. QEMU ARM64 VIRT — O QUE A EQUIPE DEVE IMPLEMENTAR

### 8.1. Configuração de referência

Usar **somente** a release local fixada `Buildroot 2026.08.1` e sua configuração oficial `configs/qemu_aarch64_virt_defconfig`. Fonte primária: [Buildroot upstream](https://github.com/buildroot/buildroot/blob/2026.08.1/configs/qemu_aarch64_virt_defconfig).

O alvo ARM64 precisa de kernel para a placa virtual `virt`, drivers VirtIO, serial PL011 (`ttyAMA0`), ext4 e rede. **Não** trocar o kernel Pi 5 por esse kernel na imagem física.

**Desenho a implementar (não executar antes do merge do perfil):**

```text
configs/elo_qemu_aarch64_defconfig
board/elo/qemu-aarch64/rootfs-overlay/etc/elo-os-release
scripts/build.sh: PROFILE=qemu-aarch64
scripts/run-qemu.sh: seleção explícita de perfil
scripts/inspect-image.sh: suporte a Image e rootfs.ext4
output/qemu-aarch64/ (gerado; ignorado pelo Git)
tests/boot/qemu-arm64-smoke.py (ou smoke parametrizado)
```

Criar o arquivo derivado de `qemu_aarch64_virt_defconfig`; registrar o **diff** em relação ao upstream. Usar `BR2_ROOTFS_OVERLAY` comum e um overlay de identidade ARM64 específico. O `BR2_ROOTFS_POST_IMAGE_SCRIPT` upstream pode ser dispensado se utilizarmos o lançador próprio e documentarmos essa opção. Compilação de host QEMU pelo Buildroot pode ser desabilitada se o host Fedora fornecer o QEMU: registrar essa escolha, não supor que foi feita automaticamente.

### 8.2. Build proposto, depois que o perfil estiver implementado

```bash
cd ~/dev/cpp/elo-os

# SOMENTE após o novo perfil e scripts terem sido integrados.
PROFILE=qemu-aarch64 JOBS=8 ./scripts/build.sh
PROFILE=qemu-aarch64 ./scripts/inspect-image.sh

# Checagem de arquitetura e formato dos artefatos:
file output/qemu-aarch64/images/Image
file output/qemu-aarch64/images/rootfs.ext4
sha256sum output/qemu-aarch64/images/Image \
          output/qemu-aarch64/images/rootfs.ext4
```

**Requisitos:** ambiente/`O=` isolados; não recriar `output/pi5`; não sobrescrever `output/qemu-x86_64`; preservar artefatos e logs que documentam o P1.

### 8.3. Contrato do lançador QEMU ARM64

A equipe deve implementar um comando idempotente como:

```bash
PROFILE=qemu-aarch64 ./scripts/run-qemu.sh
```

**Referência conceitual de argumentos para o script (não é comando já implementado):**

```bash
qemu-system-aarch64 \
  -machine virt -cpu cortex-a53 -accel tcg \
  -m 1024 -smp 2 -nographic \
  -kernel output/qemu-aarch64/images/Image \
  -append 'rootwait root=/dev/vda console=ttyAMA0' \
  -drive file=output/qemu-aarch64/images/rootfs.ext4,if=none,format=raw,id=hd0,snapshot=on \
  -device virtio-blk-device,drive=hd0 \
  -netdev user,id=net0 \
  -device virtio-net-device,netdev=net0
```

O script real deve verificar arquivos e QEMU instalados, imprimir perfil/arquitetura e argumentos relevantes, evitar exposição de portas e cuidar de códigos de saída. Quando a VM rodar no host x86_64, **KVM não acelera convidado ARM64**: usar TCG.

### 8.4. Teste ARM64 obrigatório

Dentro do convidado, comprovar por saída **real**:

```sh
uname -m                       # aarch64
cat /etc/elo-os-release       # PLATFORM="qemu-aarch64"
cat /proc/1/comm               # init, conforme BusyBox
cat /proc/cmdline              # root=/dev/vda, console=ttyAMA0
mount                          # ext4 e estado real do rootfs
ls -l /dev/vda                 # disco virtio
ip -4 addr show                # interface + DHCP (não presumir nome)
ip route                       # rota padrão
poweroff                       # encerramento limpo
```

Teste automatizado: iniciar **duas vezes**, validar login, ausência de kernel panic, identidade/arquitetura, rede, shutdown, e **snapshot descartável** por comparação de escrita temporária entre sessões. Capturar `stdout/stderr`, código de saída e hashes do kernel/rootfs testados. Não exigir IP `10.0.2.15` se a rede configurada tiver parâmetros diferentes: testar a propriedade correta e registrar o IP observado.

### 8.5. Diagnóstico — sem improviso

| Sintoma | Investigar primeiro |
|---|---|
| Panic VFS | `root=/dev/vda`, ext4 integrado, virtio-blk e associação de drive |
| Sem console | `console=ttyAMA0`, PL011 e getty na configuração do alvo |
| Sem DHCP | Driver virtio-net, interface, udhcpc e rede NAT |
| Emulação lenta | TCG cross-architecture; não tomar isso como desempenho do Pi 5 |
| Mudança na imagem Pi 5 | `O=` compartilhado indevidamente; bloquear PR |
| Qt falha no QEMU | Escopo gráfico; não extrapolar para VC4/V3D da Pi 5 |
| Artefatos ausentes | Build incompleto; não rodar QEMU antes de concluir build |

---

## 9. CI E VERIFICAÇÃO — AUTOMATIZAR SEM MAQUIAR SUCESSO

**CI atual:** `.github/workflows/structure.yml` passou em `01574c6`, mas só executa `./tests/smoke.sh`. Sua conclusão significa **Q0 PASS**, não `Q1X PASS` por ação do GitHub. Q1X foi demonstrado nos testes locais, documentados à parte.

### Pipeline mínimo proposto

1. **`static-q0` obrigatório**: shell syntax/lint, Python compile, integridade da árvore, documentação/paths, checagem de arquivos que não deveriam entrar no Git.
2. **`config-q0` obrigatório**: carregar defconfigs de cada perfil, examinar Kconfig resultante; sem full build, quando possível.
3. **`qemu-x86-boot` separado**: compilar imagem em ambiente reprodutível e inicializar, com timeout e artefatos; só marcar PASS se houve boot efetivo. Custo alto? usar workflow manual/programado até estruturar cache e recursos.
4. **`qemu-arm64-boot` separado**: após criar o perfil, repetir gate com `TCG` e console ARM64.
5. **`pi5-hardware` externo**: relatório de ensaio manual/automatizado em hardware real, nunca simulá-lo com CI virtual.

**Regras:** nenhuma credencial em log, timeout controlado, artefato de falha preservado sem dados privados, token GitHub com permissões mínimas, proteção de `main` avaliada, revisão de actions e dependências. Não usar `sudo` nem desligar SELinux do Fedora como solução genérica de CI.

### Falhas do teste não devem mascarar regressões

- O teste deve buscar a **saída do convidado**, não eco dos comandos enviados.
- Login pode ser reapresentado após `exit`: distinguir comportamento legítimo de reinício de getty.
- Timeout deve produzir `FAIL` e log, **não** loop infinito.
- Um teste QEMU x86_64 **não** pode verificar ARM64 por nome ou por variável trocada sem imagem própria.
- Não mutar imagem base para testes: usar snapshot/cópia descartável.
- Hash do artefato antes e depois do teste deve continuar igual.

---

## 10. MATRIZ DE EVIDÊNCIAS E CRITÉRIOS DE ACEITE

| ID | Plataforma | Verificação | Situação atual | Prova exigida |
|---|---|---|---|---|
| H-001 | Host | Fedora 44, ferramenta QEMU e versão | Registro x86 existente | Inventário de ambiente |
| B-001 | Pi 5 | Compilação `sdcard.img` | **PASS — build** | Hash, `fdisk`, config, log |
| V-001 | QEMU x86_64 | Kernel + boot serial | **PASS — observado** | Console/PID 1 |
| V-002 | QEMU x86_64 | Rede DHCP, rota e identidade | **PASS — observado/testado** | Saída convidado |
| V-003 | QEMU x86_64 | 2× KVM / 2× TCG | **PASS — relatado em Git** | `tests/boot/README`, hashes/logs |
| V-004 | QEMU x86_64 | Snapshot descartável | **PASS — relatado em Git** | Teste entre sessões |
| A-001 | QEMU aarch64 | Defconfig derivada de upstream | **NOT TESTED** | Diff + `.config` |
| A-002 | QEMU aarch64 | Build isolado | **NOT TESTED** | Exit 0 + Image/rootfs hashes |
| A-003 | QEMU aarch64 | Login, PID 1, rootfs, identidade | **NOT TESTED** | Log + testes |
| A-004 | QEMU aarch64 | Rede, poweroff, snapshot | **NOT TESTED** | Reexecução + logs |
| P-001 | Raspberry Pi 5 | Boot e console real | **NOT TESTED** | Ensaio físico |
| P-002 | Raspberry Pi 5 | 30 ciclos de boot | **NOT TESTED** | Tabela de ciclos + falhas |
| P-003 | Raspberry Pi 5 | Queda de energia, mídia e retorno | **NOT TESTED** | Protocolo seguro dedicado |
| G-001 | Repositório | CI estática | **PASS — Q0** | Execução GitHub Actions |
| G-002 | Repositório | README/CHANGELOG/acceptance coerentes | **PENDENTE** | Revisão cruzada |
| F-001 | Todos | Rootfs RO e `/data` | **NOT IMPLEMENTED** | ADR + testes futuros |
| UI-001 | Pi 5 | Qt6/DRM/KMS | **NOT TESTED** | Demo funcional no hardware |

**Condição de promoção:** registrar o artefato testado, commit, máquina, método, resultado (PASS/FAIL/NOT TESTED), evidência e limitações. Estado parcial não deve ser promovido por entusiasmo.

---

## 11. RASPBERRY PI 5 — AVALIAÇÃO FÍSICA, SEM ATALHOS

### 11.1. Situação atual

`sdcard.img` compilada (152 MiB); partição FAT de 32 MiB e raiz ext4 de 120 MiB, configuração para `/dev/mmcblk0p2` e consoles `tty1`/`ttyAMA10`. **Não** foi demonstrado boot da Pi 5 em hardware real. Essa pendência permanece mesmo depois do sucesso de QEMU x86_64 ou ARM64 `virt`.

### 11.2. Alinhamento e `genimage`

A tabela de partições gerada começou em LBA 1 (FAT) e LBA 65537 (ext4), sem alinhamento convencional de 1 MiB. **Não é prova de corrupção.** Auditar `output/pi5/images/genimage.cfg`, comparar com Buildroot Pi 5 upstream e avaliar se corrigir o alinhamento é compatível com o boot físico. **Não** editar a imagem original com `fdisk` e **não** alterar hooks upstream sem ensaios.

### 11.3. Boot físico como experimento

- Preparar microSD de teste **descartável**; confirmar cuidadosamente o dispositivo antes de qualquer gravação.
- Verificar fonte, HDMI, teclado, versão de firmware/EEPROM e periféricos mínimos.
- Registrar artefato exato, SHA-256, data, revisão Git, bootloader e configuração de kernel.
- Provar `uname`, PID 1, console, armazenamento, identidade e desligamento.
- Repetir partidas frias conforme protocolo P1 e registrar falhas, não somente sucessos.
- Testes de queda de energia exigem protocolo e hardware adequados, mídia de testes e avaliação de integridade; **não** iniciar desligamentos bruscos aleatórios.

---

## 12. ROOTFS RO, `/data`, RECUPERAÇÃO — NÃO DECLARAR PRONTO

**Estado real x86_64:** raiz ext4 `rw` após init; `/run` e `/tmp` em `tmpfs`; emulação usa snapshot descartável no **host**. A Pi 5 atual apresenta apenas FAT + ext4, sem partição `/data` independente.

**Diretriz futura:**

```text
BOOT CONTROLADO
  + rootfs somente leitura
  + /data persistente leitura/escrita
  + /run e /tmp em tmpfs
  + mecanismo explícito de atualização/rollback
```

Não incluir esses componentes como uma grande reforma durante o fechamento de Q1A. Abrir ADR/PR próprio depois dos ensaios de boot. O desenho deve definir: estado de dispositivo, migrações, `fstab`, permissões, inicialização sem rede, logs, retenção, energia, idempotência das operações de configuração, recuperação e atualização segura.

**Critério científico:** somente chamar `rootfs RO` quando `mount` demonstrar `ro` **após o init ter concluído**, e quando tentativas de escrita indevida falharem conforme o contrato. `snapshot=on` não basta.

---

## 13. GRÁFICOS, ELO CLIENT E AS CAMADAS DE DOMÍNIO

### 13.1. Gráficos P2

Qt 6 / QML via EGLFS e DRM/KMS permanece **candidato** para a Pi 5. Evitar GNOME, KDE, X11 ou Chromium como dependência presumida. Avaliar Mesa/EGL/GBM, capacidade de tela cheia, touch, vídeo e recuperação em testes específicos. Weston/Wayland mínimo só entra se a experiência demonstrar necessidade.

No QEMU, futuramente podemos ter perfil gráfico de desenvolvimento; `virtio-gpu` não é GPU V3D/VC4, e comportamento/performance do emulador não homologam a Pi 5.

### 13.2. Contrato das três responsabilidades

```text
ELO Server      publica, coordena e autentica de forma segura
ELO Thin Client recebe, valida, apresenta e persiste o estritamente necessário
ELO/OS          inicializa, disponibiliza capacidades, protege e recupera
```

A imagem P1 só demonstra **infraestrutura de sistema**. Não chamar o aplicativo QML de ELO funcional antes de existir contrato ELO, cache, sessão, atualização de conteúdo e teste offline. Preservar o princípio do ELO como projeto próprio, não reduzi-lo à Raspberry Pi nem a este Linux.

---

## 14. SEGURANÇA, PROVENIÊNCIA E LICENÇA

- `root` **sem senha** e login serial em QEMU são uma **exceção temporária de laboratório**. Não transportar esse perfil para dispositivo em campo.
- `sudo` não está instalado; não adicionar privilégios sem necessidade.
- QEMU usa user-mode NAT; ausência de portas encaminhadas é uma propriedade do lançador atual, não auditoria completa de rede.
- Não embarcar senhas, certificados privados, tokens, imagens biométricas ou dados pessoais nas imagens ou commits.
- SSH não deve ser habilitado automaticamente para simplificar o smoke; login local/serial basta para esta rodada.
- Não desabilitar verificação TLS, SELinux ou verificações de integridade para contornar erros.
- `uname`/strings de compilador e nome do host de build servem à **proveniência**; não provaram onde o convidado foi executado. Registrar commit Buildroot, versão da toolchain e configuração.
- Definir licença de software ELO/OS e inventário das dependências e suas respectivas obrigações. Não presumir licença herdada do projeto ELO.

---

## 15. MODELO DE EVIDÊNCIA OBRIGATÓRIO — COPIAR PARA CADA MARCO

Salvar como `docs/evidence/<MARCO>-<PERFIL>-AAAAMMDD.md` após executar o ensaio. Evitar logs grandes no Git; anexar sumários e localizações, mantendo arquivos de diagnóstico sob `output/` (ignorado).

```markdown
# ELO/OS — Evidência de execução

- Data/hora e fuso:
- Operador:
- Perfil: pi5 | qemu-x86_64 | qemu-aarch64
- Plataforma de execução:
- Kernel e configuração:
- Buildroot e revisão:
- Commit ELO/OS:
- Comando de build:
- Exit code do build:
- Comando de boot:
- Exit code do teste:
- Hash do kernel:
- Hash do rootfs ou sdcard.img:

## Testes
| ID | Critério | Resultado PASS/FAIL/NOT TESTED | Evidência |
|---|---|---|---|
| ... | ... | ... | ... |

## Observações e limites
- O que foi visto diretamente:
- O que consta apenas do relatório da equipe:
- O que NÃO foi testado:
- Erros, avisos e suas interpretações:

## Encerramento
- Resultado do marco:
- Issues abertas:
- Revisão e aprovação:
```

**Todo `PASS` deve apontar para um artefato testado e método capaz de exercitar a propriedade alegada.** Logs resumidos podem omitir ruído, nunca o código de saída relevante ou a evidência discriminante.

---

## 16. INSTRUÇÕES DE GIT E EXECUÇÃO — NÃO INTERROMPER A EQUIPE

### 16.1. Antes de qualquer atualização local

Não fazer `pull` enquanto uma compilação/VM/teste da equipe estiver usando a mesma árvore ou alterando código; não rodar dois builds no mesmo `O=`.

```bash
cd ~/dev/cpp/elo-os

git status --short
git log -1 --oneline

# Consulta ao remoto não muda os arquivos de trabalho:
git fetch origin
git log --oneline HEAD..origin/main
```

Após testes concluídos, árvore limpa e ausência de operações que dependam da versão corrente:

```bash
git pull --ff-only
./tests/smoke.sh
./scripts/doctor.sh
```

Se houver alterações locais, fazer revisão antes do pull; **não** `git reset --hard` por conveniência.

### 16.2. Evitar recompilar o que já foi demonstrado

```bash
# Só inspecionar os artefatos x86_64 existentes:
PROFILE=qemu-x86_64 ./scripts/inspect-image.sh

# Rodar a VM para exploração interativa, se não houver
# outro teste concorrente:
./scripts/run-qemu.sh
```

`python3 tests/boot/qemu-smoke.py` pode ser usado como regressão com artefatos intactos quando houver mudança relevante; não é obrigação repeti-lo toda vez que se abre um terminal. No shell da VM, `poweroff` (não `sudo poweroff`).

### 16.3. Integração deste documento no repositório

Após baixar o arquivo e revisar seu conteúdo:

```bash
cd ~/dev/cpp/elo-os
cp ~/Downloads/ELO-OS-IMPL-001_v0.1.1.md docs/

git add docs/ELO-OS-IMPL-001_v0.1.1.md
git commit -m "docs: consolidate P1 x86 boot and ARM64 validation plan"
git push origin main
```

**Preferência de governança:** abrir PR para documentação e outro para perfil ARM64. Não misturar grande refatoração de imagens com o registro retrospectivo das evidências. Os comandos acima demonstram o fluxo manual e devem ser adaptados se a equipe estiver trabalhando por branches/PRs.

---

## 17. DEFINIÇÃO DE PRONTO — PRÓXIMAS ENTREGAS

### Entrega A — **Fechamento P1-QEMU-X86**

- [ ] `docs/tests/acceptance.md` registra o gate x86_64 aprovado e Pi 5 físico pendente.
- [ ] `README.md` e `CHANGELOG.md` não contradizem build Pi 5 nem boot virtual.
- [ ] `tests/boot/README.md` indica com precisão testes físicos pendentes, dados da execução e hashes.
- [ ] Este `IMPL-001_v0.1.1.md` está versionado com histórico.
- [ ] CI Q0 passa; não declarar Q1 via CI estático.
- [ ] Não houve alteração inesperada em artefatos Pi 5 e x86_64.

### Entrega B — **QEMU ARM64 `virt`**

- [ ] Novo perfil deriva da defconfig oficial Buildroot 2026.08.1, diferenças documentadas.
- [ ] Kernel `Image` e rootfs ext4 AArch64 gerados em `output/qemu-aarch64`, com hashes.
- [ ] Launcher TCG sem root/port forwarding e com snapshot descartável.
- [ ] Boot ARM64 demonstra `aarch64`, PID 1, getty serial `ttyAMA0`, identidade e rootfs.
- [ ] Rede/DHCP, desligamento e segunda sessão testados.
- [ ] Teste automatizado tem timeout, código de saída e artefatos de falha.
- [ ] Os testes x86_64 permanecem válidos e o `output/pi5` intacto.

### Entrega C — **Primeiro boot físico Pi 5**

- [ ] Mídia correta identificada e gravada com procedimento seguro.
- [ ] Boot físico e console demonstrados, kernel/DTB/EEPROM inventariados.
- [ ] Primeiros testes de rede e shutdown documentados.
- [ ] Plano de 30 partidas, mídia e energia definido e executado.
- [ ] Nenhum PASS virtual foi transferido automaticamente para o hardware.

**Merge só com:** escopo claro, evidência, revisão, ausência de segredos e resultado de teste honesto. Falha reproduzível vira issue, não desaparece no texto.

---

## 18. ORDEM FINAL — CAVEMAN FULL

> **JÁ COMPILAMOS O LINUX DA PI 5. NÃO DISSEMOS QUE ELE BOOTOU NA PI 5.**  
> **JÁ INICIAMOS O ELO/OS EM QEMU x86_64. NÃO DISSEMOS QUE ISSO É ARM64.**  
> **ROOTFS RW + SNAPSHOT DESCARTÁVEL NÃO É ROOTFS IMUTÁVEL.**  
> **Q0 VERDE NÃO É Q1 VERDE.**  
> **NÃO RECOMPILAR POR RITUAL. NÃO ALTERAR POR INTUIÇÃO.**  
> **MEDIR. PROVAR. REGISTRAR. ENTÃO AVANÇAR.**

**FAÇA SIMPLES. DEPOIS DEIXE MAIS LEVE.**  
**SEMPRE PRONTO. SEMPRE INCOMPLETO.**

---

## Histórico de versões

| Versão | Data | Alteração |
|---|---|---|
| `0.1.0` | 2026-11-08 | Plano inicial: auditoria P1, separação física/virtual e instruções originais para QEMU ARM64. |
| `0.1.1` | 2026-11-08 | Incorpora o boot QEMU x86_64 e commit `01574c6`, resultados KVM/TCG, leitura crítica dos comandos manuais, correção de estados/documentação, gates Q0/Q1X/Q1A/Q2 e novo plano executivo para a equipe. |

## Referências e proveniência

1. **Código/estado auditado:** https://github.com/jpereiratrindade/ELO-OS/tree/01574c60d06d82070f82d0ef969bef020c694c7e
2. **Registro de testes x86_64:** https://github.com/jpereiratrindade/ELO-OS/blob/01574c60d06d82070f82d0ef969bef020c694c7e/tests/boot/README.md
3. **Commit de evidência:** https://github.com/jpereiratrindade/ELO-OS/commit/01574c60d06d82070f82d0ef969bef020c694c7e
4. **Perfil ARM64 upstream:** https://github.com/buildroot/buildroot/blob/2026.08.1/configs/qemu_aarch64_virt_defconfig
5. **Documentação QEMU ARM:** https://www.qemu.org/docs/master/system/target-arm
6. **Documento original:** `ELO-OS-IMPL-001_v0.1.0.md`, preservado como linha de base.
7. **Evidência adicional:** logs de terminal fornecidos na conversa de 08/11/2026 — boot manual, `/proc/1/comm`, `mount`, `free -m`, `poweroff`.

**Observação final:** novas alterações em `main` após `01574c6` exigem comparação, não migração automática das declarações deste documento.
