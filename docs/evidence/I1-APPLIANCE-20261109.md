# I1 — fundação de appliance virtual, 2026-11-09

**Resultado: PASS — x86_64/KVM e ARM64/TCG.** O mantenedor adiou testes físicos. Esta evidência promove somente a fundação virtual do [IMPL-003](../ELO-OS-IMPL-003_v0.1.0.md), sem homologar Pi 5, perda real de energia ou segurança de produção.

## Ambiente e proveniência

- Fedora Silverblue 44, Toolbox `elo-os`, Ryzen 9 7950X, 64 GiB instalados. Dois builds isolados com 16 jobs cada (32 no total).
- Buildroot 2026.08.1, commit `7fdeadb3b9f12f78e5fccca914d7fef47090ab9a`, árvore Buildroot limpa; Linux 6.18.7, BusyBox 1.38.0 e Qt 6.11.2.
- QEMU 10.2.2 Fedora. VirtIO GPU/teclado e Qt Quick por software/LinuxFB; nenhum resultado é atribuído à GPU física.
- Fonte-base `99ede0c9314e1c7d72711a7ee7a09971bebe3727`, com alterações locais desta etapa (`source_dirty=true`). `/etc/elo-build.json` lido dentro de cada VM registra os hashes e modos de todos os arquivos de entrada do projeto, configuração e Buildroot. Os arquivos registrados conferiram com o checkout após os ensaios.
- Rootfs de 256 MiB, RAM virtual padrão de 1 GiB. Disco normal `/data` de 128 MiB; recuperação usa arquivos próprios descartáveis de 32 MiB. Nenhum dispositivo físico foi formatado ou gravado.

## Ensaios executados

| Ensaio | x86_64/KVM | ARM64/TCG |
| --- | --- | --- |
| GUI sem NIC | PASS, 39.969 s | PASS, 42.001 s |
| DHCP, perda e reconexão | PASS, 31.707 s | PASS, 30.345 s |
| GUI sem disco de dados | PASS, 40.296 s | PASS, 42.284 s |
| Recuperação, oito boots por arquitetura | PASS, 158.131 s | PASS, 163.258 s |

Os seis ensaios gráficos exigiram raiz ext4 RO e recusa de escrita em `/etc`, apresentação confirmada antes de `Starting network:`, identidade/configuração, frames/teclado, SIGKILL/SIGSTOP do cliente, nova geração, retorno da fixture inicial e desligamento limpo. Com dados, exigiram montagem `rw,nosuid,nodev,noexec`, marcador `ELO_DATA_V1` e quatro diretórios 0700. Sem dados, estado `UNAVAILABLE MISSING_DEVICE`, ausência de montagem e recusa de escrita alternativa na raiz.

Nos dois ensaios de recuperação, cada um com oito boots:

1. Inicialização de disco novo, escrita sincronizada e raiz RO.
2. SIGKILL do QEMU após `fsync`; retomada de layout parcialmente inicializado preserva estado.
3. Staging não publicado sobrevive à interrupção sem substituir o estado ativo.
4. ENOSPC real em candidato de 2 MiB; estado anterior preservado. Publicação por rename e `fsync` sobrevive ao reboot limpo.
5. Layout de versão desconhecida recusado sem reinicialização; leitura posterior confirma estado preservado.
6. Symlink em diretório do layout recusado, mantendo o estado salvo.
7. Disco sem formato recusado, hash do arquivo idêntico antes/depois.
8. Volume ext4 com rótulo estrangeiro recusado, hash idêntico antes/depois.

Todos os relatórios confirmaram hashes dos kernels/rootfs base inalterados. Frames iniciais, navegação, desconexão e ausência de disco foram inspecionados visualmente. A fixture continua explícita como apresentação local de teste; posição de navegação reinicia após recuperação do cliente.

## Artefatos e rastreabilidade

| Campo | x86_64 | ARM64 |
| --- | --- | --- |
| ID de fonte/configuração | `elo-os/0.1.0+5b890927abbf.80f11fa8f4cd` | `elo-os/0.1.0+5b890927abbf.d0a0ee616dc7` |
| SHA-256 das entradas do projeto | `5b890927abbf79f3c9824a03a2ba86e01c9775cac4260493c48922b85060692a` | `5b890927abbf79f3c9824a03a2ba86e01c9775cac4260493c48922b85060692a` |
| SHA-256 `.config` | `80f11fa8f4cd55ee3dffec5b22e1f2b6a755e0fe6147def4cc8fff6e1543c622` | `d0a0ee616dc7c2cfcda0495a2ac53895aed6258e4d98c180b2c3dbe2a0cfa473` |
| SHA-256 kernel | `1131e3016c6f324fd25d3f0908fa8557ff086c5cbdccfa83504dc10176279ee5` | `fd2236095faded5bbf11c6661f96bc6de4424b0fab85687bc1e8c415a8d62689` |
| SHA-256 rootfs | `3357fa4bdac2ed1d1d7c9d82d08d54c0a2bc340888e6217240a56ef8e94527ab` | `ab850d5cca9916f0aad1d278f90325cdf5a13366dcb236af4660dd5d1398ce8c` |

ID de fonte/configuração não é promessa de reprodução byte a byte do filesystem; os hashes finais identificam os binários ensaiados.

As saídas são `output/toolbox/qemu-{x86_64,aarch64}-appliance/`. Cada uma contém `gui-smoke{,-network,-no-data}.json`, logs seriais, diagnósticos QEMU separados, frames PPM/PNG, `data-smoke.json` e consoles `data-smoke-*.log`. Manifesto com relatórios e hashes: `output/desktop-validation/i1-appliance-manifest.json`. Logs de build/rebuild e inventários estão em `output/desktop-validation/`. Artefatos grandes continuam locais, ignorados no Git.

| Harness | SHA-256 |
| --- | --- |
| `tests/client/qemu-gui-smoke.py` | `5ab2d686a8228a83d6749a04a6c8e348091079c314014a233aedf4c8e7265715` |
| `tests/recovery/appliance-smoke.py` | `479f40eb1965f81beea8a75fa2fc125cd2ca58448fb47eaf6e473fe90c42e7ef` |
| `tests/recovery/data-image-test.py` | `f8db8ad7e334afa8a9da77ba92fe159de11b2c6ae1bce989cc3c059e44ca6373` |
| `tests/config-smoke.py` | `38e0193748356f815e479c4a8e30c3f435454edd5fdd7c45142d2dd43c102a8b` |
| `tests/smoke.sh` | `71b8860af43f787c1a9eebc3fe932a5c2f7057ec629afae79c428bda60587aeb` |

## Regressão e correções encontradas

- Os perfis P2 anteriores passaram novamente sem NIC e com perda/reconexão, nas duas arquiteturas; imagens não foram reconstruídas e seus hashes foram preservados. Relatórios originais/harness preservados em `output/desktop-validation/p2-baseline-99ede0c/` antes da repetição.
- Um ensaio de regressão x86 foi encerrado após avisos do QEMU intercalarem o delimitador serial. O harness separa agora stderr do emulador; os quatro cenários P2 e seis cenários I1 passaram com essa correção. Tentativa anterior preservada em `output/desktop-validation/gui-regression-serial-interleave.*`.
- Revisão encontrou `stat -c` desabilitado no BusyBox; fragmento corrigido e ambos os builds finais recompilados com `CONFIG_FEATURE_STAT_FORMAT=y` antes dos boots.
- Primeira tentativa de ENOSPC mostrou que um `dd` de blocos de 1 MiB pode falhar e ainda deixar espaço para poucos bytes. O cenário passou a exigir falha de candidato de 2 MiB; o console registra `No space left on device` para filler e candidato. Tentativas anteriores preservadas em `output/desktop-validation/enospc-scenario-before-fix/`.
- Q0 Kconfig passou nos sete perfis; smoke local passou em 34 testes (9 preflight, 11 conteúdo, 8 supervisor, 6 disco/launcher). CI desta revisão ainda não executada.

## Limites e continuidade

SIGKILL do QEMU após `fsync` testa interrupção de processo virtualizado, com caches e filesystem do host ainda presentes. Não demonstra queda física de energia, mídia defeituosa ou EEPROM/boot/GPU/toque do Pi 5. Esses testes continuam adiados.

Cliente executa como root, console serial sem senha é de desenvolvimento e caches/logs básicos ficam em RAM. Raiz RO não equivale a dm-verity ou secure boot; dados pertencem a operador confiável. Testes de staging são operações explícitas do harness: não anunciam catálogo ou fila integrados ao cliente.

Identidade provisionada, execução sem privilégios, limites de escrita, catálogo/fila duráveis, contrato de distribuição/TLS/relógio, atualização e operação prolongada permanecem nas etapas I2–I7. O contrato de distribuição Thin Client ainda não foi identificado/definido. Consulte [aceitação](../tests/acceptance.md) e [comandos de reprodução](../tests/appliance-validation.md).
