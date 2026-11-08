# ELO/OS — Linux embarcado mínimo para ELO Thin Client

> Faça simples. Depois deixe mais leve. **Sempre pronto. Sempre incompleto.**

**Versão de projeto:** `v0.1.0` · **Estado:** `design-candidate / scaffold` · **Hardware:** Raspberry Pi 5, ARM64

O ELO/OS é uma árvore `br2-external` do Buildroot para compor uma distribuição-appliance Linux mínima. **Não é outro kernel**, nem o ELO Server, nem a aplicação ELO existente. Esta versão entrega documentação, estrutura, configuração inicial Pi 5 e um *demo* Qt opcional. **Não afirma funcionamento gráfico nem confiabilidade homologados no hardware.**

## Decisões iniciais

- Buildroot **2026.08.1**, `raspberrypi5_defconfig` adaptado e fixado em `configs/elo_pi5_defconfig`.
- Linux + BusyBox; sem desktop. Pilha DRM/KMS + Qt 6/EGLFS como **caminho experimental P2**.
- Subconjunto de experiência offline local, com futura sincronização segura pelo ELO Server.
- Nenhuma credencial, segredo, certificado privado ou configuração de dispositivo no Git.

## Árvore

- `docs/`: constituição e ADRs versionados; critérios de aceitação.
- `configs/`: defconfig Pi 5 derivado do oficial Buildroot 2026.08.1.
- `board/elo/pi5/`: overlay do rootfs e hooks de construção.
- `package/elo-client/`: demonstração Qt/QML **opcional, não incluída na imagem P1**.
- `scripts/`: build, diagnóstico e inventário da imagem.
- `tests/`: verificações do repositório e roteiros de ensaio.

## Primeiro uso

Requisitos de host: Fedora/Linux com `git`, `make`, `gcc`, `g++`, `python3`, `rsync`, ferramentas comuns para Buildroot (veja [manual oficial](https://buildroot.org/downloads/manual/manual.html)) e Internet para obtenção de fontes e toolchain. O script baixa a release 2026.08.1 do repositório oficial **somente quando invocado**.

```bash
./tests/smoke.sh
./scripts/doctor.sh
./scripts/build.sh
./scripts/inspect-image.sh
```

O build pode baixar fontes e consumir recursos significativos. Não executamos o build nesta entrega.

O comando `./scripts/build.sh` cria `.cache/buildroot-2026.08.1/`, configura `output/pi5/` com `elo_pi5_defconfig` e chama o Buildroot. A saída esperada é `output/pi5/images/sdcard.img`, caso a versão/base/hardware suporte corretamente todas as dependências. **O script não grava mídia.**

### Primeiro marco: P1, console Linux

A primeira imagem **não habilita o cliente Qt**: é uma base Pi 5 com identidade ELO/OS. Validar boot e console antes de adicionar a interface gráfica. Os arquivos `board/elo/pi5/genimage.cfg`, `post-image.sh` e `package/elo-client/` estão preparados para fases futuras e **não devem ser interpretados como integração homologada**.

### Segundo marco: P2, demo Qt

Após validar o perfil P1, executar `./scripts/menuconfig.sh` e habilitar `elo-client (Qt Quick proof-of-concept)` em `External options`. O pacote depende de Qt 6 Base (GUI) e Qt Declarative; configurar DRM/Mesa/EGL e requisitos de Qt no Buildroot. Gravar nova defconfig somente após os testes de configuração. O demo ainda **não contém protocolo ELO, cache, eventos nem lógica de domínio**.

## Repositórios relacionados

- [ELO existente](https://github.com/jpereiratrindade/ELO)
- [Constituição do ELO](https://github.com/jpereiratrindade/ELO/blob/main/docs/constitution/ELO-CONSTITUTION-001.md)
- [Buildroot 2026.08.1](https://buildroot.org/download.html)

## Versão e status

`VERSION` identifica a versão do **projeto**, não a versão de uma imagem executada. As decisões de `docs/adr` estão **propostas**. Cada avanço só vira *demonstrado* com evidências e testes.

Licenciamento de código ainda requer definição explícita pelo mantenedor; não presumir licença do ELO existente nem da distribuição resultante. As licenças das dependências permanecem aplicáveis e precisarão ser inventariadas.
