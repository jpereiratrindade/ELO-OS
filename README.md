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

O build pode baixar fontes e consumir recursos significativos.

O comando `./scripts/build.sh` cria `.cache/buildroot-2026.08.1/`, configura `output/pi5/` com `elo_pi5_defconfig` e chama o Buildroot. A saída esperada é `output/pi5/images/sdcard.img`, caso a versão/base/hardware suporte corretamente todas as dependências. **O script não grava mídia.**

### Primeiro marco: P1, console Linux

A primeira imagem **não habilita o cliente Qt**: é uma base Pi 5 com identidade ELO/OS. Validar boot e console antes de adicionar a interface gráfica. Os arquivos `board/elo/pi5/genimage.cfg`, `post-image.sh` e `package/elo-client/` estão preparados para fases futuras e **não devem ser interpretados como integração homologada**.

### Segundo marco: P2, demo Qt

Após validar o perfil P1, executar `./scripts/menuconfig.sh` e habilitar `elo-client (Qt Quick proof-of-concept)` em `External options`. O pacote depende de Qt 6 Base (GUI) e Qt Declarative; configurar DRM/Mesa/EGL e requisitos de Qt no Buildroot. Gravar nova defconfig somente após os testes de configuração. O demo ainda **não contém protocolo ELO, cache, eventos nem lógica de domínio**.

### Desenvolvimento no Fedora com QEMU

O perfil `qemu-x86_64` permite desenvolver boot, serviços, rede e comportamento do sistema sem gravar o microSD. Ele usa a identidade e o overlay ELO/OS da base P1, com identificação própria de plataforma. É uma compilação x86_64 separada: não executa a `sdcard.img` ARM64 nem valida firmware, drivers, GPU ou desempenho do Raspberry Pi 5.

```bash
# Se QEMU ainda não estiver instalado:
sudo dnf install qemu-system-x86-core

PROFILE=qemu-x86_64 ./scripts/build.sh
PROFILE=qemu-x86_64 ./scripts/inspect-image.sh
./scripts/run-qemu.sh
```

A saída fica em `output/qemu-x86_64/`; a imagem Pi 5 em `output/pi5/` é preservada. O lançador usa KVM quando acessível e emulação por software como alternativa (`QEMU_ACCEL=tcg ./scripts/run-qemu.sh`). A VM tem console no terminal e rede por NAT, sem privilégios de root ou portas expostas no host. Login de bancada: `root`, sem senha. Para sair: `Ctrl-a`, depois `x`; para desligar pelo console: `poweroff`.

O disco usa snapshot temporário: alterações feitas dentro da VM são descartadas ao sair. Para persistir mudanças do sistema, edite o overlay ou os pacotes no repositório e recompile com o mesmo comando. Para configurar pacotes: `PROFILE=qemu-x86_64 ./scripts/menuconfig.sh`. Qt ainda não está habilitado neste perfil; o lançador atual usa apenas console.

No console, confira `uname -m`, `cat /etc/elo-os-release`, `ip addr show eth0` e `ip route`. O roteiro está em [tests/boot/README.md](tests/boot/README.md). Continue usando `./scripts/build.sh` para gerar a imagem destinada ao Pi 5.

## Repositórios relacionados

- [ELO existente](https://github.com/jpereiratrindade/ELO)
- [Constituição do ELO](https://github.com/jpereiratrindade/ELO/blob/main/docs/constitution/ELO-CONSTITUTION-001.md)
- [Buildroot 2026.08.1](https://buildroot.org/download.html)

## Versão e status

`VERSION` identifica a versão do **projeto**, não a versão de uma imagem executada. As decisões de `docs/adr` estão **propostas**. Cada avanço só vira *demonstrado* com evidências e testes.

Licenciamento de código ainda requer definição explícita pelo mantenedor; não presumir licença do ELO existente nem da distribuição resultante. As licenças das dependências permanecem aplicáveis e precisarão ser inventariadas.
