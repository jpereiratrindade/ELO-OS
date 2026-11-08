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
