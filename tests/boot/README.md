# Boot — testes P1
- [ ] Imagem Pi 5 gerada por Buildroot 2026.08.1.
- [ ] SHA-256 da imagem registrado.
- [ ] 30 boot frios com console e logs.
- [ ] EEPROM/firmware/Device Tree/kernel inventariados.
- [ ] Sistema identifica `/etc/elo-os-release`.
- [ ] Teste de queda de energia executado com mídia descartável e hardware adequado.

## Console virtual de desenvolvimento

1. Compile: `PROFILE=qemu-x86_64 ./scripts/build.sh`.
2. Inicie: `./scripts/run-qemu.sh` (ou `QEMU_ACCEL=tcg ./scripts/run-qemu.sh`).
3. Faça login como `root`, sem senha.
4. Confira `uname -m` (`x86_64`) e `cat /etc/elo-os-release` (`PLATFORM="qemu-x86_64"`).
5. Confira DHCP com `ip addr show eth0` e rota com `ip route`.
6. Execute `poweroff` e confirme que o QEMU encerra.
7. Inicie novamente e confirme que alterações no disco da sessão anterior foram descartadas.

Esses testes validam a base virtual de desenvolvimento. Os ensaios físicos Pi 5 acima continuam necessários.

Teste automatizado da imagem real: `python3 tests/boot/qemu-smoke.py`. Ele inicia duas sessões, verifica login, arquitetura, identidade, DHCP, rota, desligamento e descarte das escritas entre sessões. Os logs ficam em `output/qemu-x86_64/qemu-smoke-*.log` (ou no `OUTPUT_DIR` informado). Para verificar a alternativa sem KVM: `QEMU_ACCEL=tcg python3 tests/boot/qemu-smoke.py`.
