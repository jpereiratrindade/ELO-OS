---
document_id: ELO-OS-IMPL-001
title: "ELO/OS — Plano de execução Caveman Full: auditoria P1 e validação virtual no Fedora 44"
version: 0.1.0
status: action-required
created: 2026-11-08
system: ELO/OS
repository: https://github.com/jpereiratrindade/ELO-OS
repository_branch_baseline: main
repository_commit_baseline: be651aa
buildroot_version: 2026.08.1
host_target: "Fedora 44 / x86_64"
virtual_target: "QEMU system/aarch64 -machine virt (TCG)"
physical_target: "Raspberry Pi 5 / BCM2712 / aarch64"
related_documents:
  - ELO-OS-BASES-001_v0.1.0.md
  - ELO-CONSTITUTION-001_v0.2.0
principles:
  - "Faça simples. Depois deixe mais leve."
  - "Sempre pronto. Sempre incompleto."
---

# ELO/OS — Plano de execução **Caveman Full**

**Documento:** `ELO-OS-IMPL-001`  
**Versão do documento:** `v0.1.0`  
**Estado:** `ACTION REQUIRED` — diretriz para a equipe; **não** é relatório de execução concluída  
**Data:** 08/11/2026  
**Base de código observada:** `jpereiratrindade/ELO-OS`, commit inicial `be651aa` em `main`  
**Host:** Fedora 44, x86_64, em `~/dev/cpp/elo-os`  
**Alvos distintos:** Raspberry Pi 5 física e QEMU ARM64 `virt` virtual  
**Documento constitutivo:** `ELO-OS-BASES-001_v0.1.0.md`

> **FAÇA SIMPLES. DEPOIS DEIXE MAIS LEVE.**  
> **SEMPRE PRONTO. SEMPRE INCOMPLETO.**  
> **REGRA CAVEMAN:** fazer, medir, provar, registrar. Não anunciar como feito o que só foi planejado.

---

## 0. ORDEM PARA A EQUIPE — LEITURA DE 60 SEGUNDOS

**O QUE FAZER AGORA:**

1. **Preservar o build P1 da Pi 5**, que concluiu a produção da imagem `sdcard.img`. Nada de apagar `output/pi5` ou reconfigurar a árvore física para tentar iniciar no QEMU.
2. **Criar perfil ARM64 `virt` independente**, derivado de `qemu_aarch64_virt_defconfig` da **mesma** release Buildroot 2026.08.1.
3. **Compilar em `output/qemu-aarch64`**, de forma independente de `output/pi5`.
4. **Iniciar no QEMU do Fedora 44**, por serial, sem ambiente gráfico, com emulação TCG e disco descartável.
5. **Provar PID 1, login, identidade, kernel, filesystem e rede**, com logs reproduzíveis e evidências anexadas à documentação.
6. **Corrigir divergências de documentação e scripts** encontradas abaixo.
7. **Só então** avançar a DRM/KMS + Qt 6, após um boot virtual válido e testes físicos do Pi 5 em trilha separada.

**NÃO FAZER:** tentar iniciar `output/pi5/images/sdcard.img` com `qemu-system-aarch64 -M virt`; misturar `.config` e `output` de plataformas; apagar imagens; habilitar Qt, watchdog, armazenamento A/B ou SSH público por impulso; afirmar que o boot físico já foi demonstrado.

**DEFINIÇÃO DE SUCESSO DESTA RODADA:** o ELO/OS inicializa no QEMU ARM64 no Fedora 44, chega a login serial, identifica-se corretamente e tem as evidências mínimas salvas. Isso **não** comprova que a imagem Pi 5 inicializa em hardware real.

---

## 1. FATOS DEMONSTRADOS VS. HIPÓTESES

### 1.1. Demonstrado pelos comandos e logs locais fornecidos

| Observação | Evidência concreta | Interpretação permitida |
|---|---|---|
| Estrutura criada | 41 arquivos adicionados no commit `be651aa` | *Scaffold* versionado e publicado |
| Smoke estrutural | `PASS: integridade do scaffold e sintaxe shell` | Estrutura e sintaxe básicas passam |
| Ambiente mínimo do host | `doctor.sh`: git/make/gcc/g++/python3/etc. `OK` | Pré-requisitos básicos presentes; diagnóstico **não é completo** |
| Build Pi 5 | `make` encerrou e `sdcard.img` foi gerada | Construção P1 concluída **sem teste de boot** |
| Imagem | 159.384.064 bytes; `fdisk`: 311.297 setores | Imagem de ~152 MiB |
| Partição 1 | FAT, 32 MiB, setores 1–65536 | Conteúdo de boot |
| Partição 2 | tipo Linux, 120 MiB, setores 65537–311296 | Root filesystem |
| Root filesystem | `file rootfs.ext2`: `ext4 filesystem data` | Formato real ext4; `rootfs.ext4` é link para `rootfs.ext2` |
| Kernel | `Image`, ~24 MiB | Kernel ARM64 produzido |
| BusyBox | `/bin/busybox`, 862.656 bytes | Binário presente na árvore alvo |
| Init | `/sbin/init -> ../bin/busybox` | BusyBox será o PID 1 esperado **se** o kernel o iniciar |
| Getty | `console::respawn` e `tty1::respawn` | Configurações presentes; não são testes de login em execução |
| `cmdline.txt` Pi 5 | `root=/dev/mmcblk0p2 rootwait console=tty1 console=ttyAMA10,115200` | Boot configurado para microSD; console serial deve ser validado no hardware |
| Identidade | `/etc/elo-os-release`: nome e versão 0.1.0 | Arquivo inserido corretamente no rootfs |
| SHA-256 | `a858973142ea7d6560389ee71b14dfbad828bc940f944e7aa6682fef7c4f32fb` | Identificador da imagem P1 gerada nesta máquina |

### 1.2. Não demonstrado — não declarar concluído

- Boot físico e login real na Raspberry Pi 5.
- Boot virtual e login real no QEMU ARM64.
- Console serial físico `ttyAMA10` funcionando no cabo/pino usado.
- Rede funcional, acesso a servidor ELO, sincronização ou funcionamento offline.
- Qt/EGLFS/DRM/KMS, vídeo, aceleração GPU, touchscreen e câmera.
- Rootfs realmente montado **somente leitura** na execução.
- Partição persistente `/data`, tolerância à queda de energia, watchdog ou rollback.
- Reprodutibilidade binária bit a bit, segurança de inicialização ou garantia de atualização.

### 1.3. Registro obrigatório de estado

Propor o seguinte vocabulário no projeto e nos testes:

```text
PROPOSED       = decidido conceitualmente, sem implementação
SCAFFOLDED     = arquivos e estrutura presentes
BUILT          = build concluído, artefatos identificáveis
BOOTED_QEMU    = Linux iniciou na máquina virtual ARM64
BOOTED_PI5     = Linux iniciou na Raspberry Pi 5 física
VERIFIED       = testes e evidências do comportamento aprovados
PRODUCTION     = bloqueado até requisitos operacionais homologados
```

**Estado correto hoje:** `BUILT` para o perfil Pi 5; `PROPOSED` para o perfil QEMU. `BOOTED_QEMU` e `BOOTED_PI5` permanecem pendentes.

---

## 2. DECISÃO FUNDAMENTAL — DUAS PLATAFORMAS, UMA BASE

```text
                           REPOSITÓRIO elo-os
                                  |
                         br2-external ELO_OS
                                  |
               +------------------+------------------+
               |                                     |
      elo_pi5_defconfig                 elo_qemu_aarch64_defconfig
               |                                     |
        output/pi5/                         output/qemu-aarch64/
               |                                     |
       Kernel BCM2712                        Kernel ARM64 virt
       Firmware RPi                           VirtIO/PL011
       root mmcblk0p2                        root vda
       boot SD/EEPROM                         QEMU -M virt
               |                                     |
      RASPBERRY PI 5                         FEDORA 44 (x86_64)
       TESTE FÍSICO                          TESTE VIRTUAL (TCG)
```

**Por quê?** A máquina `virt` é uma placa virtual genérica; não emula o firmware de boot, a GPU V3D/VC4 nem os periféricos BCM2712 da Pi 5. A documentação do QEMU lista modelos Raspberry Pi até a Pi 4; não usar `raspi5` como pressuposto sem verificar o QEMU instalado. No Fedora x86_64 executando convidado AArch64, usar **TCG**, não presumir aceleração KVM.

**O que é compartilhável:** identidade de sistema, política de inicialização, serviços POSIX, interfaces da aplicação, teste de rede, persistência lógica e contratos. **O que não se confunde:** DTB, kernel config, driver gráfico, controlador de armazenamento, firmwares, parâmetros de console e desempenho.

---

## 3. MATRIZ DE AÇÕES DA EQUIPE — POR PRIORIDADE

| ID | Prioridade | Ação | Arquivos alvo | Pronto quando |
|---|---|---|---|---|
| T-001 | **P0** | Criar `elo_qemu_aarch64_defconfig` baseada na release fixada | `configs/` | Perfil carrega com Kconfig sem conflito |
| T-002 | **P0** | Criar build QEMU independente, reusar fontes quando seguro | `scripts/build.sh`, `scripts/build-qemu.sh` | Build QEMU conclui sem alterar `output/pi5` |
| T-003 | **P0** | Criar execução QEMU por serial e disco descartável | `scripts/run-qemu.sh` | Login aparece no terminal Fedora |
| T-004 | **P0** | Testar `init`, getty, rootfs, identidade e rede | `tests/qemu/`, `docs/tests/` | Evidências demonstram Linux inicializado |
| T-005 | **P0** | Atualizar relatório e README: P1 compilado, boot pendente | `README.md`, `docs/tests/acceptance.md` | Sem afirmações contraditórias |
| T-006 | **P0** | Capturar inventário e hashes do build P1 | `scripts/inspect-image.sh`, `docs/evidence/` | SHA, partições e metadados arquivados |
| T-007 | **P1** | Separar overlay de identidade comum do hardware Pi 5 | `board/elo/common/`, `board/elo/pi5/` | `/etc/elo-os-release` entra em ambos os alvos |
| T-008 | **P1** | Corrigir diagnósticos do host e verificações de dependências | `scripts/doctor.sh` | Falta de QEMU/build depende claramente identificada |
| T-009 | **P1** | Auditar alinhamento da imagem `sdcard.img` | `board/raspberrypi5/` upstream; proposta `board/elo/pi5/` | Partições analisadas e decisão explicitada |
| T-010 | **P1** | Auditar kernel cmdline, getty e console serial/HDMI | configurações Pi e QEMU | Cada plataforma usa seu console adequado |
| T-011 | **P1** | Formalizar rootfs RO e `/data`, ainda **não** implementados | ADR-004; future genimage | Não haver promessa incorreta no README |
| T-012 | **P1** | Acrescentar CI estrutural + teste de configuração QEMU | `.github/workflows/` | Evidência em CI; não simular boot que não foi executado |
| T-013 | **P2** | Planejar/validar Qt6/EGLFS no **hardware**, separadamente de QEMU | `package/elo-client`, ADR-002 | Mecanismo gráfico escolhido com ensaio real |
| T-014 | **P2** | Atualização A/B, segurança, watchdog, idempotência e ELO Server | docs/ADR e implementação futura | Manter bloqueado até especificação e testes |

**Regra de integração:** cada tarefa deve referenciar um issue, um commit, um teste e uma evidência ou declaração explícita de limitação.

---

## 4. INSTRUÇÕES OPERACIONAIS — FEDORA 44 + QEMU AARCH64

A seção abaixo é **um roteiro para executar/testar**, não uma alegação de que esses comandos já rodaram. Deve ser reproduzida pela equipe e refinada para scripts idempotentes.

### 4.1. Host: inspecionar antes de instalar

```bash
cd ~/dev/cpp/elo-os
uname -m
cat /etc/fedora-release
command -v qemu-system-aarch64 || true
qemu-system-aarch64 --version 2>/dev/null || true
findmnt -T .
df -h .
```

**Esperado:** Fedora 44 x86_64 e `qemu-system-aarch64` disponível ou ausente com erro explícito. O pacote correspondente no Fedora 44 é `qemu-system-aarch64-core`.

Se ausente, instalar **no host**, não dentro de uma imagem ELO/OS:

```bash
sudo dnf install qemu-system-aarch64-core
```

Não instalar `qemu-system-aarch64` como serviço no convidado: QEMU é o **emulador que roda no Fedora**. Não exigir `virt-manager`, libvirt, UEFI ou desktop para o primeiro teste Linux de console.

### 4.2. Conferir a release Buildroot usada no primeiro build

```bash
cd ~/dev/cpp/elo-os
BR="$PWD/.cache/buildroot-2026.08.1"
test -f "$BR/configs/qemu_aarch64_virt_defconfig"
git -C "$BR" describe --tags --always
```

Se o caminho estiver ausente, a equipe deverá parar e verificar `scripts/build.sh` e `BUILDROOT_DIR`, em vez de misturar duas releases. A configuração `qemu_aarch64_virt_defconfig` oficial da versão 2026.08.1 usa kernel 6.18.7 e configuração em `board/qemu/aarch64-virt/linux.config` — **não** a configuração BCM2712 da Pi 5.

### 4.3. Criar perfil de configuração QEMU **a partir da fonte oficial**

```bash
cd ~/dev/cpp/elo-os
BR="$PWD/.cache/buildroot-2026.08.1"
cp "$BR/configs/qemu_aarch64_virt_defconfig" \
  configs/elo_qemu_aarch64_defconfig

# O script post-image upstream gera start-qemu.sh para nomes oficiais qemu_*;
# nossa configuração customizada terá script de execução próprio.
sed -i \
  -e '/^BR2_ROOTFS_POST_IMAGE_SCRIPT=/d' \
  -e '/^BR2_ROOTFS_POST_SCRIPT_ARGS=/d' \
  -e '/^BR2_PACKAGE_HOST_QEMU=/d' \
  -e '/^BR2_PACKAGE_HOST_QEMU_SYSTEM_MODE=/d' \
  configs/elo_qemu_aarch64_defconfig

cat >> configs/elo_qemu_aarch64_defconfig <<'CFG'
# ELO/OS QEMU ARM64 P1 — teste de console; sem Qt.
BR2_TARGET_GENERIC_HOSTNAME="elo-os-qemu"
BR2_TARGET_GENERIC_GETTY_PORT="ttyAMA0"
# Compartilhamento provisório do overlay já existente.
# T-007 deverá movê-lo para board/elo/common/ e atualizar ambos os perfis.
BR2_ROOTFS_OVERLAY="$(BR2_EXTERNAL_ELO_OS_PATH)/board/elo/pi5/rootfs-overlay"
CFG
```

**Nota de governança:** o overlay `board/elo/pi5/rootfs-overlay` é compartilhado **provisoriamente** só porque contém os arquivos de identificação existentes. O desenho final deve mover o conteúdo comum para `board/elo/common/rootfs-overlay` e reservar `board/elo/pi5/` a personalizações físicas da Raspberry Pi. Não fazer `git mv` sem atualizar a defconfig física na mesma alteração.

### 4.4. Configurar e compilar sem interferir no perfil físico

```bash
cd ~/dev/cpp/elo-os
ROOT="$PWD"
BR="$ROOT/.cache/buildroot-2026.08.1"
OUT="$ROOT/output/qemu-aarch64"

# Não reutilizar output/pi5 ou sua .config.
make -C "$BR" O="$OUT" BR2_EXTERNAL="$ROOT" \
  elo_qemu_aarch64_defconfig

# Registrar logs, preservando o código de saída em caso de erro.
set -o pipefail
make -C "$BR" O="$OUT" BR2_EXTERNAL="$ROOT" -j8 \
  2>&1 | tee "$ROOT/qemu-build.log"

# Verificar artefatos antes de tentar executar.
ls -lh "$OUT/images/Image" "$OUT/images/rootfs.ext4"
file "$OUT/images/rootfs.ext4"
```

`qemu-build.log` deverá ir para um diretório de evidências local ignorado pelo Git, ou ser removido após extração de sumário saneado; não subir logs com dados confidenciais. **Não prometer compilação rápida:** a configuração QEMU tem kernel/toolchain diferentes, podendo recompilar componentes apesar de downloads compartilhados.

**Melhoria estrutural obrigatória (T-002):** criar `scripts/build-qemu.sh` ou generalizar `scripts/build.sh` para um argumento `--target pi5|qemu-aarch64`, sem default silencioso perigoso. Manter `.config`, builds e diretório de saída exclusivos por alvo. Compartilhar `dl/` apenas como cache de downloads, quando configurado corretamente.

### 4.5. Executar em QEMU com uma cópia descartável do rootfs

```bash
cd ~/dev/cpp/elo-os
OUT="$PWD/output/qemu-aarch64"
mkdir -p "$OUT/run"

# Nunca usar a imagem de build diretamente como disco de VM gravável.
cp -L --reflink=auto "$OUT/images/rootfs.ext4" \
  "$OUT/run/rootfs-test.ext4"

qemu-system-aarch64 \
  -machine virt \
  -cpu cortex-a53 \
  -accel tcg \
  -m 1024 \
  -smp 2 \
  -nographic \
  -kernel "$OUT/images/Image" \
  -append 'rootwait root=/dev/vda console=ttyAMA0' \
  -netdev user,id=net0 \
  -device virtio-net-device,netdev=net0 \
  -drive "file=$OUT/run/rootfs-test.ext4,if=none,format=raw,id=hd0" \
  -device virtio-blk-device,drive=hd0
```

**Resultado esperado:** mensagens do kernel na saída padrão, inicialização do PID 1 BusyBox e prompt de login serial. Para sair do QEMU em modo `-nographic`, em geral usar **Ctrl+A, depois X**; preferir desligamento limpo dentro do convidado quando possível.

**Limitações importantes:**

- `-machine virt` não inicia o firmware real do Pi 5.
- `-append` usa `root=/dev/vda`, não `/dev/mmcblk0p2`.
- `ttyAMA0` é o console serial do modelo `virt`, não `ttyAMA10` do perfil físico.
- TCG emula instruções ARM64 em CPU host x86_64, portanto tempos de boot **não** são benchmarks da Pi 5.
- QEMU user-mode networking cria uma rede NAT isolada; não expor portas ou habilitar SSH apenas para facilitar a prova de boot.
- Problemas gráficos no QEMU não permitem concluir que a GPU V3D/VC4 da Pi 5 falha ou funciona.

### 4.6. Diagnóstico dentro do convidado QEMU

Depois do login:

```sh
cat /etc/elo-os-release
uname -a
cat /proc/cmdline
cat /proc/1/comm
readlink /sbin/init
cat /etc/inittab
mount
df -h
ip link 2>/dev/null || ifconfig -a
ls -l /dev/vda
```

A presença de `/dev/vda` e do argumento `console=ttyAMA0` é parte do contrato virtual. O arquivo `/etc/elo-os-release` deve identificar ELO/OS. **O processo `/proc/1/comm` esperado é `init`/BusyBox conforme a configuração**, não um daemon particular do ELO. Se algum utilitário estiver ausente, registrar e avaliar necessidade antes de adicionar pacote.

### 4.7. Rede — ensaio mínimo, sem confundir IP com serviço ELO

Usar QEMU com `-netdev user` e placa virtio como na linha acima. Registrar a interface recebida, configuração DHCP e uma conexão **apenas para destino de teste controlado**. Uma interface `UP` ou IP recebido não prova que TLS, autenticação, DNS ou o ELO Server estejam prontos.

### 4.8. Validação de saída e evidência

```bash
cd ~/dev/cpp/elo-os
sha256sum output/pi5/images/sdcard.img
sha256sum output/qemu-aarch64/images/Image \
          output/qemu-aarch64/images/rootfs.ext4

git status --short
```

Gerar `docs/evidence/P1-PI5-BUILD-20261108.md` (metadados e hashes) e `docs/evidence/P1-QEMU-BOOT-<data>.md` **somente após executar** o teste virtual. Não publicar o disco de teste, caches, imagens volumosas nem dados privados no repositório de código.

---

## 5. OBSERVAÇÕES TÉCNICAS A CORRIGIR NO PERFIL PI 5

### 5.1. O build passou, mas o boot físico permanece aberto

O `make` executou o script oficial `board/raspberrypi5/post-image.sh`, escreveu `boot.vfat`, `rootfs.ext4` e `sdcard.img`. **Não modificar esses hooks upstream sem motivo demonstrado**. A equipe deve primeiro testar o boot físico com microSD de testes e periféricos mínimos, preservando cópia e checksum do artefato original.

### 5.2. Alinhamento das partições

`fdisk -l` fornecido:

```text
sdcard.img: 159384064 bytes, 311297 setores de 512 bytes
partição 1: LBA 1       até 65536  (32 MiB, FAT)
partição 2: LBA 65537   até 311296 (120 MiB, Linux)
```

**Achado:** partições começam em setores 1 e 65537, sem alinhamento convencional de 1 MiB (2048 setores). Tratar como **dívida técnica observável**, não afirmar corrupção. Abrir T-009 para auditar `output/pi5/images/genimage.cfg`, comparar com o *upstream* e propor alinhamento, medindo diferenças antes/depois. Testar boot na Pi 5 antes de promover a alteração. Não executar `fdisk` de edição na imagem original.

### 5.3. Nomes dos arquivos e filesystem real

O arquivo `rootfs.ext2` contém filesystem **ext4** segundo `file`, e `rootfs.ext4` é link simbólico para ele. Não tratar isso como erro de corrupção: o Buildroot usa a família de geração ext2 com formato ext4 habilitado. Documentar o formato real e usar comandos que seguem links corretamente.

### 5.4. Console de boot e getty

**Kernel, Pi 5:**

```text
root=/dev/mmcblk0p2 rootwait console=tty1 console=ttyAMA10,115200
```

**Configuração do Buildroot:**

```text
BR2_TARGET_GENERIC_GETTY=y
BR2_TARGET_GENERIC_GETTY_PORT="console"
BR2_TARGET_GENERIC_GETTY_BAUDRATE_KEEP=y
```

**`/etc/inittab` observado:**

```text
console::respawn:/sbin/getty -L  console 0 vt100
 tty1::respawn:/sbin/getty -L  tty1 0 vt100
```

**Conclusão válida:** há getty configurado para o console genérico e para o terminal HDMI. **Ainda não sabemos** se a serial exposta como `ttyAMA10` corresponde ao cabeamento/porta física de depuração escolhidos; isso exige um ensaio separado com pinagem e hardware corretos. Para QEMU usar `ttyAMA0` na configuração própria.

### 5.5. Rootfs de produção e `/data`

O rootfs ext4 gerado em P1 não prova montagem em modo **somente leitura**, e o `fdisk` atual mostra **somente duas partições**, sem `/data` independente. A diretriz constitutiva prevê:

```text
boot controlado + rootfs RO + /data RW + /run /tmp tmpfs
```

Esse desenho permanece **proposta**, não implementação. Não implementar uma terceira partição às pressas antes de validar o primeiro boot. Depois dos ensaios, especificar criação da partição, montagem, `fstab`/init, permissões, ciclo de atualização e teste de queda de energia.

### 5.6. Configuração do firmware

O `config.txt` observado é um exemplo genérico e inclui `kernel=Image`. Isto é válido para o build inicial, mas não é uma garantia de configuração ótima. Auditar configuração de HDMI, vídeo, touchscreen, watchdog e Device Tree overlays **a partir de necessidades reais**, não habilitar opções por conjectura.

### 5.7. Tamanho de imagem não é RAM consumida

`sdcard.img` usa ~152 MiB de **espaço em disco**; rootfs tem capacidade de 120 MiB, não necessariamente 120 MiB de dados. Não confundir com RAM, tempo de boot, consumo de energia ou desempenho da UI. Métricas só após iniciar o convidado/hardware.

---

## 6. CORREÇÕES DE GOVERNANÇA E AUTOMAÇÃO

### 6.1. README e acceptance

O `README.md` consultado ainda se apresenta como `design-candidate / scaffold` e afirma não haver build executado. `docs/tests/acceptance.md` também marca P1 como pendente. Corrigir para **distinguir marcos**:

```text
P1-A  Estrutura/sintaxe         PASS (2026-11-08)
P1-B  Compilação imagem Pi 5    PASS (2026-11-08)
P1-C  Boot QEMU ARM64 virt      PENDING
P1-D  Boot físico Raspberry Pi 5  PENDING
P1-E  30 boot cycles físicos   PENDING
P2    Qt/DRM/KMS               PENDING
P3    ELO Server/Client        PENDING
P4    Confiabilidade           PENDING
P5    Updates recuperáveis     PENDING
```

**Cuidado com P0 original:** o marco `P0` previsto no documento-base para experimentos com Raspberry Pi OS Lite não foi comprovado na conversa. Não o marcar como concluído retroativamente apenas porque P1 compilou.

### 6.2. `doctor.sh`

Hoje verifica ferramentas elementares, mas **não** a presença de `qemu-system-aarch64`, memória, espaço, release de host, checksum das fontes ou toolchain. Expandir com níveis:

- `doctor --target pi5`: ferramentas do Buildroot, disponibilidade de disco, fonte Buildroot fixada.
- `doctor --target qemu`: tudo acima + QEMU e sua versão, arquitetura do host e disponibilidade de TCG.
- `doctor --target graphics`: em momento posterior, testes de EGL/DRM e dependências de Qt.

Exibir `PASS`, `WARN` ou `FAIL` com motivo e comando de correção. Não instalar pacotes automaticamente sem consentimento.

### 6.3. `build.sh`

Atualmente fixa `VERSION=2026.08.1`, `JOBS=8` e `OUT_DIR=output/pi5`. É correto para a primeira imagem, mas inadequado para perfis múltiplos sem parametrização.

**Contrato a implementar:**

```text
./scripts/build.sh --target pi5 --jobs 8
./scripts/build.sh --target qemu-aarch64 --jobs 8
./scripts/doctor.sh --target qemu-aarch64
./scripts/run-qemu.sh --target qemu-aarch64
```

Pode-se inicialmente criar `build-qemu.sh` separado, antes de refatorar. Mais importante que unificar o script é **nunca compartilhar o mesmo diretório `O=` entre duas plataformas**. Preservar cache de downloads sempre que seguro; registrar qual configuração e release geraram cada build.

### 6.4. `inspect-image.sh`

Hoje lista arquivos e calcula hash do `sdcard.img` físico. Estender para `--target pi5|qemu-aarch64`, com existência, `file`, tamanho, SHA-256, partições (apenas Pi 5), kernel e versão do Buildroot. Para QEMU, **não exigir** `sdcard.img`: o perfil inicial usa `Image` + `rootfs.ext4` diretamente.

### 6.5. Smoke test e GitHub Actions

O smoke atual verifica existência de arquivos, sintaxe shell e algumas strings. **Não testa configuração Kconfig, build, boot, rede ou privacidade.** Não anunciar CI verde como sistema homologado.

Acrescentar testes automáticos sem hardware:

- Configuração de ambos os perfis sem interferência em `O=`.
- Falha explícita quando faltam scripts ou configurações.
- Verificação de formato dos arquivos `.md` e dos scripts shell.
- Teste QEMU em ambiente de CI **somente se configurado com timeout, artefatos e recursos adequados**, sem exigir GPU real.
- Comparação de hashes com inventários e detecção de segredos em arquivos a publicar.

**Segurança CI:** revisar *pinning* das actions, permissões mínimas de token, proveniência de dependências e tratamento de artefatos de build.

---

## 7. REQUISITOS DE TESTE — MATRIZ DE EVIDÊNCIAS

| ID teste | Plataforma | Ação | Condição de aceite | Artefato/evidência |
|---|---|---|---|---|
| Q-001 | Host | Verificar Fedora 44 e QEMU AArch64 | Binário presente e versão registrada | `host-info.txt` |
| Q-002 | Buildroot | Carregar defconfig QEMU | `.config` coerente com AArch64 virt | `defconfig-diff.txt` |
| Q-003 | Buildroot | Compilar QEMU sem tocar Pi 5 | `Image` e `rootfs.ext4` presentes | `qemu-build-summary.md`, hashes |
| Q-004 | QEMU | Boot serial | Prompt de login alcançado | `qemu-boot.log` saneado |
| Q-005 | QEMU | PID 1 | BusyBox init funcional, sem panic | comandos `/proc` + log |
| Q-006 | QEMU | Identidade | `/etc/elo-os-release` aponta 0.1.0 | transcrição do convidado |
| Q-007 | QEMU | Armazenamento | `/dev/vda` montado e legível | `mount`, `df`, `/proc/cmdline` |
| Q-008 | QEMU | Rede | Interface virtio detectada; DHCP verificado | `ip`/`ifconfig`; log sem segredos |
| Q-009 | QEMU | Reinício/desligamento | Reinicia ou desliga sem falhas detectadas | log e saída |
| Q-010 | QEMU | Disco descartável | Imagem de build original não é alterada | hash antes/depois do rootfs base |
| P-001 | Pi 5 | Boot físico | Console HDMI ou serial operacional | foto/transcrição datada |
| P-002 | Pi 5 | 30 boots | Ausência de intervenções em 30 ciclos | planilha/log de ensaio |
| P-003 | Pi 5 | Alimentação/armazenamento | Perfil físico estável | evidência de testes |
| P-004 | Pi 5 | GPU/touch | Só no P2 | relatório específico |

**Sem provas, marcar `NOT TESTED`, nunca `PASS` por inferência.** Capturas e logs não podem conter credenciais, dados pessoais ou imagens biométricas.

---

## 8. CONDIÇÕES DE FALHA E DIAGNÓSTICO — NÃO IMPROVISAR

| Sintoma | Hipótese a verificar | Ação permitida |
|---|---|---|
| QEMU `Could not open ... Image` | Perfil QEMU não compilou ou caminho errado | Conferir `output/qemu-aarch64/images` |
| QEMU kernel panic VFS | `root=/dev/vda`, virtio-blk ou ext4 ausentes no kernel | Conferir kernel config e comando; **não** usar kernel Pi 5 |
| Kernel inicia, sem login | Getty/console `ttyAMA0` divergentes | Conferir `.config`, `/etc/inittab`, `-append` |
| Sem `/dev/vda` | Virtio-blk não configurado ou drive não associado | Conferir dispositivos QEMU, drivers e rootfs |
| Falha de DHCP | Interface, driver de rede ou BusyBox udhcpc | Registrar interfaces e logs; não supor falha do ELO Server |
| Emulação lenta | TCG em x86_64 sem KVM ARM64 | Aceitar custo e medir; não ajustar kernel às cegas |
| Build QEMU modifica Pi 5 | `O=` compartilhado ou script de perfil errado | Bloquear merge e separar saídas |
| GUI falha no QEMU | Ausência de virtio-gpu/aceleração/Qt | Tratar como estudo virtual; não inferir falha da GPU Pi 5 |
| `sdcard.img` não boota na Pi 5 | Bootloader, microSD, HDMI, DTB, fonte ou cmdline | Testar fisicamente sem reformatar outros discos |

**PROIBIÇÕES:** não desligar SELinux do Fedora como solução genérica, não executar `dd` sem confirmar destino, não montar imagens graváveis sem necessidade, não destruir `output/pi5`, não desabilitar validação TLS para corrigir relógio/rede.

---

## 9. DIREÇÃO DE ARQUITETURA DEPOIS DO PRIMEIRO BOOT

### 9.1. `rootfs` de leitura e estado mutável

Depois da prova de boot, desenvolver o layout `boot + rootfs RO + /data RW` com inicialização independente da rede, `/run` e `/tmp` em tmpfs, e estratégia clara para falha de energia. O QEMU poderá testar **lógica POSIX e montagem**, mas a validação de mídia física e power loss deverá ocorrer na Pi 5.

### 9.2. Gráficos

Na Pi 5, investigar diretamente **DRM/KMS + Mesa/EGL/GBM + Qt6/EGLFS**; alternativa mínima Weston/Wayland somente se necessária. No QEMU, um perfil **gráfico separado** poderá usar `virtio-gpu` como teste de interface e fluxo, mas **não será substituto de driver V3D/VC4 nem prova de desempenho**.

### 9.3. ELO Server e ELO Thin Client

Continuar preservando o contrato constitutivo:

```text
ELO Server:     publica e coordena com segurança
ELO Thin Client: recebe, valida, apresenta e persiste o necessário
ELO/OS:         inicializa, protege, disponibiliza e recupera
```

O P1 **não** implementa protocolo HTTPS de conteúdo, idempotência ou sessão ELO. Quando chegar o P3, tratar manifestos imutáveis, chaves idempotentes e fallback offline como comportamentos a testar separadamente.

### 9.4. Privacidade e segurança

Identidade de dispositivo não é identidade de pessoa. Sem segredos embutidos em imagem pública; sem SSH externo por padrão; não coletar frames/biometria pela camada de SO. Watchdog e atualização A/B somente depois de testes de recuperação. Não chamar o sistema de seguro ou confiável só porque a VM iniciou.

---

## 10. PROPOSTA DE ORGANIZAÇÃO DO REPOSITÓRIO (SEM GERAR ARQUIVOS FANTASMA)

```text
elo-os/
├── configs/
│   ├── elo_pi5_defconfig                 # EXISTE
│   └── elo_qemu_aarch64_defconfig        # CRIAR (T-001)
├── board/elo/
│   ├── common/rootfs-overlay/            # PROPOSTO (T-007)
│   └── pi5/                              # EXISTE; hardware específico
├── docs/
│   ├── ELO-OS-BASES-001_v0.1.0.md        # EXISTE
│   ├── ELO-OS-IMPL-001_v0.1.0.md         # ESTE DOCUMENTO
│   ├── adr/                              # EXISTE
│   ├── evidence/                         # CRIAR (relatórios pequenos)
│   └── tests/acceptance.md               # ATUALIZAR
├── scripts/
│   ├── build.sh                          # EXISTE; evoluir
│   ├── doctor.sh                         # EXISTE; evoluir
│   ├── inspect-image.sh                  # EXISTE; evoluir
│   └── run-qemu.sh                       # CRIAR
├── tests/
│   ├── smoke.sh                          # EXISTE
│   └── qemu/                             # CRIAR
├── .cache/buildroot-2026.08.1/          # GERADO/IGNORADO
├── output/pi5/                           # GERADO/IGNORADO
└── output/qemu-aarch64/                  # GERADO/IGNORADO
```

**Importante:** os caminhos `board/elo/common`, `scripts/run-qemu.sh` e `configs/elo_qemu_aarch64_defconfig` são **tarefas para a equipe**, não arquivos já existentes no commit inicial. Nenhuma saída gerada vai para o Git por padrão; registrar somente hashes, versões, configurações e sumários sem segredos.

---

## 11. CRITÉRIO DE CONCLUSÃO DA PRÓXIMA ENTREGA

A equipe só poderá anunciar **“ELO/OS P1-QEMU validado”** se entregar, juntos:

- [ ] Novo perfil QEMU derivado do Buildroot 2026.08.1, com diferenças documentadas.
- [ ] Build QEMU isolado do build Pi 5; hashes de ambos os conjuntos.
- [ ] Comando/script idempotente de inicialização QEMU documentado.
- [ ] Log e evidência de login serial ARM64, PID 1, rootfs e identificação do ELO/OS.
- [ ] Teste de integridade do disco base após executar convidado com cópia descartável.
- [ ] Registro da interface de rede e seu comportamento, sem alegar integração ELO Server.
- [ ] Atualização do README e do acceptance sem contradições de estado.
- [ ] Testes `smoke.sh` e revisão shell/Kconfig passando.
- [ ] Ausência de senhas, certificados privados, dados pessoais e imagens grandes no commit.
- [ ] Relatório com **o que funcionou, o que falhou e o que permanece desconhecido**.

**A aceitação física Raspberry Pi 5 permanece separada.** A equipe não poderá transferir `PASS` do QEMU para o hardware.

---

## 12. ENTREGA À EQUIPE — INSTRUÇÃO OPERACIONAL

**Issue/PR sugerido:** `feat(p1): validação ARM64 QEMU virt e auditoria do primeiro build ELO/OS`.

**Descrição para o PR:**

> Implementar perfil de plataforma ARM64 virtual independente da imagem física Raspberry Pi 5, com Buildroot 2026.08.1, execução serial em QEMU sobre Fedora 44, testes e evidências. Corrigir a documentação para distinguir `BUILT`, `BOOTED_QEMU` e `BOOTED_PI5`, sem prometer recursos gráficos, persistência RO, recuperação ou servidor ELO antes de comprovação. Preservar imutavelmente o build P1 e seus hashes.

**Merge somente mediante:** revisão de arquivos alterados, `smoke` e testes do novo perfil, evidência de boot real em QEMU, checksums, e aprovação da matriz de estado.

**Não atualizar versão de produto automaticamente:** este documento é `v0.1.0`; o software continua na versão `0.1.0` até decisão de release. Evitar registrar tag antes da evidência.

---

## 13. REFERÊNCIAS PRIMÁRIAS E RASTREABILIDADE

### Evidência local do trabalho

- Commit criado/push no repositório do usuário: `be651aa` (`chore: bootstrap ELO-OS v0.1.0`).
- Relatórios de terminal de 08/11/2026: compilação bem-sucedida, `fdisk`, `sha256sum`, `file`, `cmdline.txt`, `config.txt`, `elo-os-release`, `inittab`, `BusyBox` e `init`.
- SHA-256 de `sdcard.img`: `a858973142ea7d6560389ee71b14dfbad828bc940f944e7aa6682fef7c4f32fb`.
- Documento-base: `docs/ELO-OS-BASES-001_v0.1.0.md`.

### Referências técnicas verificadas (08/11/2026)

- Buildroot 2026.08.1 `configs/qemu_aarch64_virt_defconfig`: https://github.com/buildroot/buildroot/blob/2026.08.1/configs/qemu_aarch64_virt_defconfig
- Buildroot 2026.08.1 `board/qemu/aarch64-virt/readme.txt`: https://github.com/buildroot/buildroot/blob/2026.08.1/board/qemu/aarch64-virt/readme.txt
- Manual Buildroot — `br2-external` e configuração: https://buildroot.org/downloads/manual/manual.html
- Documentação oficial QEMU ARM (máquinas suportadas): https://www.qemu.org/docs/master/system/target-arm
- QEMU Raspberry Pi board models: https://www.qemu.org/docs/master/system/arm/raspi
- Pacote Fedora `qemu-system-aarch64-core`: https://packages.fedoraproject.org/pkgs/qemu/qemu-system-aarch64-core/
- Projeto ELO/OS: https://github.com/jpereiratrindade/ELO-OS
- Constituição ELO: https://github.com/jpereiratrindade/ELO/blob/main/docs/constitution/ELO-CONSTITUTION-001.md

**Critério de documentação:** se o código mudar, atualizar o estado do documento e vincular o commit. Não alterar fatos observados para fazer o relatório parecer mais completo.

---

## 14. FECHO CAVEMAN

> **O Linux foi compilado. Não significa que já iniciou.**  
> **A VM pode provar o software genérico. Não prova o hardware Pi 5.**  
> **O Buildroot monta o sistema. O kernel executa. O BusyBox inicia. O ELO apresenta.**  
> **Não otimizar o que ainda não medimos. Não proclamar o que ainda não verificamos.**
>
> **FAÇA SIMPLES. DEPOIS DEIXE MAIS LEVE.**  
> **SEMPRE PRONTO. SEMPRE INCOMPLETO.**

---

## Histórico de versões

| Versão | Data | Mudança |
|---|---|---|
| `0.1.0` | 2026-11-08 | Plano de execução da equipe; auditoria das evidências P1, separação de perfis físicos/virtuais, guia Fedora 44 + QEMU ARM64, prioridades, testes e critérios de aceite. |
