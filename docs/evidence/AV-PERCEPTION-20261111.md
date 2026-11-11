# Áudio, vídeo e percepção local — 2026-11-11

## Entrega

O cliente ELO-OS ganhou publicação/projeção audiovisual v5, reprodução Qt
Multimedia a partir do cache offline e percepção facial opcional portada do
ELO anterior. O Estúdio ELO recebeu upload, prévia, listagem, vinculação e
serviço HTTP de vídeos MP4/WebM. Os códigos estão nos repositórios ELO-OS e ELO.

A implantação operacional não foi trocada: o binário novo está em
`build/client-av/elo-client` e o lançador de bancada é
`scripts/run-audiovisual-client.sh`. Câmera e reconhecimento exigem opções
explícitas. Autostart do cliente permanece desabilitado.

[Configuração e limites](../client/audiovisual-perception.md).

## Ambiente e resultados

- Fedora 44, Qt 6.11.2 e OpenCV 4.13.0 no container de desenvolvimento `elo-os`.
  Dependências instaladas apenas nesse container, sem alteração de pacotes do host.
- Build audiovisual/visão: passou.
- Build mínimo e regressão de núcleo/interface sem multimídia: passaram.
- 4 testes CTest do build audiovisual: núcleo, mídia, percepção e interface passaram.
- Regressão de interface após ajuste final de rótulos: passou.
- 21 testes de distribuição com cliente Qt real: passaram, incluindo áudio e vídeo
  recebidos por HTTPS, confirmação de apresentação e reinício com servidor desligado.
- 11 testes do painel, 9 de provisionamento, 10 de importação, 11 de conteúdo
  local e 4 específicos do formato audiovisual: passaram.
- Teste adicional de duração tardia: exposição de 5 segundos foi estendida para
  mídia de 7 segundos, sem corte na marca de 5 segundos.
- WAV/PCM real: validação de bytes, decodificação, progresso e pausa passaram.
- VP8/WebM real gerado pelo FFmpeg: pixels azuis renderizados, pausa e reinício
  passaram. Houve fallback de conversão para CPU no ambiente offscreen.
- ELO: build de elo-admin, ContentPublishing, ContentDatabase, AdminSecurity e
  StudioBrowserXss passaram. O upload de vídeo foi verificado com autenticação,
  caminho de destino e retorno HTTP com MIME correto.
- `git diff --check`, sintaxe Python/JavaScript e lançadores Bash: passaram.

## Câmera e reconhecimento

A câmera física **C270 HD WEBCAM**, em `/dev/video0`, foi aberta apenas pelo teste
explicitamente habilitado. O teste aguardou pelo menos três frames efetivamente
capturados e processados pelo detector YuNet. Os seis casos/etapas reportados pelo
executável de percepção passaram, sem skip nesse ensaio. Nenhum frame foi salvo.

Cadastro, persistência, retomada mediante confirmação, exclusão e rejeição de
correspondência ambígua foram exercitados com representações sintéticas. O teste
não cadastrou nem reconheceu uma pessoa real. Isso separa validação do mecanismo
de cadastro da avaliação de falsos positivos/negativos em uso real.

Reconhecimento só produz representações após adesão na tela e só persiste um
cadastro quando a pessoa escolhe lembrar a visita. Os dados ficam locais ao
totem, em arquivo privado, sem identificação civil e sem envio ao distribuidor.
Correspondência não serve como autenticação nem prova de vivacidade.

## Limites e próximos ensaios físicos

- Clipes limitados a 8 MiB por arquivo; apresentação completa a 32 MiB.
  Não é streaming de vídeo longo.
- MP3/OGG/MP4 dependem dos codecs instalados. Exercícios de decodificação desta
  etapa usaram PCM/WAV e VP8/WebM; não se declara que todos os codecs MP4 funcionem.
- Alto-falantes, iluminação/distância, reconhecimento entre pessoas reais,
  consentimento na instalação e taxas de erro ainda precisam de avaliação física.
- A geometria facial é uma estimativa de orientação, não evidência de atenção
  cognitiva, emoção ou compreensão.
- Nenhuma imagem Raspberry Pi foi recompilada. Os recursos opcionais no
  Buildroot foram declarados; boot, áudio e desempenho no Pi não foram validados.
