# C6 — Imagem Pi 5 com início automático — 2026-11-10

## Artefato

`output/pi5-client/images/sdcard.img`, 570425856 bytes (aproximadamente 544 MiB).

SHA-256: `93e12e63d6b79b693fcf87c4f6eeffcff3e754cc747012e11c765ec704b07dac`.

Buildroot 2026.08.1, perfil `pi5-client`, Toolbox `elo-os`, 32 jobs.
Qt 6.11.2 recompilado com rede, SSL, PNG, JPEG e `qml_network` habilitado.
Cliente inclui monitoramento por página e verificação de compilação da capacidade
QML necessária para carregar imagens embutidas.

## Correções encontradas no ensaio

Build incremental tinha Qt Base sem Network/PNG/JPEG e Qt Declarative sem
`qml_network`. Após atualizar Base, Declarative antigo aceitava primeira página, mas
não carregava data URL da foto; supervisor detectava frames estagnados. Foram refeitos
Base/Declarative e ferramentas host dependentes. Ensaio final usa política de produção
padrão do supervisor, sem ampliar timeout para esconder problema.

Outro cache mantinha cmdline antigo da firmware. Hook de pós-build agora atualiza
`config.txt` e `cmdline.txt` em cada geração; imagem final contém `consoleblank=0`.

Preparação inicial do teste também foi corrigida: preserva executável ARM64 do rootfs
em vez de copiá-lo sem permissão de execução, e usa modos octais aceitos pelo debugfs.
Esses ajustes são do harness; não foram necessários no cliente instalado.

## Resultado

`tests/client/pi5-autostart-smoke.py`: PASS com rootfs Pi e kernel virt ARM64 genérico.

- Nenhuma NIC, mouse ou teclado virtual configurados.
- Serviço de boot iniciou supervisor e cliente sem comando manual de início.
- Cache provisionado isoladamente exibiu texto e JPEG editorial original.
- Sequência avançou à página 2 e retornou à 1, por exposição de 5 segundos.
- SIGKILL provocou novo processo; cliente voltou a apresentar página 2.
- Serviço parou e VM desligou sem erro.
- SHA-256 do rootfs original permaneceu
  `1070e506fab0da96ac41f2d6f69cb54b9fd2e99819431ac37dae264d735e696e`.

Relatório: `output/pi5-client/autostart-qemu.json`; log e capturas `autostart-*.ppm`
no mesmo diretório; foto também conferida visualmente em `autostart-image.png`. Serial administrativa foi usada para verificar saúde e encerrar VM;
não foram enviados eventos de mouse ou teclado ao cliente.

SSID escolhido: `CPPSUL-VISITANTES`; servidor: `10.163.80.176:8443`, HTTPS com IP no
certificado local. Credencial individual do Pi foi criada privadamente; roteiro local
`build/pi5-provisioning/configurar-pi.sh` recebe ponto de montagem e solicita senha sem eco.
Imagem base não contém senha Wi-Fi nem credencial operacional: precisa ser provisionada
antes de operação como totem.

## Limites

Não testa firmware/bootloader Pi, framebuffer físico, rádio Wi-Fi ou rota entre rede
visitantes e cabeada. Não havia cartão removível conectado; nenhum disco foi gravado.
Primeiro boot no Pi e ensaio de energia/rede continuam pendentes.

[Provisionamento](../client/terminal-provisioning.md).
