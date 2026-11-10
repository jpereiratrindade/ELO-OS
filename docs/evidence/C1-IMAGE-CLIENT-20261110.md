# Texto e imagem no cliente — 2026-11-10

Base ELO-OS `b225390` mais alterações desta entrega. ELO permanece no commit
`8204b39`, sem novas alterações de fonte ou dados editoriais nesta etapa.

## Implementação

Catálogo local v2 carrega uma imagem PNG/JPEG por página com hash e alt. Formato v1
preservado para texto. Bytes da imagem incorporados ao JSON: envelope, download,
ativação atômica e cache incluem todos os recursos necessários à apresentação.
Qt verifica dimensões/decodificação antes da ativação; confirmação de frame exige
imagem pronta. Formato v2 só é entregue a cliente que anuncia `image-v2`.

Layout MORFO com foto/texto lado a lado ou empilhados e rolagem. Painel foi atualizado
para selecionar variantes compatíveis com foto e indicar imagem na prévia textual.
Daemons reinstalados/reiniciados; seleção vigente do operador mantida.

## Provas

- Build nativo concluído e núcleo/UI testados por CTest.
- Nove testes do importador passaram, incluindo nova projeção de imagem e recusa
  de mídia ausente, externa, múltipla ou incompatível e divergência de hash.
- Integração testa download HTTPS de PNG, bloqueio de cliente sem capacidade,
  confirmação de frame e reinício sem servidor com mesma apresentação.
- Bytes inválidos de imagem, mesmo com hash do envelope correto, preservam cache.
- Teste Qt cria PNG vermelho, verifica pixel no frame, alt, imagem pronta e recibo;
  imagem de 4097 pixels de largura e hash corrompido são recusados.
- Foto JPEG original `assets/images/Campos-Sulinos.jpg` importada do bundle real:
  1.349.572 bytes, 2576×1920, com preenchimento FF após marcador final. Bytes e
  hash originais preservados, sem transformação da foto ou alteração no ELO.
- SHA-256 do catálogo projetado real:
  `001951722877f198797946189a4f236845ed8eb42a6b48b763d4eaaea3f94bf9`.
- Teste Qt com `ELO_IMAGE_CONTENT_DIR=build/elo-image-content` aplicou publicação
  real na janela, confirmou prontidão e salvou `build/client-campos-sulinos.png`.
  Frame inspecionado: foto e texto legíveis no mesmo cartão.
- Navegador contra daemon instalado confirmou que variante real Campos Sulinos
  está selecionável e marcada Texto + imagem. Não publicou seleção diferente.
- Smoke, Kconfig dos oito perfis e diff check executados.

## Limites

Testes visuais offscreen/software no Fedora. Sem rebuild Buildroot, boot ou homologação
Pi 5 nesta etapa. Nenhuma alegação de suporte ao domínio ELO completo. Imagens de
publicações diferentes não são buscadas como URLs externas; imagem e texto pertencem
a um único payload autenticado e validado. Privacidade/procedência editorial continuam
responsabilidade do ELO e do provisionamento da instalação.

Resultado final: 14 testes de distribuição passaram (13,18 s), incluindo imagem por
HTTPS e bytes inválidos preservando cache. CTest 2/2 passou após layout final (8,13 s).
Smoke passou com nove casos do importador e oito casos do painel; Kconfig passou nos
oito perfis. Ambos os daemons ativos ao concluir; checkout ELO permanece limpo.
