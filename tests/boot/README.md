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
