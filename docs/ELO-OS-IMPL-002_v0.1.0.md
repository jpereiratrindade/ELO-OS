---
document_id: ELO-OS-IMPL-002
title: "ELO/OS — Evolução virtual P2: núcleo do cliente, primeira interface e testes antes da Raspberry Pi 5"
version: 0.1.0
status: action-required
created: 2026-11-08
repository: https://github.com/jpereiratrindade/ELO-OS
baseline_commit: 02b71076f1356584d8dfcae4be464ff476b1cef7
software_version_at_baseline: 0.1.0
host: Fedora 44 x86_64
verified_virtual_profiles: [qemu-x86_64, qemu-aarch64]
physical_target: Raspberry Pi 5 aarch64
related_documents:
  - docs/ELO-OS-BASES-001_v0.1.0.md
  - docs/ELO-OS-IMPL-001_v0.1.1.md
  - docs/tests/acceptance.md
  - docs/evidence/P1-QEMU-X86-20261108.md
  - docs/evidence/P1-QEMU-AARCH64-20261108.md
  - docs/evidence/P1-BUILT-PI5-20261108.md
---

# ELO/OS — IMPL-002 v0.1.0 — CAVEMAN FULL

> **FAÇA SIMPLES. DEPOIS DEIXE MAIS LEVE.**  
> **SEMPRE PRONTO. SEMPRE INCOMPLETO.**  
> **REGRA:** uma capacidade real, testada e registrada por vez. Não confundir interface, estado, processo e evidência.

**DESTINATÁRIO:** equipe de desenvolvimento ELO/OS.  
**TIPO:** ordem de implementação, não relatório de resultado.  
**DECISÃO:** prosseguir no Fedora 44, sem condicionar o desenvolvimento ao primeiro boot físico do Raspberry Pi 5.

## 0. ORDEM EXECUTIVA — LER PRIMEIRO

**FAZER AGORA**

1. Preservar os três baselines já obtidos: imagem Pi 5 (`BUILT`), QEMU x86_64 (`Q1X PASS`) e QEMU ARM64 (`Q1A PASS`).
2. Encerrar e registrar a inspeção FAT da imagem Pi 5 quando houver a saída real de `fsck.fat -n -v`. **Não presumir PASS a partir da existência do executável.** Não bloquear trabalho de software por essa pendência.
3. Criar **núcleo portátil de cliente** em C++, sem Qt, sem rede e sem modificações no kernel, como biblioteca testável no Fedora. Esta é lógica do *ELO Thin Client*, **não** responsabilidade do ELO/OS.
4. Ligar essa biblioteca à demonstração Qt 6/QML já existente, com distinção entre estado de demonstração e estado operacional verdadeiro.
5. Testar a GUI primeiro **no host Fedora**, depois em **novo perfil gráfico virtual isolado**. Manter os perfis QEMU de console intactos.
6. Só depois cruzar o mesmo código de aplicação para AArch64 e verificar a compatibilidade da toolchain. A GPU V3D/VC4 e a inicialização gráfica **reais** ficarão para a Raspberry Pi 5.
7. Entregar código, testes, métricas, logs, registro de versões e relatório de limitações. Não anunciar integração com ELO Server antes de existir contrato implementado e testado.

**NÃO FAZER:** recompilar Pi 5 ou os baselines históricos sem mudança motivada; editar `output/pi5/images/sdcard.img` ou `boot.vfat`; adicionar GNOME/KDE/X11, Chromium, Docker, banco de dados ou serviço web sem requisito; ativar SSH público, senha padrão em produção, watchdog, A/B e `/data` físico nesta rodada; anunciar `READY_LOCAL` apenas porque um texto apareceu na tela.

**SAÍDA ESPERADA:** `P2-V0` — uma aplicação gráfica de bancada, com núcleo de estados testado, executando localmente e opcionalmente em VM, que permanece utilizável sem servidor. **Não** significa `P2-PI5` homologado.

---

## 1. BASELINE CONHECIDO — CONGELAR O QUE FUNCIONA

Base de referência consultada em 08/11/2026: commit `02b7107` de `main`. Não presuma que a árvore local do mantenedor já esteja atualizada: confira `git status` e `git log` antes de alterar.

| Evidência | Estado permitido | Limite |
| --- | --- | --- |
| Pi 5 Buildroot `sdcard.img` | `BUILT_PI5` | Boot físico `NOT TESTED` |
| Preflight Pi 5 somente leitura | `PASS_IMAGE_PREFLIGHT` | Não verifica arquivos ou firmware; não prova boot |
| QEMU x86_64 em KVM/TCG | `VERIFIED_QEMU_X86` | Não valida ARM64 nem GPU Pi 5 |
| QEMU AArch64 `virt` em TCG | `BOOTED_QEMU_AARCH64 / Q1A PASS` | Não emula BCM2712 |
| Cliente Qt 6/QML do repositório | `SCAFFOLDED` | Demo opcional; não comprova execução gráfica |
| ELO Server ↔ Thin Client | `PROPOSED` | Rotas do documento-base são ilustrativas |
| Rootfs somente leitura + `/data` | `PROPOSED` | Na VM a raiz é RW, com snapshot no host |
| Pi 5 FAT: MBR 0x0c e volume FAT16 | `OBSERVED` | Compatibilidade real ainda não testada |

Hash Pi 5 preservado: `a858973142ea7d6560389ee71b14dfbad828bc940f944e7aa6682fef7c4f32fb`. Para os baselines QEMU, usar sempre os relatórios e hashes de `docs/evidence/`, não valores reconstituídos de memória.

**REGRA DE REGRESSÃO:** alteração documental não invalida um binário já testado; qualquer novo binário, nova configuração, overlay ou launcher relevante exige teste para o novo hash/escopo. Os baselines físicos e virtuais não se substituem.

---

## 2. ARQUITETURA — TRÊS COMPONENTES, SEM MISTURA

```text
ELO SERVER (projeto/serviço separado)
    publica conteúdo e contratos autenticados
             |
        HTTPS (futuro, contrato explicitamente acordado)
             |
             v
ELO THIN CLIENT — C++ + Qt 6/QML
    [núcleo portátil: estado, sessão, interface de conteúdo]
    [adaptadores: armazenamento, rede, apresentação]
             |
    solicita capacidades do sistema operacional
             v
ELO/OS — Buildroot + Linux + BusyBox init
    boot, processos, console, arquivos, rede, dispositivos,
    montagem, permissões, recuperação operacional
```

**Não colocar o domínio ELO dentro do sistema operacional.** O ELO/OS pode incluir o pacote da aplicação na imagem; isso não lhe transfere responsabilidade sobre identidade de pessoa, semântica de experiência, conteúdo ou autorização.

**Não criar um daemon para cada caixa do diagrama.** Núcleo + GUI podem estar no mesmo processo. As fronteiras devem ser de código e contratos; processo separado só se uma necessidade medida exigir.

### 2.1. Estrutura proposta, ainda NÃO implementada

```text
apps/elo-client-core/              # CRIAR: lógica portátil C++ testável
  CMakeLists.txt
  include/elo/client/{State,Controller,Interfaces}.hpp
  src/{State,Controller}.cpp
  tests/{state-transitions,offline-boot,failures}.cpp
package/elo-client/                # EXISTE: demonstrador Qt; integrar sem quebrar demo
  src/{main.cpp,Main.qml,CMakeLists.txt}
configs/
  elo_qemu_x86_64_defconfig        # EXISTE: perfil console — NÃO ALTERAR por GUI
  elo_qemu_aarch64_defconfig       # EXISTE: perfil console — NÃO ALTERAR por GUI
  elo_pi5_defconfig                # EXISTE: perfil físico — NÃO ALTERAR nesta rodada
  elo_qemu_x86_64_gui_defconfig    # CRIAR somente após estudo das dependências
scripts/
  run-qemu-gui.sh                  # CRIAR se novo perfil for efetivamente habilitado
tests/
  client/                          # CRIAR: CTest e ensaios de estados
  gui/                             # CRIAR: smoke gráfico e evidências
```

A divisão de fonte pode ficar no repositório ELO/OS **provisoriamente**, mas avaliar posteriormente se o código do cliente deve ser compartilhado com o projeto ELO de origem. Evitar duplicação de regras constitutivas do ELO.

---

## 3. MARCO P2-A — NÚCLEO PORTÁTIL PRIMEIRO

### T-201 — Núcleo puro em C++, sem dependência de Qt

**Implementar:** controlador de ciclo de vida do cliente; enumeração explícita de estados; eventos tipados; transições determinísticas; portas abstratas para conteúdo, rede, relógio e persistência; executor local de teste.

**Condição:** nenhum include de Qt, libcurl, socket, `system()` ou acesso automático a arquivos no núcleo. O núcleo recebe informações de adaptadores e decide transições; não realiza I/O escondido.

**Estados constitutivos do projeto-base** (não inventar estados alternativos sem ADR):

- `BOOTING`
- `READY_LOCAL`
- `CONNECTING`
- `ONLINE`
- `DEGRADED_OFFLINE`
- `UPDATE_STAGED`
- `VALIDATING`
- `ERROR_RECOVERABLE`
- `RESTARTING`
- `ERROR_FATAL`

`DIAGNOSTIC_SCREEN` é a apresentação prevista após erro fatal, não prova de estado saudável. O protótipo pode usar `DEMO_READY` na GUI **apenas como rótulo de demonstração**, nunca como alegação de sessão offline funcional.

**Pré-condição para `READY_LOCAL`:** houve carga e validação de um conteúdo local de teste definido, compatível e apresentável, com resultado observável. O conteúdo de teste deve ser claramente identificado como *fixture*, não uma experiência ELO real.

### T-202 — Ciclo offline sem servidor

**Implementar como comportamento de bancada:** cliente inicia, usa fixture local válida, segue apresentando quando não há rede; indisponibilidade de servidor não bloqueia boot nem provoca `reboot` ou `ERROR_FATAL` por si só.

**Injetar:** rede ausente antes do boot; rede perdida depois da apresentação; reconexão; fixture inexistente/corrompida; timeout de adaptador; evento repetido; término do processo.

**Definir o que é sucesso:** um teste demonstra a permanência da mesma experiência local durante os eventos de rede. O simples fato de haver console, PID e IP **não** satisfaz este critério.

### T-203 — Contratos separados antes de integrar HTTPS

**Criar interfaces, não endpoints fictícios:** `ContentCatalog`, `LocalStore`, `NetworkStatus`, `PresentationPort`, `Clock`, `Diagnostics`. Contratos devem distinguir erro temporário, conteúdo inválido e erro fatal. Dados binários devem ser validados por tamanho/hash **antes** de ativação.

**Não implementar** `GET /v1/client/manifest` nem outras rotas como se o servidor as fornecesse: `ELO-OS-BASES-001` as registra apenas como propostas. Sua integração depende da negociação com o repositório/contrato ELO Server.

### T-204 — Linguagem e toolchain

Prioridade: C++23 portátil que compile corretamente nas toolchains disponíveis. **C++26 como objetivo e experimento de recurso**, não mera flag `-std=c++2c` que encobre falta de biblioteca. Registrar versão de GCC, biblioteca-padrão e resultado de `try_compile` de cada recurso efetivamente usado. Não exigir que Qt 6 seja compilado em C++26.

---

## 4. MARCO P2-B — PRIMEIRA INTERFACE REAL NO FEDORA

### T-205 — Integrar núcleo e QML

O `package/elo-client/src/Main.qml` atual apenas exibe uma tela estática com `READY_LOCAL`. Revisar esse texto: não exibir estado operacional como fato antes de existir controlador/fixture válido.

**Implementar:** modelo Qt pequeno que expõe o estado do núcleo (`Q_PROPERTY` ou equivalente) e aciona atualização de interface por transições reais. UI inicialmente simples: identidade do sistema, estado do cliente, nome/versão da fixture local, conectividade (sem revelar segredos) e painel de falhas recuperáveis.

**Não desenvolver** domínio próprio novo, reconhecimento biométrico, coleta de câmera, animação pesada ou navegador. Não depender de rede para exibir a primeira tela útil.

### T-206 — Testar Qt no Fedora **antes** de cruzar para Buildroot

A equipe deve verificar disponibilidade do Qt 6, compilar a aplicação nativamente e executá-la na sessão gráfica Fedora. Isso valida código e QML **no host**; não prova compatibilidade EGLFS/DRM/KMS da Pi 5.

**Quando a implementação existir**, o fluxo esperado será equivalente a:

```bash
# Na raiz do repo; caminhos abaixo são NOVOS e devem ser criados pela equipe
cmake -S apps/elo-client-core -B build/elo-client-core \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON
cmake --build build/elo-client-core -j4
ctest --test-dir build/elo-client-core --output-on-failure

# Depois de integrar a GUI e criar um alvo/roteiro nativo documentado:
# cmake -S ... -B build/elo-client-gui ...
# cmake --build build/elo-client-gui -j4
# executar binário no Fedora e registrar screenshot/log, sem afirmar teste Pi 5
```

**NÃO executar o primeiro comando antes da equipe criar `apps/elo-client-core`.** Os comandos descrevem o contrato da entrega, não arquivos hoje existentes.

Teste Qt `offscreen` é útil para inicialização e automação, mas não substitui a inspeção visual de uma janela efetivamente apresentada. Captura de tela e observação de entrada são testes distintos de *bootstrap*.

### T-207 — Perfil GUI virtual isolado

Após o sucesso do host, criar **novo perfil opt-in**, preferencialmente `qemu-x86_64-gui`, com pasta de saída própria; manter `qemu-x86_64`, `qemu-aarch64` e `pi5` como perfis de referência.

**Decisão em aberto:** comparar configuração mínima `virtio-gpu`/DRM/Qt com Weston/Wayland mínimo; não presumir que EGLFS usado na Pi 5 seja apropriado para a GPU virtual. Documentar por que cada pacote foi adicionado. O demonstrador gráfico não deve depender de GNOME/KDE/Chromium/X11.

**Gate de aceitação:** build terminado; QEMU inicia; `init` sobe; aplicação abre de fato; fixture é visível; desconectar a rede não remove conteúdo; `poweroff` encerra; logs/versões/hashes registrados. Se a virtualização gráfica apresentar limitações, registrar como tal, sem promover o hardware físico.

**IMPORTANTE:** não executar outro `make` sobre o mesmo `O=` de um build em andamento. Novo perfil = nova `.config` e novo `output/`.

---

## 5. MARCO P2-C — PREPARAR O ARM64, SEM CONFUNDIR GPU

### T-208 — Compilação cruzada ARM64

Depois do núcleo e GUI nativos aprovados, compilar o núcleo com o compilador ARM64 da toolchain Buildroot já fixada, usando um perfil próprio ou integração opt-in no ambiente virtual ARM64; testar execução em `qemu-aarch64` **somente do código que não precise de GPU**.

**Gates:** ELF AArch64 correto, bibliotecas resolvidas, inicialização do controlador, transições offline e sem segredos; preservar `Image` e `rootfs.ext4` ARM64 históricos quando criar novo perfil de app.

Qt ARM64 poderá ser compilado em perfil separado, com dependências explicitamente rastreadas. A imagem Pi 5 `sdcard.img` original **não** deve ser reescrita ou tomada como compatível com o pacote sem novo build/teste.

**Não afirmar:** que o uso de `virtio-gpu` emula V3D/VC4, que taxa de quadros no QEMU prediz Pi 5 ou que TCG é benchmark de boot físico.

---

## 6. CONFIABILIDADE TESTÁVEL EM HOST, SEM NOVO DISCO PI 5

### T-209 — Ativação local de conteúdo (protótipo isolado)

Implementar, para fixture não sensível, o ciclo `staged → validated → active` com diretório temporário próprio. Não destruir ativo se staged falhar; comparar tamanho e SHA-256; escrever e `fsync` arquivos; publicar mudança no **mesmo filesystem** via `rename` apropriado e sincronizar diretório. Se múltiplos arquivos precisarem de troca conjunta, usar marcador/manifesto de ativação único ou transação, não supor que vários `rename()` formam uma transação.

**Bateria:** arquivo truncado, hash errado, falta de espaço, falha antes/depois do `rename`, repetição da mesma ativação, reinício com fixture antiga válida. A persistência operacional definitiva `/data` ficará para P4; o teste host deve usar diretório descartável de testes.

### T-210 — Fila de eventos futura, sem fabricar protocolo

Definir formato de evento de teste e política local de reenvio idempotente, com o princípio: mesma chave + mesmo payload → mesmo efeito; mesma chave + payload diferente → conflito explícito. **Não chamar a função de integração real com servidor.** Nenhum conteúdo pessoal ou biométrico em fixtures.

### T-211 — Supervisão controlada

Testar execução/parada do processo e backoff de reinício em bancada, sem watchdog nem reboot da VM por indisponibilidade da rede. Distinguir `process_alive` de `presentation_healthy`. Uma aplicação travada mas com PID presente deve falhar no teste de saúde observável.

**Não ativar** novo serviço no perfil físico durante esta rodada.

---

## 7. MATRIZ DE TAREFAS — ORDEM, DONO E PROVA

| ID | Prioridade | Entrega | Estado em 08/11/2026 | Critério de pronto |
| --- | --- | --- | --- | --- |
| T-200 | P0 | Congelar baseline P1 e inventariar novos perfis | A executar | Hash/revisão/matriz preservados |
| T-201 | P0 | Núcleo C++ sem Qt | A implementar | CTest passa, nenhum I/O oculto |
| T-202 | P0 | Boot offline com fixture válida | A implementar | Apresentação útil sem rede |
| T-203 | P0 | Contratos de adaptadores | A implementar | Sem endpoints inventados |
| T-204 | P1 | Prova de compatibilidade C++23/26 | A implementar | Recursos necessários compilam nos alvos |
| T-205 | P0 | GUI Qt ligada ao estado real | A implementar | UI reflete transições, não strings fixas |
| T-206 | P0 | Execução nativa Fedora | A implementar | Captura/observação real da GUI |
| T-207 | P1 | Perfil QEMU gráfico isolado | A estudar/implementar | Boot+GUI+offline+shutdown+evidência |
| T-208 | P1 | Cruzamento ARM64 do núcleo | A implementar | Testes funcionais no executável AArch64 |
| T-209 | P1 | Ativação de fixture e falhas | A implementar | Integridade e retorno ao ativo anterior |
| T-210 | P2 | Modelo de eventos idempotentes | A especificar | Testes locais, sem alegação de servidor |
| T-211 | P1 | Supervisão da aplicação | A implementar | Recuperação limitada e observável |
| T-212 | P1 | Atualizar docs/CI | A implementar | Estados coerentes e gates auditáveis |
| T-213 | P2 | Registro FAT e preparação Pi 5 | Em aberto | `fsck.fat` real e teste físico posteriores |

**Para cada tarefa:** issue, arquivos alterados, revisão Git, teste, relatório/hashes, risco, decisão de merge. Não usar percentual de progresso subjetivo para substituir evidência.

---

## 8. GATES E CRITÉRIOS DE ACEITAÇÃO

| Gate | Ambiente | Critério | Permissão ao concluir |
| --- | --- | --- | --- |
| `Q0` | Git/CI | lint, sintaxe, Kconfig, testes Python existentes | Integridade estrutural |
| `Q1X` | QEMU x86_64 console | baseline histórico aprovado | **Não reabrir sem modificação** |
| `Q1A` | QEMU ARM64 console | baseline histórico aprovado | **Não reabrir sem modificação** |
| `P2-C0` | Fedora/C++ | testes do núcleo passam, offline determinístico | Núcleo experimental validado |
| `P2-HGUI` | Fedora gráfico | Qt abre janela útil e estado real é visível | Interface host validada |
| `P2-QGUI` | QEMU GUI isolado | UI, offline, falha/reinício, shutdown observados | GUI virtual validada |
| `P2-A64` | ARM64 virtual | binário AArch64 e núcleo offline aprovados | Núcleo ARM64 validado |
| `P2-PI5` | Pi 5 física | vídeo, driver, entrada e boot gráfico comprovados | **Pendente até hardware** |
| `P4-DATA` | Ambiente apropriado | root RO + `/data` RW + falhas | **Não implementado nesta rodada** |

**Critério antissimulação:** `READY_LOCAL` somente se conteúdo realmente válido puder ser apresentado; `ONLINE` somente se conexão autenticada e protocolo real operarem. Texto em QML ou IP DHCP não satisfazem tais condições.

**Teste negativo obrigatório:** processo não deve anunciar sucesso após erro de fixture, ausência de rede, falha de validação ou impossibilidade de apresentar. Falha deve resultar em estado/erro explícito, não exceção silenciosa.

**Relatório mínimo:** commit, plataforma, compilador, kernel/Qt quando aplicável, comandos, exit codes, duração, hashes dos artefatos, testes aprovados/reprovados, comportamento observado e próximos limites.

---

## 9. INSTRUÇÃO DE EXECUÇÃO LOCAL — SEM TOCAR NO PI 5

Com todas as VMs/builds encerrados, e depois de confirmar que não há arquivos locais a preservar:

```bash
cd ~/dev/cpp/elo-os

git status --short
git log -1 --oneline

git fetch origin
# Revise diferenças antes de atualizar:
git log --oneline HEAD..origin/main

# Se o estado local estiver limpo e não houver operações paralelas:
git pull --ff-only

# Criar branch da PR de desenvolvimento, SEM mexer em output/pi5
# Só após a equipe concordar com a divisão de trabalho:
git switch -c feat/p2-client-offline-core

# Gates existentes, somente leitura do produto:
./tests/smoke.sh
python3 tests/config-smoke.py

# Depois de implementar T-201, T-202 e testes correspondentes:
# cmake -S apps/elo-client-core -B build/elo-client-core -DBUILD_TESTING=ON
# cmake --build build/elo-client-core -j4
# ctest --test-dir build/elo-client-core --output-on-failure
```

Não use `PROFILE=pi5 ./scripts/build.sh` nem reconfigure o `O=` da Pi 5 nessa rodada. Não são necessárias gravação de SD, alterações de EEPROM, reformatar partições ou conectar hardware. Código e fixtures devem residir em fontes/testes versionados; `build/` e `output/` são artefatos ignorados.

### 9.1. O que NÃO estamos afirmando sobre o `fsck.fat`

O executável foi localizado em `output/pi5/host/sbin/fsck.fat` e em `/usr/bin/fsck.fat`; **não recebemos sua saída de diagnóstico**. O arquivo FAT já teve diretório e `config.txt`/`cmdline.txt`/`Image`/DTBs lidos pela ferramenta `mtools`. Isso não equivale a `fsck.fat` aprovado nem prova que a Pi 5 inicializa. Quando o teste for retomado, capturar output e exit code sem reparar o volume; preservar hash antes/depois.

---

## 10. DECISÕES E BLOQUEIOS

1. **ADR-002** permanece *proposed*: host/VM não decide EGLFS ou Weston na Pi 5 física.
2. **ADR-004** permanece *proposed*: não implementar `/data` físico agora; testes de armazenamento no host podem preceder o projeto de partições.
3. **ADR-005** orienta vida do processo e desligamento; supervisão não é equivalente a interface saudável.
4. **ADR-006** continua contrato *proposed*: não inventar rotas/identidades, não simular integração ELO Server como pronta.
5. A licença `GPL-3.0-only` do código próprio do ELO/OS deve ser preservada; verificar compatibilidade/licenças das novas dependências e do eventual código do cliente ELO antes de copiar fontes entre repositórios.
6. Mudança de estado de ADR requer decisão e evidência, não resultado de compilação isolado.
7. Questões que dependem de energia, EEPROM, BCM2712, V3D/VC4, touchscreen, armazenamento físico e termal são **testes físicos futuros**; não criar PASS virtual para elas.

---

## 11. MODELO DO RELATÓRIO DA PR

```text
PR: feat(p2): portable offline client core and native Qt integration
Base: 02b7107 ou sucessor verificado
Compilador host: __________
Compilador ARM64: __________
Qt host: __________

P2-C0:    PASS / FAIL / NOT TESTED
P2-HGUI:  PASS / FAIL / NOT TESTED
P2-QGUI:  PASS / FAIL / NOT TESTED
P2-A64:   PASS / FAIL / NOT TESTED
P2-PI5:   NOT TESTED (intencional)

Comandos e logs: __________
Hashes: __________
Riscos não resolvidos: __________
O que a mudança não demonstra: __________
```

**NÃO dar merge** se o código altera um baseline histórico sem justificação, se a GUI anuncia `READY_LOCAL` sem conteúdo válido, se a rede é condição de boot, se o serviço sofre crash-loop não controlado, ou se há falha sem teste/report.

---

## 12. FECHO CAVEMAN

> **P1 PASSOU EM DUAS MÁQUINAS VIRTUAIS. A PI 5 AINDA NÃO FOI TESTADA.**  
> **NÃO PRECISAMOS PARAR O DESENVOLVIMENTO POR CAUSA DISSO.**  
> **O PRÓXIMO PRODUTO DEVE SER UMA CAPACIDADE DO CLIENTE, NÃO MAIS UMA CAMADA DO SO.**  
> **O NÚCLEO DECIDE. O QT APRESENTA. O ELO/OS DISPONIBILIZA. O SERVIDOR PUBLICA.**  
> **SEM TESTE, NÃO HÁ PASS. SEM CONTEÚDO REAL, NÃO HÁ READY_LOCAL.**  
> **FAÇA SIMPLES. DEPOIS DEIXE MAIS LEVE. SEMPRE PRONTO. SEMPRE INCOMPLETO.**

---

## Histórico de versões

| Versão | Data | Mudança |
| --- | --- | --- |
| 0.1.0 | 2026-11-08 | Primeira ordem de implementação pós-P1: núcleo portátil, integração Qt, virtualização gráfica isolada, portas de confiabilidade e diferenciação explícita de gates físicos. |
