# Totem sem mouse: exposição programável

No painel de distribuição, marque **Avançar automaticamente e repetir sequência**
e informe **Tempo de exposição por página**, entre 5 e 3600 segundos. Publique
seleção. Tempo é comum a todas as páginas da sequência; não altera versão editorial.

Cliente atualizado entra no modo automático sem clique local, mesmo se estava
apresentando cache manual. Avança páginas e repete sequência continuamente. Mudanças
recebidas durante reprodução entram ao terminar ciclo. Configuração e conteúdo ficam
juntos no cache: sem servidor, continuam funcionando após reinício.

Contagem começa depois de confirmar frame com imagem pronta. Navegação manual fica
oculta. Variantes reveal exibem texto/imagem automaticamente na entrada, durante todo
tempo de exposição; não há espera por toque. Texto longo rola automaticamente até fim,
reservando aproximadamente último segundo para leitura final. Operador deve escolher
tempo suficiente para leitura do conteúdo. Não há dependência de mouse ou teclado.

Abra cliente atualizado na bancada com:

```bash
./scripts/run-thin-client.sh --fullscreen
```

Nesta bancada, modo automático foi ativado com **15 segundos por página**,
preservando variantes selecionadas. Alterações seguintes dependem de publicação no painel. Para voltar ao
modo manual, desmarque reprodução automática e publique; troca ocorre no fim do ciclo.
Instalações que ainda não escolheram modo automático preservam comportamento anterior.

## Contrato e validação

Formato local 4, schema 1, acrescenta `exposure_seconds` inteiro entre 5 e 3600.
Cliente anuncia `autoplay-v4`, além das capacidades de texto, imagem e reveal.
Servidor recusa entrega a cliente sem capacidade necessária (HTTP 409).
Alterar duração altera hash da apresentação e seu recibo de entrega. Hash editorial
original é preservado. Relatório de apresentação não registra respostas ou toques.

QTimer de precisão controla exposição por página. Quadro anterior permanece até
próxima página pronta; tempo efetivo pode aumentar por carga/renderização do sistema.
Não há garantia de temporização de tempo real. Atualização aguarda ciclo completo,
que pode durar quantidade de páginas multiplicada pelo tempo configurado.

Testes Qt verificam espera por frame, expiração apesar de frames repetidos e mudança
de rede, navegação automática, aplicação de atualização, controles ocultos e rolagem.
Integração verifica entrada a partir de cache manual sem mouse e continuidade offline.
Imagem `pi5-client` recompilada e testada com kernel ARM64 virtual, sem rede ou
periféricos de entrada. [Evidência](../evidence/C6-PI5-AUTOSTART-20261110.md).
Validação física no Pi 5 permanece pendente.

[Reinício automático após falha e lançador supervisionado](supervised-playback.md).
