# Pi 5 — primeiro ensaio físico P1

Estado: **preparado, não executado**. Use a imagem inventariada em [P1-BUILT-PI5](../../docs/evidence/P1-BUILT-PI5-20261108.md). O build e a auditoria não gravam mídia.

## Preparar e registrar

No Fedora, antes de gravar, execute na raiz do repositório:

```bash
python3 scripts/pi5-preflight.py > output/pi5/preflight.json
cat output/pi5/preflight.json
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINTS
```

Só prossiga se o primeiro comando terminar com código zero e o relatório indicar `PASS_IMAGE_PREFLIGHT`. A checagem abre somente o arquivo de imagem para leitura, compara o SHA-256 com o baseline de [P1-BUILT-PI5](../../docs/evidence/P1-BUILT-PI5-20261108.md), confere limites/sobreposição das duas partições MBR e assinaturas FAT/ext4. Não monta partições nem grava mídia. Não valida conteúdo de arquivos, firmware, consistência completa dos filesystems ou boot. O campo `physical_boot` continua `NOT_TESTED`.

Para uma imagem futura, use `--image CAMINHO --expected-sha256 HASH_DO_INVENTARIO`, depois de registrar sua origem e hash independentemente. Não substitua o hash esperado apenas para contornar uma divergência. Não execute durante um build. O relatório é emitido em stdout; em caso de erro, descarte o arquivo redirecionado vazio. Para reproduzir a checagem sem salvar, omita o redirecionamento.

1. Registrar data/hora/fuso, operador, revisão ELO/OS, SHA-256 da imagem, modelo/revisão/RAM da placa, fonte, microSD de teste, cabos, tela e teclado.
2. Conferir o hash com `PROFILE=pi5 ./scripts/inspect-image.sh` e identificar a mídia de destino por modelo, tamanho e número de série (`lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINTS`). Confirmar explicitamente o dispositivo antes de gravar; nenhum comando destrutivo com destino presumido é fornecido aqui.
3. Gravar a imagem completa com uma ferramenta de imagem, verificar a gravação e ejetar a mídia. Preservar a imagem original. Esta etapa depende de mídia identificada pelo operador.
4. Preparar HDMI/teclado e, se necessário, serial com adaptador/níveis elétricos adequados ao conector usado. A cmdline atual cita `ttyAMA10,115200`; não presumir disponibilidade sem conferir o hardware/firmware. Não conectar alimentação do adaptador serial por conveniência.
5. Ligar e capturar console desde o firmware até o login, incluindo erros. Registrar EEPROM/bootloader pelo que o hardware/firmware disponibilizar; se não houver ferramenta no sistema mínimo, marcar dado como não coletado em vez de inventar versão.

## Conferir no convidado físico

```sh
uname -a
cat /proc/1/comm
readlink /proc/1/exe
cat /etc/elo-os-release
cat /proc/cmdline
cat /proc/mounts
ls -l /dev/mmcblk0*
ip -4 addr show
ip route
free -k
dmesg
poweroff
```

Registrar arquitetura aarch64, BusyBox init, identidade Pi 5, raiz `mmcblk0p2`, estado real de montagem após init, console disponível, rede se conectada e desligamento. Não adicionar sudo, SSH, Qt ou watchdog para fazer esse ensaio passar. Sem rede conectada, separar teste de boot de teste DHCP.

## Registro de ciclos

Após o primeiro boot observado, executar 30 partidas frias com desligamento limpo, aguardando o encerramento antes de retirar alimentação. Isso testa partidas, não queda abrupta de energia. Registrar também todas as falhas.

| Ciclo | Data/hora | Imagem/hash | Console/login | PID 1/raiz | Rede | Shutdown | Duração/erro/log |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1–30 | NOT TESTED | | | | | | |

Salvar sumário em `docs/evidence/P1-PI5-AAAAMMDD.md`; logs extensos em `output/pi5/`. Ensaios de queda de energia ficam para protocolo separado com mídia de teste e verificação de integridade. Não alterar alinhamento, EEPROM ou hooks upstream durante o ensaio inicial.

Use o [modelo de evidência física](pi5-evidence-template.md) para o sumário. Um primeiro boot aprovado comprova apenas aquele ciclo; os 30 ciclos têm resultado próprio. O shutdown só pode ser confirmado após a mensagem final e o comportamento observado na placa, não apenas pela execução do comando `poweroff`.
