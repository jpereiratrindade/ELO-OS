# ELO/OS — ensaio físico Pi 5 — AAAA-MM-DD

Estado: **NOT TESTED**. Preencher com observações reais e remover instruções deste modelo ao registrar o ensaio.

- Data/hora/fuso e operador:
- Modelo/revisão/RAM da placa:
- Fonte, microSD (modelo/capacidade), cabos, HDMI/teclado/serial:
- Revisão fonte da imagem (não presumir HEAD atual):
- Caminho, tamanho e SHA-256 da imagem gravada:
- Relatório `preflight.json` e método/resultado da verificação da gravação:
- EEPROM/bootloader e firmware (ou motivo de não coleta):
- Método de captura e caminho/hash do log bruto:

| Critério | Resultado (PASS / FAIL / NOT TESTED) | Saída observada / trecho do log |
| --- | --- | --- |
| Firmware, kernel e acesso ao login | NOT TESTED | |
| `uname -a`: aarch64 e kernel físico | NOT TESTED | |
| `/etc/elo-os-release`: identidade Pi 5 | NOT TESTED | |
| `/proc/1/comm` e `/proc/1/exe`: BusyBox init | NOT TESTED | |
| `/proc/cmdline`: raiz e console reais | NOT TESTED | |
| `/proc/mounts`: mmcblk0p2, ext4 e opções após init | NOT TESTED | |
| `/dev/mmcblk0*`: armazenamento | NOT TESTED | |
| IPv4 DHCP e rota com cabo conectado | NOT TESTED | |
| `free -k`: memória observada | NOT TESTED | |
| `dmesg`: erros e avisos registrados | NOT TESTED | |
| `poweroff`: término observado | NOT TESTED | |

Sem cabo/rede, manter DHCP como NOT TESTED e registrar o motivo. A raiz atual pode estar RW: não declarar imutabilidade. Login no HDMI não comprova console serial.

## Partidas frias

Copiar uma linha por ciclo até 30; incluir falhas e ligar cada registro ao log, imagem e hash correspondentes. Desligar de forma limpa antes de retirar alimentação.

| Ciclo | Data/hora/fuso | Imagem/hash | Console/login | PID 1/raiz | Rede | Shutdown | Duração/erro/log |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | |

## Resultado e limites

- Primeiro boot físico: NOT TESTED.
- 30 partidas físicas: NOT TESTED.
- Falhas, ações e pendências:
- Qt/vídeo acelerado, queda de energia, rootfs RO e recuperação: fora deste ensaio.

Somente promover o estado na [matriz de aceitação](../../docs/tests/acceptance.md) depois de revisar os logs e os critérios correspondentes do [roteiro](../../tests/boot/pi5-first-boot.md).
