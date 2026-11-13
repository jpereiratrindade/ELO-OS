# Experiência audiovisual e percepção local

O cliente oferece reprodução de áudio/vídeo publicada pelo Estúdio ELO, cache
validado para operação offline e percepção facial opcional, reaproveitada do
ELO anterior. A câmera não é exigida para apresentar conteúdo. O lançador audiovisual da bancada ativa a câmera local por padrão;
reconhecimento ainda exige adesão na tela. O executável direto requer `--camera`.

## Recursos implementados

- WAV, MP3 e OGG para áudio; MP4 e WebM para vídeo. Os codecs devem estar
  disponíveis no backend Qt Multimedia; foram exercitados PCM/WAV e VP8/WebM.
- Texto com imagem e áudio, ou texto com vídeo, mantendo navegação manual
  e sequência automática. Silenciar/ativar som está disponível na interface.
- A exposição automática aguarda a mídia ficar pronta e usa, no mínimo,
  a duração informada pelo player. Uma troca de página ou volta do ciclo
  reinicia a mídia; pausa por orientação mantém a posição de reprodução.
- YuNet para detecção e geometria facial; SFace para representações locais.
  A estimativa usa orientação/permanência do rosto, não comprova atenção
  cognitiva, compreensão, emoções ou identidade civil.
- Cadastro voluntário de visita neste totem, confirmação antes da retomada,
  posição da página por publicação e exclusão do cadastro pela pessoa.
  A retomada é da página, não do instante exato de áudio/vídeo.

## Publicar conteúdo

No Estúdio ELO atualizado, edite um átomo, envie áudio ou vídeo em
**Ativos Multimodais** e salve. Vídeos têm upload, prévia, listagem e
vinculação ao átomo. Desvincular vídeo não apaga o arquivo; a biblioteca de
mídias mantém a ação de exclusão existente.

Publique uma versão editorial, selecione a variante no painel de distribuição
e publique a seleção. O projetor usa `presentation.media`; quando a variante
não define áudio/vídeo, usa `modalities.audio` ou `modalities.video` do átomo.
Combinações ambíguas são recusadas em vez de descartar mídia silenciosamente.
Para a primeira versão, selecione um vídeo ou uma imagem com um áudio por página.

Cada arquivo audiovisual tem limite de **8 MiB**, cada imagem de **2 MiB** e
cada apresentação completa de **32 MiB**. São clipes locais, não streaming de
vídeos longos. SHA-256 e tipo de contêiner são verificados antes da ativação.
Integridade não substitui autenticação do servidor nem comprova decodificação.

A apresentação usa formato local `5`; versões 1–4 continuam compatíveis.
A mídia fica no pacote imutável do cache e é materializada em diretório
privado temporário do processo. Reinício offline reconstrói esses arquivos
sem consultar o servidor. Não são aceitas URLs externas no player.

O cliente anuncia `audiovisual-v5` somente quando compilado com esse recurso.
Clientes antigos ou sem multimídia recebem HTTP 409 quando a seleção a exige,
conservando seu cache anterior. Atualize o cliente antes de distribuir mídia.

## Executar na bancada Fedora

O container `elo-os` desta bancada recebeu Qt Multimedia, OpenCV e FFmpeg.
O lançador a seguir compila e executa dentro dele, mantendo o runtime e o
binário audiovisual separados do cliente instalado anteriormente:

```bash
./scripts/run-audiovisual-client.sh
```

Ele reutiliza servidor, credencial e cache configurados por `run-thin-client.sh`.
Não execute simultaneamente dois clientes usando a mesma identidade de terminal.
O lançador abre `/dev/video0` com os modelos locais do ELO anterior e mostra
prévia no canto superior direito, incluindo contorno e estado do rosto.
Reconhecimento e cadastro continuam dependendo de adesão na tela. Para executar
sem câmera, use `ELO_CAMERA=off ./scripts/run-audiovisual-client.sh`.
`ELO_CAMERA` seleciona outro dispositivo; `ELO_VISION_MODEL_DIR` seleciona o
diretório dos modelos. Argumentos explícitos de câmera/modelos têm precedência.
Ausência do detector desativa a câmera com aviso; nenhuma dependência é baixada.
Não altera autostart nem substitui o binário instalado. Não use como `ExecStart` do
supervisor: a entrada em container modifica a árvore de processos observada.

Para percepção e reconhecimento opcionais:

```bash
./scripts/run-audiovisual-client.sh \
  --camera /dev/video0 \
  --detector-model "$PWD/../elo/build/models/face_detection_yunet_2023mar.onnx" \
  --recognizer-model "$PWD/../elo/build/models/face_recognition_sface_2021dec_int8.onnx" \
  --recognition-store "$HOME/.local/share/elo-client/private/visits.json" \
  --attention-playback
```

Os caminhos de modelos acima reutilizam os arquivos já provisionados no ELO
anterior. Não há download de modelos durante o build do cliente. A origem e
os SHA-256 fixados constam no CMake do ELO anterior:

- YuNet 2023mar: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
- SFace 2021dec int8: `2b0e941e6f16cc048c20aee0c8e31f569118f65d702914540f7bfdc14048d78a`.

`--attention-playback` pausa mídia e exposição enquanto uma câmera operacional
não indica rosto orientado à tela. Sem essa opção, a percepção não interfere
na sequência. Ausência/falha de câmera mantém reprodução; nova tentativa de
abertura ocorre em cinco segundos após falha de captura.

Escolha **Reconhecer visitas** para autorizar reconhecimento nesta visita.
**Lembrar visita** grava um cadastro local. Uma correspondência mostra
**Retomar visita** ou **Confirmar visita**; não retoma automaticamente.
**Apagar cadastro** remove o cadastro confirmado deste totem.
Ausência confirmada do rosto ou presença de múltiplas pessoas desliga a
autorização da visita. Sem adesão não são produzidas representações biométricas.

## Persistência e limites de reconhecimento

A prévia usa frames transitórios em memória, sem arquivos ou envio pela rede; o cliente não persiste fotografias, não exporta
representações e não as inclui na telemetria de distribuição. O cadastro
contém identificador aleatório local, representação SFace, hash do modelo,
hash da publicação e página. O arquivo tem permissão 0600 e deve ficar em
diretório privado, fora do Git. Não é um identificador civil nem autenticação.

O hash do modelo impede misturar galerias de modelos diferentes. São aceitos
até 128 cadastros; similaridade mínima 0,50 e margem 0,08 entre candidatos,
reaproveitando os critérios conservadores do ELO anterior. Correspondências
fracas/ambíguas não retomam visitas nem permitem cadastro a partir da hipótese
incerta. A qualidade de imagem mínima e rosto único são exigidos na captura.

Não há prova de vivacidade nem garantias contra apresentação de fotografias.
O reconhecimento não concede acesso, não controla autorização administrativa
e não substitui confirmação humana. Iluminação, distâncias, múltiplas pessoas
e taxas de falso reconhecimento precisam de avaliação com pessoas reais.

## Build e Raspberry Pi

As opções CMake `ELO_ENABLE_MULTIMEDIA` e `ELO_ENABLE_VISION` são independentes
e ficam desligadas no build mínimo. As dependências são Qt 6 Multimedia e
OpenCV core/imgproc/objdetect/videoio/dnn. O núcleo textual continua independente.

No Buildroot, habilite os recursos opcionais de `elo-client` depois de
configurar Qt Multimedia/FFmpeg e os módulos OpenCV correspondentes.
Na etapa inicial de 2026-11-11, nenhuma imagem Pi foi recompilada. Reprodução, áudio físico,
desempenho térmico, câmera e consentimento no painel Pi precisam de validação
física; testes na workstation não demonstram esse funcionamento.

### Câmera USB no perfil Pi 5

O perfil `pi5-client` agora habilita `ELO_CLIENT_VISION` e OpenCV com V4L2.
Multimídia continua sendo uma opção independente. Para ativar a câmera em um
terminal, instale os dois modelos ONNX de hashes listados acima em
`/usr/share/elo-client/models/` e grave `/dev/video0` no arquivo
`/etc/elo-terminal/camera.device`. Não são baixados modelos no boot.

O lançador carrega `uvcvideo` antes de iniciar o cliente, configura a prévia e
usa `/var/lib/elo-client/private/visits.json` para cadastros voluntários.
Remover `camera.device` desativa a câmera na próxima partida do cliente.
Reconhecimento exige adesão na interface; ativar câmera não autoriza cadastro.
O comando `/etc/init.d/S50elo-client restart` reaplica a configuração.

Em 2026-11-12, o cliente ARM64 com visão foi instalado por SSH no Pi 5.
A câmera USB `0c45:64ab` passou na captura de frames e no processamento do
detector; o cliente instalado abriu `/dev/video0` e manteve a renderização.
[Evidência e limites do ensaio](../evidence/PI5-USB-CAMERA-20261112.md).

## Validação reproduzível

```bash
python3 tests/client/audiovisual-launcher-test.py
python3 tests/client/audiovisual-content-test.py
python3 tests/client/elo-import-test.py
python3 tests/client/local-content-test.py

toolbox run -c elo-os env QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  QT_MEDIA_BACKEND=ffmpeg ctest --test-dir build/client-av --output-on-failure

toolbox run -c elo-os env ELO_AV_TEST=1 \
  ELO_CLIENT_BIN="$PWD/build/client-av/elo-client" \
  python3 tests/network/distribution-test.py
```

Os testes de mídia geram WAV e vídeo VP8 reais; conferem decodificação, pixels,
pausa e reinício. O teste de distribuição usa HTTPS e servidor reais, verifica
capacidade, recebimento e apresentação, encerra o servidor e reinicia o cliente
para áudio e vídeo offline. Dados e credenciais são isolados.

Cadastro, correspondência, ambiguidade e apagamento usam representações
sintéticas. A captura/detecção foi exercitada na C270 com adesão explícita do
teste (`ELO_TEST_CAMERA`/`ELO_TEST_DETECTOR`); nenhum cadastro real foi feito.
Ouvir o alto-falante, reconhecer pessoas reais e calibrar a orientação no
ponto de instalação continuam verificações físicas distintas.

O Estúdio ELO tem testes de upload/serviço de vídeo, publicação e segurança.
A implantação operacional exige atualizar o Estúdio e o distribuidor com os
instaladores existentes; esta etapa não troca automaticamente as instalações
nem habilita serviços. O cliente continua sem autostart.
