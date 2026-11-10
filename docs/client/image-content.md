# Cliente com texto e imagem

Primeira capacidade visual além de texto: uma imagem PNG ou JPEG por página, com
texto alternativo, download validado e cache offline. Compatível com variantes
ELO `interaction: none`; não converte perguntas, áudio, vídeo ou receitas em texto.

## Usar no Fedora

1. Feche cliente antigo e execute `./scripts/run-thin-client.sh`, dentro de ELO-OS.
2. Abra `https://localhost:8443/`, entre e Atualizar.
3. Variante **Campos Sulinos** (`var_campos_ambient_01`) agora está habilitada e
   identificada como **Texto + imagem**. Selecione páginas desejadas e publique seleção.
4. Cliente consulta servidor em até 30 segundos. Clique Recomeçar para apresentar
   atualização recebida. Foto permanece disponível após reinício sem servidor.

Seleção original do operador não foi modificada por esta entrega. Uma prévia local
independente já importada nesta bancada pode ser aberta com:

```bash
./scripts/run-client.sh --content-dir "$PWD/build/elo-image-content"
```

Essa prévia contém foto original publicada dos Campos Sulinos, não arte gerada.
Não usa nem altera cache operacional de `run-thin-client.sh`.

## Contrato e limites

- Envelope de distribuição continua schema 1. Catálogo local passa a aceitar versões
  `1` (texto) e `2` (texto com imagem opcional em cada página).
- Página com imagem mantém `title` e `body` e acrescenta `image` com exatamente
  `mime`, `base64`, `sha256` e `alt`.
- Imagem vem dos arquivos já incluídos no hash nativo do bundle ELO. Referência
  deve existir em `assets/`; caminhos externos, absolutos, travessia e mídia não
  suportada são recusados.
- PNG e JPEG somente, até 2 MiB de bytes por imagem. Alt obrigatório até 512 bytes
  UTF-8; usa `accessibility.alt_text` do átomo ou título da variante como alternativa.
- Qt confere hash dos bytes, dimensões e decodificação completa antes de publicar
  cache. Máximo 4096 por eixo e 8 Mi pixels. Arquivo que parece imagem pelo cabeçalho
  mas não decodifica é recusado. Não há acesso a URL remota pelo componente visual.
- Catálogo completo até 8 MiB; resposta até 16 MiB. Até 32 páginas, mantendo limites
  de título/corpo. A base64 conta no tamanho do catálogo; 32 imagens de tamanho máximo
  não cabem e são recusadas. Limites de espaço disponível e bundles do cache continuam.
- Conteúdo e imagens ficam no mesmo JSON validado/hasheado, portanto sua ativação
  permanece atômica. Nenhum arquivo auxiliar pode faltar depois da publicação local.
- Cliente anuncia `X-ELO-Capabilities: text-v1,image-v2`. Servidor exige `image-v2`
  antes de entregar catálogo com imagens. Cliente antigo recebe HTTP 409 e preserva
  cache anterior, em vez de aceitar conteúdo que não consegue apresentar.

Exemplo de página, omitindo os bytes completos da imagem:

```json
{
  "title": "Campos Sulinos",
  "body": "Texto editorial da variante.",
  "image": {
    "mime": "image/jpeg",
    "sha256": "hash hexadecimal dos bytes originais",
    "base64": "bytes originais em base64",
    "alt": "Paisagem dos campos"
  }
}
```

Hash da apresentação cobre imagem embutida e metadados. Digest do frame também
incorpora hash da imagem. Runtime só confirma apresentação depois de Image.Ready
no frame correspondente, mantendo distinção entre recebimento e apresentação.

Layout lado a lado em janela larga, empilhado em janela estreita; leitura tem
rolagem quando necessário. Imagem preserva proporção e não fica armazenada no cache
visual do QML entre páginas. Consultas de rede/estado não reiniciam posição de leitura.

## Painel e autoria

Painel verifica compatibilidade de cada variante pelo mesmo projetor de distribuição,
em vez de recusar toda variante que menciona mídia. A prévia administrativa continua
sendo do texto e informa descrição da imagem incluída; não finge exibir a imagem.

Upload e publicação editorial continuam no Estúdio existente. Apenas anexar imagem
ao átomo não faz essa foto aparecer em todas as variantes: a variante precisa
referenciá-la em `presentation.media`. Não houve mudança nos dados editoriais.

## Verificação e escopo

Build Qt nativo, testes de importação, testes Qt com verificação de pixel, download
HTTPS e reinício offline foram executados. Imagem com hash divergente, dimensão
excessiva ou bytes inválidos não substitui cache anterior. Foto JPEG original também
passou por importação e apresentação; captura em `build/client-campos-sulinos.png`.

Kconfig habilita PNG/JPEG em Qt nos perfis com cliente. Não foi recompilada imagem
Buildroot nem validado Pi 5. Desempenho/memória desses limites ainda precisam de ensaio
na plataforma embarcada. Áudio, vídeo, múltiplas imagens por página e interações
permanecem recusados. [Evidência desta entrega](../evidence/C1-IMAGE-CLIENT-20261110.md).
