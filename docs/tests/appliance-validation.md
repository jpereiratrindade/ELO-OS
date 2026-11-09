# Appliance virtual — fundação I1

Esta bancada implementa a primeira etapa do [plano integral](../ELO-OS-IMPL-003_v0.1.0.md). Os perfis `qemu-x86_64-appliance` e `qemu-aarch64-appliance` têm saídas independentes dos perfis de console e gráficos P2. Não gravam mídia física. Contrato de distribuição e integração real com ELO Server ainda serão definidos; a apresentação permanece a fixture local incorporada.

## Compilação no Silverblue

Use a Toolbox `elo-os` e as dependências do [roteiro desktop](desktop-validation.md). Dentro dela, a partir da raiz do checkout:

```bash
export PROFILE=qemu-x86_64-appliance
export OUTPUT_DIR="$PWD/output/toolbox/$PROFILE"
export JOBS=32
./scripts/doctor.sh
./scripts/build.sh
./scripts/inspect-image.sh
```

Para ARM64, troque `PROFILE` por `qemu-aarch64-appliance` e derive novamente `OUTPUT_DIR`. Duas compilações simultâneas neste desktop usam 16 jobs cada, totalizando 32. Nunca execute dois builds, ou build e VM, no mesmo diretório de saída. Não transporte toolchains Buildroot entre caminhos absolutos.

## Disco de dados e execução

Após o build terminar com código zero, no mesmo ambiente:

```bash
./scripts/create-data-image.sh
./scripts/run-qemu.sh
```

O primeiro comando cria um **arquivo novo** `data.ext4` de 128 MiB, ext4 rotulado `ELO_DATA`. Não substitui arquivo ou symlink existente e não formata dispositivo físico. `DATA_SIZE_MIB=32` até `4096` ajusta o tamanho. `QEMU_DATA_IMAGE=/caminho/novo.ext4` escolhe outro arquivo; informe a mesma variável ao launcher e aos testes gráficos para usá-lo.

O launcher mantém snapshot do disco de sistema e conecta o disco de dados sem snapshot. Escritas usuais na raiz são recusadas no convidado. `/data` persiste entre sessões; o launcher recusa conectar como dados o próprio kernel ou rootfs. O convidado nunca formata um volume e aceita somente `/dev/vdb` ext4 com o rótulo esperado e layout reconhecido. Para ausência deliberada: `QEMU_DATA=off ./scripts/run-qemu.sh`.

Login serial de desenvolvimento: `root`, sem senha. `poweroff` encerra a sessão. Em outra sessão, confirme:

```sh
cat /etc/elo-build.json
cat /run/elo-storage/status
cat /proc/mounts
cat /run/elo-client/health
```

`/etc/elo-build.json` identifica perfil, configuração, Buildroot, commit e hashes dos arquivos de entrada. O indicador `source_dirty` explicita builds anteriores ao commit. O ID de fonte/configuração não promete reprodução byte a byte do filesystem; registre também os hashes dos artefatos finais.

## Validação automatizada

Execute sequencialmente por perfil, depois do build. Arquivos de teste adicionais são criados apenas no diretório de saída:

```bash
python3 tests/client/qemu-gui-smoke.py
QEMU_GUI_NETWORK=user python3 tests/client/qemu-gui-smoke.py
QEMU_DATA=off QEMU_STORAGE_EXPECT=UNAVAILABLE python3 tests/client/qemu-gui-smoke.py
python3 tests/recovery/appliance-smoke.py
```

Os três ensaios gráficos exigem apresentação antes da rede, raiz RO, estado de armazenamento coerente, teclado, frames, recuperação após SIGKILL/SIGSTOP do cliente e desligamento. O segundo derruba/restaura o link; o terceiro exige apresentação sem `/data` e recusa de escrita alternativa na raiz.

Relatórios gráficos: `gui-smoke.json`, `gui-smoke-network.json`, `gui-smoke-no-data.json`, respectivos logs seriais, diagnósticos `*-qemu.log` separados e frames PPM. Os testes incluem hashes das imagens antes/depois e proveniência lida do convidado. Inspecione também os frames visualmente.

O teste de recuperação usa discos próprios descartáveis, preservando o `data.ext4` normal. Exercita inicialização, estado sincronizado após SIGKILL do QEMU, retomada de layout parcialmente inicializado, staging sem publicação, ENOSPC, publicação sincronizada e reboot limpo. Recusa versão desconhecida e symlink em diretório do layout, preservando estado. Discos sem formato e com rótulo estrangeiro devem permanecer idênticos byte a byte. Relatório: `data-smoke.json`; consoles: `data-smoke-*.log`.

SIGKILL do QEMU após `fsync` é um modelo de interrupção de processo virtualizado. Não mede perda física de energia nem falhas de mídia. A [matriz de aceitação](acceptance.md) registra somente resultados realmente executados.

## Limites

Cliente ainda executa como root e o console é de desenvolvimento. RAM recebe caches, logs e estado básico de serviços. `/data` fornece estrutura e contrato de montagem, mas ainda não alimenta automaticamente o catálogo nem uma fila durável. Identidade provisionada, usuário sem privilégios, reserva de espaço, TLS/relógio, servidor, atualização e recuperação de produção têm etapas próprias no plano integral. Testes Pi 5 físicos foram adiados pelo mantenedor.
