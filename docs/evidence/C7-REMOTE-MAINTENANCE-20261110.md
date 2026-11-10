# C7 — Manutenção remota do Pi 5 — 2026-11-10

Resultado: PASS no ambiente de integração ARM64. Validação física pendente.

## Artefato

Imagem: `output/pi5-client/images/sdcard.img`.

SHA-256:
`b07d45309434c5e7d668005d6477f5a30b856cfd1614e3912f3a14aaafa96f09`.

Rootfs testado:
`eff4f56fa22555d859c0d0ce63718894d58d0a1da663d54900902c9b0bad4862`.

Perfil inclui Dropbear com autenticação exclusivamente por chave, chrony,
restauração de limite inferior de horário, diagnóstico remoto e probe HTTPS sem GUI.
Provisionamento exige chave pública; credenciais operacionais não integram imagem base.
Instalador local foi atualizado para provisionar chave pública da bancada e conferir
hash da imagem antes da gravação. Nenhuma gravação física foi feita nesta etapa.

## Validação

- Build completo `PROFILE=pi5-client JOBS=32 ./scripts/build.sh`: PASS.
- `./tests/smoke.sh`: PASS, 67 testes.
- `python3 tests/config-smoke.py`: PASS nos oito perfis; SSH/chrony restritos ao Pi cliente.
- `tests/network/distribution-test.py`: PASS, 19 testes, incluindo probe HTTPS,
  rejeição de credencial e verificação de nome TLS.
- `tests/client/terminal-setup-test.py`: PASS, nove testes, incluindo chave pública,
  permissões, provisionamento e relógio sem regressão.
- QEMU ARM64 com rootfs final: PASS nos modos manutenção em rede isolada e apresentação offline.

Ensaio de manutenção usa chave SSH, certificado, credencial e servidores HTTPS/NTP
sintéticos, sem alterar cadastro do Pi no servidor real. Verifica login autorizado,
rejeição de outra chave, correção de relógio atrasado, HTTPS com validação TLS,
relatório nativo da apresentação, diagnóstico sem impressão de credencial e SSH
acessível após parar apresentação. Ambos os modos verificam avanço automático,
recuperação após encerrar processo e desligamento limpo. Hash do rootfs original
permaneceu igual após ensaios; provisionamento ocorre em cópia descartável.

Relatórios locais: `output/pi5-client/maintenance-qemu.json` e
`output/pi5-client/autostart-qemu.json`. Dependência `perl-open` foi instalada
somente no Toolbox de compilação para construir novos pacotes.

## Limites

QEMU usa kernel ARM64 virt genérico: não testa firmware físico, rádio Wi-Fi,
isolamento da rede CPPSUL-VISITANTES nem rota até 10.163.80.176.
Ausência de comunicação do Pi anterior continua sem causa física confirmada.
Próximo ensaio deve usar nova imagem provisionada e coletar `elo-diagnose` por SSH.
