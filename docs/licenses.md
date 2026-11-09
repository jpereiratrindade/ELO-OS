# Licenças e inventário inicial

## Código próprio

O mantenedor escolheu **GPLv3.0** em 2026-11-08. Aplicação ao código próprio: **GPL-3.0-only** (versão 3), sem opção automática de versões futuras. O texto integral de [LICENSE](../LICENSE) foi obtido de https://www.gnu.org/licenses/gpl-3.0.txt, sem alteração. O identificador segue [SPDX GPL-3.0-only](https://spdx.org/licenses/GPL-3.0-only.html).

A declaração cobre o código próprio deste repositório. Arquivos e trechos de terceiros conservam suas licenças e avisos de origem, incluindo as configurações derivadas do Buildroot. Esta escolha não modifica a licença do outro repositório ELO nem relê os documentos históricos como se a decisão já existisse antes desta rodada.

O pacote opcional `elo-client` declara `ELO_CLIENT_LICENSE = GPL-3.0-only` e `ELO_CLIENT_LICENSE_FILES = COPYING`; sua fonte tem identificadores SPDX e texto de licença. As novas imagens usam o arquivo comum `/usr/share/licenses/elo-os/COPYING`. As imagens históricas Pi 5/x86 não foram recompiladas apenas para acrescentar o aviso.

## Metadados de terceiros

Extração em 2026-11-08 com Buildroot 2026.08.1 (`7fdeadb3b9f12f78e5fccca914d7fef47090ab9a`), usando a `.config` de cada artefato, sem rebuild:

```bash
make -s --no-print-directory -C .cache/buildroot-2026.08.1 \
  O="$PWD/output/<perfil>" BR2_EXTERNAL="$PWD" show-info \
  > output/<perfil>/software-inventory.json
```

Os JSON completos ficam em `output/`, incluindo ferramentas do host e dependências recursivas. As tabelas abaixo reproduzem apenas entradas `type=target` declaradas pelo Buildroot: incluem pacotes virtuais e de toolchain, portanto não são uma contagem de executáveis instalados. Identificadores `unknown` são lacunas do metadado e não foram substituídos por uma licença presumida.

Para reunir textos e fontes das dependências, a etapa separada do Buildroot é `make -C .cache/buildroot-2026.08.1 O="$PWD/output/<perfil>" BR2_EXTERNAL="$PWD" legal-info`. Ela pode baixar fontes adicionais e gera manifests/textos em `output/<perfil>/legal-info/`. O inventário inicial não declara essa etapa completa; em particular, a toolchain externa exige verificar seus componentes e fontes correspondentes.

## pi5

Metadados: 58 entradas totais, 14 entradas de alvo.

| Pacote | Versão declarada | Licenças declaradas |
| --- | --- | --- |
| busybox | 1.38.0 | GPL-2.0, bzip2-1.0.6 |
| ifupdown-scripts |  | GPL-2.0-or-later |
| initscripts |  | GPL-2.0-or-later |
| kmod | 34.2 | LGPL-2.1+ (library) , GPL-2.0+ (tools) |
| linux | custom | GPL-2.0 |
| rpi-firmware | 063bcab6c8a90efb0d19f69d88cbbc7ec79cab68 | BSD-3-Clause |
| skeleton | — | — |
| skeleton-init-common |  | GPL-2.0-or-later |
| skeleton-init-sysv |  | GPL-2.0-or-later |
| toolchain | — | — |
| toolchain-external | — | — |
| toolchain-external-bootlin | 2025.08-1 | unknown |
| urandom-scripts |  | GPL-2.0-or-later |
| xz | 5.8.4 | 0BSD, GPL-2.0+, GPL-3.0+, LGPL-2.1+, FSFUL, FSFULLR, Public Domain |

## qemu-x86_64

Metadados: 47 entradas totais, 11 entradas de alvo.

| Pacote | Versão declarada | Licenças declaradas |
| --- | --- | --- |
| busybox | 1.38.0 | GPL-2.0, bzip2-1.0.6 |
| ifupdown-scripts |  | GPL-2.0-or-later |
| initscripts |  | GPL-2.0-or-later |
| linux | 6.18.7 | GPL-2.0 |
| skeleton | — | — |
| skeleton-init-common |  | GPL-2.0-or-later |
| skeleton-init-sysv |  | GPL-2.0-or-later |
| toolchain | — | — |
| toolchain-external | — | — |
| toolchain-external-bootlin | 2025.08-1 | unknown |
| urandom-scripts |  | GPL-2.0-or-later |

## qemu-aarch64

Metadados: 45 entradas totais, 11 entradas de alvo.

| Pacote | Versão declarada | Licenças declaradas |
| --- | --- | --- |
| busybox | 1.38.0 | GPL-2.0, bzip2-1.0.6 |
| ifupdown-scripts |  | GPL-2.0-or-later |
| initscripts |  | GPL-2.0-or-later |
| linux | 6.18.7 | GPL-2.0 |
| skeleton | — | — |
| skeleton-init-common |  | GPL-2.0-or-later |
| skeleton-init-sysv |  | GPL-2.0-or-later |
| toolchain | — | — |
| toolchain-external | — | — |
| toolchain-external-bootlin | 2025.08-1 | unknown |
| urandom-scripts |  | GPL-2.0-or-later |

## Perfis gráficos virtuais P2

Inventário de configuração obtido em 2026-11-08, sem executar outro make sobre um `O=` em compilação: carregar cada defconfig GUI em diretório temporário próprio e executar `show-info` ali. Os JSON resultantes foram salvos em `output/qemu-{x86_64,aarch64}-gui/software-inventory.json`. Eles descrevem dependências resolvidas por Kconfig, não comprovam por si só instalação ou execução. Ambos têm 24 entradas de alvo; x86 tem 66 entradas totais, ARM64 64. O pacote virtual `zlib` também aparece sem licença própria; a implementação é `libzlib`.

Adições de alvo em relação aos perfis de console:

| Pacote | Versão | Licenças declaradas pelo Buildroot |
| --- | --- | --- |
| dejavu | 2.37 | Bitstream-Vera |
| double-conversion | 3.4.0 | BSD-3-Clause |
| elo-client | 0.1.0 | GPL-3.0-only |
| freetype | 2.14.3 | FTL or GPL-2.0+ |
| libb2 | 0.98.1 | CC0-1.0 |
| libdrm | 2.4.134 | MIT |
| libpthread-stubs | 0.5 | MIT |
| libzlib | 1.3.2 | Zlib |
| pcre2 | 10.49 | BSD-3-Clause |
| qt6base | 6.11.2 | GPL-2.0+ or LGPL-3.0, GPL-3.0 with exception (tools), GFDL-1.3 (docs), Apache-2.0, BSD-3-Clause, BSL-1.0, MIT |
| qt6declarative | 6.11.2 | LGPL-3.0 or GPL-3.0 or GPL-2.0, BSD-3-Clause (docs), GFDL-1.3 no invariants (docs), BSD-3-Clause (examples), GPL-3.0 (tests), GPL-3.0 WITH Qt-GPL-exception-1.0 (tools) |
| qt6shadertools | 6.11.2 | Apache-2.0 or MIT (SPIRV-Cross), GPL-2.0 or LGPL-3.0 or GPL-3.0, GPL-3.0 (tests), GFDL-1.3 no invariants (docs), GPL-3.0 WITH Qt-GPL-exception-1.0 (tools) |

Qt mantém as licenças declaradas dos seus módulos; nenhum texto/licença de terceiro foi substituído por GPL-3.0-only do projeto. A toolchain externa continua com metadado `unknown` e exige a coleta separada de textos/fontes. `legal-info` e revisão completa de distribuição continuam pendentes; este inventário não declara essa etapa concluída.

## Pi 5 com cliente e Wi-Fi

O perfil experimental `pi5-client` seleciona `brcmfmac_sdio-firmware-rpi`, fixado
pelo Buildroot em `6596d332eaadd63e2413e3937715a084f61c39e2`. Firmware Broadcom/Cypress
conserva termos próprios, declarados como `PROPRIETARY` pela receita. O texto
`LICENSE` original é incluído em `/usr/share/licenses/brcmfmac-sdio-firmware-rpi/`.
Também entram `iw`, `libnl`, `wireless-regdb` e `wpa_supplicant`; inventário
resolvido fica em `output/pi5-client/software-inventory.json` após a compilação.
Esta adição não declara concluída a revisão completa de distribuição.
