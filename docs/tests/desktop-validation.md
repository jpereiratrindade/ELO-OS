# P2 — próxima compilação no desktop

Por orientação do mantenedor, a compilação gráfica do laptop foi encerrada e seu cache preservado. Esta entrega acrescenta código e testes, sem executar compiladores C++, Qt ou Buildroot. O commit usa `[skip ci]` para adiar também os jobs remotos de compilação; a configuração do workflow continua disponível. O GitHub permite executar depois o workflow manualmente, inclusive nessa revisão ([documentação](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs)).

Os PASS anteriores pertencem às fontes/artefatos registrados nas evidências P1 e na fonte `202ab1d` do cliente. Eles não validam os novos adaptadores Qt, contratos de eventos ou a imagem gráfica desta entrega.

## Preparação

Atualize `main` no desktop e registre `git rev-parse HEAD` e `git status --short`. Use um checkout limpo e saídas novas. Buildroot grava caminhos absolutos; seus diretórios `output/*/{host,staging,build}` não são um cache transportável entre instalações. O cache de fontes `dl/` do Buildroot pode ser transferido separadamente; os downloads continuam sujeitos aos hashes da receita fixada.

Requisitos nativos: Linux, compilador com C++23, CMake >= 3.25, Ninja e desenvolvimento Qt 6 Core/Gui/Qml/Quick/Test. Os adaptadores do frontend usam Linux (`getifaddrs`, `CLOCK_BOOTTIME`); o núcleo permanece independente de Qt/Linux.

Para cada perfil virtual, `PROFILE=<perfil> ./scripts/doctor.sh` verifica as ferramentas Buildroot e o emulador. A GUI requer também os dispositivos VirtIO GPU/PCI e teclado do QEMU; a janela interativa requer GTK. No Fedora, os pacotes correspondentes estão documentados em [tests/client](../../tests/client/README.md). Instale versões compatíveis do emulador e módulos; não reutilize o caminho do emulador extraído no laptop como configuração do desktop.

## 1. Verificações sem build e compilação nativa

Os comandos abaixo são para o operador executar no desktop, em sequência:

```bash
./tests/smoke.sh
cmake -S package/elo-client/src -B build/client-fedora -G Ninja \
  -DELO_BUILD_TESTS=ON -DELO_CXX_STANDARD=23 -DCMAKE_BUILD_TYPE=Release
cmake --build build/client-fedora --parallel 4
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

Em outro terminal, leia `output/client-supervisor/child.pid`, envie SIGKILL e depois SIGSTOP ao filho de cada geração e registre novo PID, nova geração, frames e estado. Encerre o **supervisor** por SIGTERM e confira remoção dos registros e ausência do filho. O teste automatizado de shell usa um processo simulado e já passou; a prova com Qt real ainda precisa ser produzida.

## 3. Imagem gráfica x86_64

```bash
PROFILE=qemu-x86_64-gui ./scripts/doctor.sh
PROFILE=qemu-x86_64-gui JOBS=4 ./scripts/build.sh
# Somente após make retornar zero, sem outro build/VM no mesmo output:
PROFILE=qemu-x86_64-gui python3 tests/client/qemu-gui-smoke.py
PROFILE=qemu-x86_64-gui QEMU_GUI_NETWORK=user python3 tests/client/qemu-gui-smoke.py
```

O primeiro ensaio inicia sem NIC; o segundo inicia com DHCP, derruba/restaura o link pelo QMP e exige a mesma página/conteúdo. Ambos testam SIGKILL, SIGSTOP, nova geração do cliente, retorno da fixture inicial, supervisor sobrevivente e desligamento. A retomada após falha começa na primeira página; posição de navegação não é persistida.

Relatórios separados: `gui-smoke.json` e `gui-smoke-network.json`, respectivos logs e frames PPM em `output/qemu-x86_64-gui/`. Revise visualmente as capturas. Os relatórios incluem hashes antes/depois, identidade, bibliotecas Qt e saúde da apresentação. `QEMU_BOOT_TIMEOUT=360` pode ajustar o limite total do ensaio se necessário.

## 4. ARM64

Repita os mesmos dois ensaios após construir `PROFILE=qemu-aarch64-gui`, usando `qemu-system-aarch64` do desktop. O lançador usa TCG neste perfil. Depois do build, a toolchain desse perfil permite testar isoladamente o núcleo. Com QEMU user `qemu-aarch64` instalado (ou substituindo pelo executável `qemu-aarch64-static` disponível):

```bash
cmake -S package/elo-client/src -B build/client-aarch64-core \
  -DELO_BUILD_GUI=OFF -DELO_BUILD_TESTS=ON -DELO_CXX_STANDARD=23 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_CXX_COMPILER="$PWD/output/qemu-aarch64-gui/host/bin/aarch64-linux-g++" \
  -DCMAKE_CROSSCOMPILING_EMULATOR="qemu-aarch64;-L;$PWD/output/qemu-aarch64-gui/host/aarch64-buildroot-linux-gnu/sysroot"
cmake --build build/client-aarch64-core --parallel 4
ctest --test-dir build/client-aarch64-core --output-on-failure
```

Essa recompilação também está pendente para o código novo. O experimento C++26 usa outro diretório e `-DELO_CXX_STANDARD=26`; não muda o padrão principal nem comprova recursos fora do subconjunto usado.

## Aceitação

Não promover P2-QGUI por build concluído, PID, CI verde ou teste de processo simulado. Exigir os dois cenários gráficos em cada arquitetura, frames inspecionados, queda/travamento recuperados, logs e hashes da revisão efetivamente testada. Registrar limitações e falhas encontradas antes de atualizar a [matriz](acceptance.md).

Pi 5 físico, rootfs imutável, `/data`, recuperação de energia, autenticação e ELO Server continuam em seus gates próprios. Esta sequência não grava mídia nem modifica o perfil físico.
