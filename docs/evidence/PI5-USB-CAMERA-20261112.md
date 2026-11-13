# Câmera USB no Pi 5 — 2026-11-12

## Instalação

Raspberry Pi 5 acessado por SSH pela rede Wi-Fi. O sistema reconhecia a câmera
USB `0c45:64ab`, produto `Integrated Camera`, mas não criava dispositivos V4L2.
O carregamento de `uvcvideo` criou `/dev/video0` e `/dev/video1`.

O perfil `pi5-client` foi recompilado com OpenCV 4.13.0, backend V4L2 e
`ELO_ENABLE_VISION=ON`. Multimídia permanece desligada. Foram transferidos
por SSH o cliente, as dependências adicionais e os modelos YuNet/SFace cujos
hashes estão documentados no roteiro audiovisual. A imagem completa também
foi reconstruída em `output/pi5-client/images/sdcard.img`; modelos e ativação
da câmera são provisionados separadamente.

O lançador lê `/etc/elo-terminal/camera.device`, carrega `uvcvideo` e configura
modelos em `/usr/share/elo-client/models`. A configuração instalada aponta
para `/dev/video0`. A versão anterior do cliente e do lançador foi preservada
no Pi em `/var/lib/elo-client/updates/before-vision-20261112`, diretório privado.

## Verificações

- Compilação ARM64 de OpenCV, cliente e verificador físico: PASS.
- Dependências ELF conferidas e arquivos transferidos verificados por SHA-256.
- Verificador usando o mesmo `PerceptionModel`/`VisionService` do cliente:
  três frames de prévia não vazios e três observações processadas pelo detector.
- Modelos carregados; reconhecimento não autorizado; nenhuma imagem salva.
- Cliente instalado: PID 5357 permaneceu estável, com frames de apresentação
  avançando de 4 para 54 e depois 392; descritor de `/dev/video0` aberto.
- Distribuição HTTPS confirmou recebimento de conteúdo após a troca.
- Nenhum cadastro `visits.json` foi criado. Diretório privado com modo 0700;
  configuração da câmera com modo 0600; arquivos instalados pertencem a root.
- Partição raiz com cerca de 268 MiB livres após instalação.

Logs e ferramentas locais de preparação estão em `build/pi5-provisioning/`:
`vision-build-20261112.log`, `vision-smoke-build-20261112.log`,
`vision-install-20261112.log` e `vision-final-20261112.log`.

## Limites

O ensaio físico confirmou captura e execução do detector, sem exigir rosto
presente. Não avaliou qualidade de detecção, reconhecimento de pessoas reais,
taxas de erro ou posição visual da prévia no monitor. Reconhecimento e cadastro
continuam exigindo adesão na interface. A sessão SSH foi mantida pela rede
Wi-Fi; não foi necessário remover o microSD nem reiniciar o Raspberry.
