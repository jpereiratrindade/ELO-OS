# P2 — núcleo e imagem gráfica ARM64 no desktop

- Data: 2026-11-09, fuso America/Sao_Paulo.
- Fontes do cliente, overlays e defconfig: `c456f0b88c47c6b9d0bf1866712aff2cffe53c53`, sem mudanças nesses arquivos durante o build/ensaio.
- Árvore em desenvolvimento: documentação, `scripts/doctor.sh` e correção do harness offline já descrita na [evidência x86](P2-DESKTOP-X86-20261109.md); os relatórios QEMU registram `source_dirty=true`.
- Desktop: Fedora Silverblue 44 x86_64, Ryzen 9 7950X, 64 GiB instalados; Toolbox Fedora 44 `elo-os`.
- Buildroot 2026.08.1, perfil `qemu-aarch64-gui`, saída nova `output/toolbox/qemu-aarch64-gui/`, `JOBS=32`, `BR2_JLEVEL=32`.
- Toolchain: Bootlin AArch64 glibc stable 2025.08-1; GCC 14.3.0, libstdc++ release 14, `__GLIBCXX__=20250523`.
- Qt 6.11.2, Linux 6.18.7. QEMU system/user 10.2.2. VM `virt`, Cortex-A53, TCG, 2 vCPUs, 1 GiB virtual, VirtIO GPU e Qt Quick por software/LinuxFB.

## Resultados

| Ensaio | Resultado | Duração observada |
| --- | --- | --- |
| Núcleo ARM64 C++23, CTest via QEMU user | PASS, 1/1 | 0,02 s |
| Núcleo ARM64 C++26, subconjunto usado, CTest via QEMU user | PASS, 1/1 | 0,02 s |
| Executável de console ARM64, nos dois padrões | PASS, BOOTING → READY_LOCAL, três páginas | Sem benchmark |
| Imagem gráfica ARM64, build/inventário | PASS, código 0 | Sem benchmark |
| QEMU sem NIC | PASS | 44,274 s |
| QEMU com DHCP e perda/reconexão | PASS | 32,081 s |

Os testes do núcleo exercitam fixture, confirmação de apresentação, falhas/retry, eventos offline, diagnósticos e ledger idempotente em memória. Os executáveis foram identificados como ELF AArch64 e executados com `qemu-aarch64-static` e o sysroot da toolchain instalada, em diretórios CMake separados da imagem.

C++23 informa `__cplusplus=202302L`; o experimento C++26 usa `-std=c++2c` e informa `202400L`. Os dois padrões produziram os mesmos hashes para o núcleo e seu teste. Isso demonstra somente o subconjunto de linguagem/biblioteca utilizado; não comprova suporte completo a C++26. Qt permanece no padrão próprio de sua receita.

Os dois boots verificaram arquitetura/identidade, BusyBox PID 1, ext4 RW, cliente Qt e bibliotecas reais, frames, setas/Home, recuperação após SIGKILL e SIGSTOP com novo PID/geração, sobrevivência do supervisor e desligamento. Hashes antes/depois preservados por snapshot. Sem NIC, o cliente chegou a `READY_LOCAL`; com rede, perda do link produziu `DEGRADED_OFFLINE` e reconexão restaurou `READY_LOCAL`, mantendo página 2 e digest. O frame reconectado coincide com o anterior à perda.

Capturas `gui-ready`, `gui-next`, `gui-network-disconnected` e `gui-network-recovered-stop` inspecionadas visualmente: textos acentuados, botões, página e estado legíveis/coerentes. Capturas de reset/recuperação também comparadas pelo harness. RSS amostrado: 36.976 KiB sem NIC e 36.928 KiB com rede, dois threads; não é dimensionamento homologado nem benchmark da Pi 5.

## Falhas de preparação resolvidas

1. O download Bootlin falhou por DNS; os mirrors Buildroot responderam 404. A URL oficial respondeu em nova tentativa; o arquivo foi baixado para cache, conferido contra o SHA-256 da receita (`dfb47eee874eef9e8a7fc042eee4e0a183f444b6bcde6a82fef8f009918389c9`) e novamente validado pelo Buildroot.
2. O OpenSSL usado na construção do kernel exigiu `Time::Piece`, ausente na Toolbox. `perl-Time-Piece` foi instalado apenas no container e o build retomou com as etapas anteriores preservadas. `doctor.sh` agora verifica módulos Perl básicos e exige `Time::Piece` quando a configuração/defconfig seleciona OpenSSL. O diagnóstico retornou 1 antes da instalação e 0 depois; requisito também documentado no roteiro da Toolbox.

Nenhuma alteração no kernel, cliente, defconfig ou overlay foi necessária para passar os ensaios ARM64.

## Artefatos e hashes SHA-256

| Artefato | SHA-256 |
| --- | --- |
| `output/toolbox/qemu-aarch64-gui/images/Image` | `26f122af976d24963c75c49db36522d5b9274bd2312650146c51df946131a3c1` |
| `output/toolbox/qemu-aarch64-gui/images/rootfs.ext4` (256 MiB) | `9647e6db0c6ba1b7f8abc15d6ec0e294f456e15dd6f90674d9ac7380e8201892` |
| `.config` da imagem ARM64 | `c4d6b52aba50ec9583bfacbb87a919b35cb27144634b4b15a1fac2c7b44620ef` |
| `build/client-aarch64-core-toolbox-cxx23/elo-client-core` | `a23309798e221eae5202afeecde529bdfaea18b5fe43a8fdd7d93be70368189e` |
| `build/client-aarch64-core-toolbox-cxx23/elo-core-test` | `f4cc013c12b2f83527e603c4b51e0a1458059c13e887fa116a096776947efcce` |
| `build/client-aarch64-core-toolbox-cxx26/elo-client-core` | `a23309798e221eae5202afeecde529bdfaea18b5fe43a8fdd7d93be70368189e` |
| `build/client-aarch64-core-toolbox-cxx26/elo-core-test` | `f4cc013c12b2f83527e603c4b51e0a1458059c13e887fa116a096776947efcce` |
| `tests/client/qemu-gui-smoke.py` | `dbef2a8971e292835ec8392ee17af56d210589fb04938a7372cfd5ec66a547dd` |
| `scripts/doctor.sh` após correção | `c6da0375e6ca3a1b2cb7924e49509e24a471d0b5d0ee8de91649b4ba3bb3258f` |

Relatórios gráficos completos: `output/toolbox/qemu-aarch64-gui/gui-smoke{,-network}.json`, respectivos logs e PPMs. Build/inventário: `output/desktop-validation/toolbox-build-qemu-aarch64-gui.log` e `toolbox-aarch64-image-inventory.log`. Núcleo: `toolbox-aarch64-core.{log,json}` e `toolbox-aarch64-compiler.txt` no mesmo diretório de validação. Diagnóstico de dependências: `toolbox-aarch64-doctor-{before,after}.log`. Artefatos locais ignorados pelo Git.

Reprodução: [roteiro do desktop](../tests/desktop-validation.md). Na Toolbox, use `PROFILE=qemu-aarch64-gui` e `OUTPUT_DIR="$PWD/output/toolbox/qemu-aarch64-gui"` em todos os comandos da imagem.

## Estado e limites

P2-A64 e P2-QGUI ARM64/TCG demonstrados para estes artefatos. Somados aos dois cenários [x86_64/KVM](P2-DESKTOP-X86-20261109.md), fecham o gate gráfico **virtual** descrito na matriz. Cliente nativo também passou na sessão Fedora por QPA xcb/Xwayland, com captura inspecionada na evidência x86.

Não comprova hardware BCM2712/V3D, boot físico Pi 5, backend Wayland nativo, servidor/autenticação, 72 horas offline, `/data`, recuperação de energia ou navegação persistente. Rootfs segue RW, cliente como root e alterações da VM descartáveis. Qt ainda registra aviso de locale C sem locale UTF-8 disponível; a renderização acentuada observada está correta. Artefatos históricos P1 e perfil físico não foram recompilados.

## Preservação da evidência

Antes dos ensaios de regressão da etapa I1, os relatórios, logs, frames e harness desta baseline foram copiados para `output/desktop-validation/p2-baseline-99ede0c/`, em subdiretórios por perfil. Os caminhos de relatório nas saídas normais podem receber novas execuções; os resultados e hashes descritos neste documento correspondem à cópia preservada. As imagens base não foram reconstruídas para esses ensaios.
