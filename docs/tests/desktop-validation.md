# P2 — compilação e validação no desktop

Em 2026-11-09, a compilação foi retomada no desktop Fedora Silverblue 44, em Toolbox dedicada, com 32 jobs. Cliente nativo, sessão gráfica Fedora e dois cenários gráficos por arquitetura passaram: [x86_64/KVM](../evidence/P2-DESKTOP-X86-20261109.md) e [ARM64/TCG](../evidence/P2-DESKTOP-AARCH64-20261109.md). Núcleo ARM64 passou em C++23 e no subconjunto experimental C++26.

O build do laptop havia sido encerrado por orientação do mantenedor, com cache preservado e CI de compilação adiada por `[skip ci]`. Os PASS históricos permanecem vinculados às fontes/artefatos das evidências P1 e `202ab1d`; os novos resultados nativos/x86_64/ARM64 pertencem à fonte `c456f0b` e ao harness corrigido registrados nas evidências do desktop.

## Preparação

Atualize `main` no desktop e registre `git rev-parse HEAD` e `git status --short`. Use um checkout limpo e saídas novas. Buildroot grava caminhos absolutos; seus diretórios `output/*/{host,staging,build}` não são um cache transportável entre instalações. O cache de fontes `dl/` do Buildroot pode ser transferido separadamente; os downloads continuam sujeitos aos hashes da receita fixada.

Requisitos nativos: Linux, compilador com C++23, CMake >= 3.25, Ninja e desenvolvimento Qt 6 Core/Gui/Qml/Quick/Test. Os adaptadores do frontend usam Linux (`getifaddrs`, `CLOCK_BOOTTIME`); o núcleo permanece independente de Qt/Linux.

Para cada perfil virtual, `PROFILE=<perfil> ./scripts/doctor.sh` verifica as ferramentas Buildroot e o emulador. A GUI requer também os dispositivos VirtIO GPU/PCI e teclado do QEMU; a janela interativa requer GTK. No Fedora, os pacotes correspondentes estão documentados em [tests/client](../../tests/client/README.md). Instale versões compatíveis do emulador e módulos; não reutilize o caminho do emulador extraído no laptop como configuração do desktop.

## 1. Verificações sem build e compilação nativa

### Fedora Silverblue / Toolbox

A bancada atual usa `toolbox enter elo-os`. Para criar outra bancada, `toolbox create --release 44 elo-os`. Instale dentro dela as ferramentas de desenvolvimento e módulos necessários; no desktop, a instalação foi feita apenas no container:

```bash
sudo dnf install git make gcc gcc-c++ python3 rsync tar gawk sed xz gzip bzip2 \
  patch cpio unzip file wget bc which diffutils findutils \
  perl-English perl-ExtUtils-MakeMaker perl-Thread-Queue perl-FindBin \
  perl-IPC-Cmd perl-Data-Dumper perl-Time-Piece cmake ninja-build pkgconf-pkg-config \
  qt6-qtbase-devel qt6-qtdeclarative-devel \
  qemu-system-x86-core qemu-system-aarch64-core qemu-user-static-aarch64 \
  qemu-device-display-virtio-gpu qemu-device-display-virtio-gpu-pci qemu-ui-gtk
```

O proxy salvo no GNOME não implica variáveis de proxy no terminal/container. Confira acesso aos repositórios na própria Toolbox e configure o proxy localmente quando necessário, sem versionar credenciais. Nesta rodada, proxy explícito recebeu 403 e os downloads funcionaram sem proxy explícito.

Os comandos seguintes rodam dentro da Toolbox a partir da raiz do checkout. Para usar os artefatos desta bancada, exporte:

```bash
export CLIENT_BUILD_DIR="$PWD/build/client-toolbox"
export OUTPUT_DIR="$PWD/output/toolbox/qemu-x86_64-gui"
```

Use `CLIENT_BUILD_DIR` como diretório `-B`/`--test-dir` do exemplo nativo abaixo. Para abrir o cliente nativo já preparado: `CLIENT_BUILD_DIR="$PWD/build/client-toolbox" JOBS=32 ./scripts/run-client.sh`.

`OUTPUT_DIR` vale para build, inspeção, lançador e smoke. No build x86 do desktop, a configuração local também usa `BR2_JLEVEL=32`. Ao passar para ARM64, troque `OUTPUT_DIR` por `"$PWD/output/toolbox/qemu-aarch64-gui"`; não reutilize a saída x86. Downloads em `.cache/buildroot-2026.08.1/dl/` podem ser compartilhados; saídas de host e Toolbox permanecem separadas.

Os comandos abaixo são para o operador executar no desktop, em sequência:

```bash
./tests/smoke.sh
cmake -S package/elo-client/src -B build/client-fedora -G Ninja \
  -DELO_BUILD_TESTS=ON -DELO_CXX_STANDARD=23 -DCMAKE_BUILD_TYPE=Release
cmake --build build/client-fedora --parallel 32
QT_QUICK_BACKEND=software ctest --test-dir build/client-fedora --output-on-failure
QT_QUICK_BACKEND=software build/client-fedora/elo-client
```

Execute na sessão gráfica real e observe texto, navegação, conectividade e retry. O comando alternativo com Xvfb está em [tests/client](../../tests/client/README.md). Preserve logs e screenshot próprios da revisão; não sobrescreva uma evidência antiga para atribuí-la a outro código.

## 2. Conteúdo externo de teste e supervisor

```bash
fixture_path=tests/client/fixtures/local.json
fixture_size=$(wc -c < "$fixture_path")
fixture_sha=$(sha256sum "$fixture_path" | cut -d' ' -f1)
python3 scripts/elo_content.py activate "$PWD/output/local-content" "$fixture_path" \
  --size "$fixture_size" --sha256 "$fixture_sha"
python3 scripts/elo_content.py show "$PWD/output/local-content"
QT_QUICK_BACKEND=software build/client-fedora/elo-client \
  --content-dir "$PWD/output/local-content"
```

O SHA acima é calculado pelo operador para uma fixture controlada; não autentica um servidor. Confira os [contratos locais](../client/local-contracts.md). Com `--content-dir`, ausência/corrupção é erro explícito; a aplicação não substitui silenciosamente esse conteúdo pela fixture incorporada. Para usar uma nova ativação após uma apresentação válida, reinicie o cliente. Retry serve para recuperar uma carga que havia falhado; não há atualização automática em segundo plano.

Para exercitar o supervisor com a aplicação Qt real:

```bash
ELO_RUNTIME_DIR="$PWD/output/client-supervisor" QT_QUICK_BACKEND=software \
  board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor \
  "$PWD/build/client-fedora/elo-client"
```

Em outro terminal, leia `output/client-supervisor/child.pid`, envie SIGKILL e depois SIGSTOP ao filho de cada geração e registre novo PID, nova geração, frames e estado. Encerre o **supervisor** por SIGTERM e confira remoção dos registros e ausência do filho. O teste automatizado de shell usa processo simulado; a prova adicional com Qt real passou no desktop, e as imagens x86_64/ARM64 exercitaram a política padrão. Os métodos e limites estão nas evidências vinculadas acima.

## 3. Imagem gráfica x86_64

```bash
PROFILE=qemu-x86_64-gui ./scripts/doctor.sh
PROFILE=qemu-x86_64-gui JOBS=32 ./scripts/build.sh
# Somente após make retornar zero, sem outro build/VM no mesmo output:
PROFILE=qemu-x86_64-gui python3 tests/client/qemu-gui-smoke.py
PROFILE=qemu-x86_64-gui QEMU_GUI_NETWORK=user python3 tests/client/qemu-gui-smoke.py
```

O primeiro ensaio inicia sem NIC ligada a dispositivo e sem rotas IPv4; um túnel inativo `sit0` criado pelo kernel é permitido. O segundo inicia com DHCP, derruba/restaura o link pelo QMP e exige a mesma página/conteúdo. Ambos testam SIGKILL, SIGSTOP, nova geração do cliente, retorno da fixture inicial, supervisor sobrevivente e desligamento. A retomada após falha começa na primeira página; posição de navegação não é persistida.

Relatórios separados: `gui-smoke.json` e `gui-smoke-network.json`, respectivos logs e frames PPM em `output/qemu-x86_64-gui/`. Revise visualmente as capturas. Os relatórios incluem hashes antes/depois, identidade, bibliotecas Qt e saúde da apresentação. `QEMU_BOOT_TIMEOUT=360` pode ajustar o limite total do ensaio se necessário.

## 4. ARM64

Repita os mesmos dois ensaios após construir `PROFILE=qemu-aarch64-gui`, usando `qemu-system-aarch64` do desktop. Na Toolbox, exporte primeiro `OUTPUT_DIR="$PWD/output/toolbox/qemu-aarch64-gui"` para build, inspeção, lançador e testes. O lançador usa TCG neste perfil. A toolchain instalada desse perfil permite testar isoladamente o núcleo em outro diretório. O exemplo usa `qemu-aarch64-static`; `QEMU_USER=qemu-aarch64` seleciona a alternativa dinâmica quando instalada:

```bash
ARM_GUI_OUT=${OUTPUT_DIR:-"$PWD/output/qemu-aarch64-gui"}
cmake -S package/elo-client/src -B build/client-aarch64-core \
  -DELO_BUILD_GUI=OFF -DELO_BUILD_TESTS=ON -DELO_CXX_STANDARD=23 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_CXX_COMPILER="$ARM_GUI_OUT/host/bin/aarch64-linux-g++" \
  -DCMAKE_CROSSCOMPILING_EMULATOR="${QEMU_USER:-qemu-aarch64-static};-L;$ARM_GUI_OUT/host/aarch64-buildroot-linux-gnu/sysroot"
cmake --build build/client-aarch64-core --parallel 4
ctest --test-dir build/client-aarch64-core --output-on-failure
```

Essa recompilação passou no desktop, nos diretórios `build/client-aarch64-core-toolbox-cxx23` e `build/client-aarch64-core-toolbox-cxx26`. O experimento C++26 usa outro diretório e `-DELO_CXX_STANDARD=26`; não muda o padrão principal nem comprova recursos fora do subconjunto usado.

## Aceitação

Não promover P2-QGUI por build concluído, PID, CI verde ou teste de processo simulado. Exigir os dois cenários gráficos em cada arquitetura, frames inspecionados, queda/travamento recuperados, logs e hashes da revisão efetivamente testada. Registrar limitações e falhas encontradas antes de atualizar a [matriz](acceptance.md).

Rootfs RO e `/data` têm agora perfis `-appliance` e [roteiro próprio](appliance-validation.md); os perfis P2 deste documento preservam suas características. Pi 5 físico, recuperação de energia, autenticação e ELO Server continuam em seus gates próprios. Esta sequência não grava mídia nem modifica o perfil físico.
