# Boot — testes P1
- [x] Imagem Pi 5 gerada por Buildroot 2026.08.1.
- [x] SHA-256 da imagem registrado em `docs/evidence/P1-BUILT-PI5-20261108.md`.
- [ ] 30 boot frios com console e logs.
- [ ] EEPROM/firmware/Device Tree/kernel inventariados.
- [ ] Sistema identifica `/etc/elo-os-release`.
- [ ] Teste de queda de energia executado com mídia descartável e hardware adequado.

A lista acima se refere à imagem e ao hardware Pi 5. Os boots virtuais abaixo não marcam os ensaios físicos como concluídos. O protocolo está em [pi5-first-boot.md](pi5-first-boot.md).

## Console virtual de desenvolvimento

1. Compile: `PROFILE=qemu-x86_64 ./scripts/build.sh`.
2. Inicie: `./scripts/run-qemu.sh` (ou `QEMU_ACCEL=tcg ./scripts/run-qemu.sh`).
3. Faça login como `root`, sem senha.
4. Confira `uname -m` (`x86_64`) e `cat /etc/elo-os-release` (`PLATFORM="qemu-x86_64"`).
5. Confira DHCP com `ip addr show eth0` e rota com `ip route`.
6. Execute `poweroff` e confirme que o QEMU encerra.
7. Inicie novamente e confirme que alterações no disco da sessão anterior foram descartadas.

Esses testes validam a base virtual de desenvolvimento. Os ensaios físicos Pi 5 acima continuam necessários.

Teste automatizado da imagem real: `python3 tests/boot/qemu-smoke.py`. Ele inicia duas sessões, verifica login, arquitetura, identidade, DHCP, rota, desligamento e descarte das escritas entre sessões. Os logs e relatórios JSON ficam em `output/<perfil>/qemu-smoke-*` (ou no `OUTPUT_DIR` informado). Para verificar a alternativa sem KVM: `QEMU_ACCEL=tcg python3 tests/boot/qemu-smoke.py`.

## Validação virtual — 2026-11-08

Ambiente: Fedora 44 x86_64, QEMU 10.2.2, Buildroot 2026.08.1 e kernel Linux 6.18.7. Build completo concluído com saída zero.

- KVM: dois boots passaram no teste automatizado.
- TCG: dois boots passaram no mesmo teste.
- Verificados: login root, arquitetura x86_64, identidade ELO/OS, DHCP, rota padrão, escrita no rootfs, descarte das escritas entre sessões e desligamento.
- Verificações de integridade/sintaxe do scaffold e lançamento mínimo com KVM também passaram.

SHA-256 das imagens virtuais testadas (artefatos locais em `output/qemu-x86_64/images/`):

```text
69c987643bca326ec0cd462c74a89b8832c854de8e76e34b4a2d179387a819b9  bzImage
653336607ad0c8ea876ae87489a60c2a9719639f326185bcedd0273dc21596d4  rootfs.ext4
```

Os testes físicos Pi 5 do roteiro P1 continuam pendentes. Qt não foi habilitado nem validado nesta imagem.

## Regressão ampliada e ARM64

`PROFILE=qemu-aarch64 python3 tests/boot/qemu-smoke.py` usa o mesmo contrato em imagens próprias ARM64, console `ttyAMA0` e TCG. O teste falha se detectar panic, repetição do login sem entrada, identidade/arquitetura incorretas, PID 1 diferente de BusyBox init, disco/raiz incorretos, ausência de DHCP/rota, falha de desligamento ou mutação da imagem base. Não depende de um IP ou nome de interface fixos. Por sessão registra saída real, PID do QEMU controlado, rede e memória; por execução registra hashes, revisão Git e defconfig.

Use `QEMU=/caminho/do/binário` quando o emulador não estiver no PATH. O timeout padrão por boot é 180 segundos (`QEMU_BOOT_TIMEOUT`); o ensaio observa pelo menos um segundo de console ocioso antes e depois do login (padrão 3, `QEMU_IDLE_SECONDS`). Não rode teste durante build ou outra VM no mesmo `OUTPUT_DIR`.

Os estados atuais estão na [matriz de aceitação](../../docs/tests/acceptance.md). Os resultados de 2026-11-08 acima são históricos e vinculados aos hashes indicados; relatórios de nova execução não devem ser atribuídos a imagens diferentes.
