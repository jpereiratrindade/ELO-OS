# Confirmações e correção editorial — 2026-11-10

Implementação experimental no host. Dois objetivos da continuidade: confirmação real
de recebimento/apresentação no painel e correção de falha reportada pelo operador na
ativação de aplicações.

## Correção ELO

Alterados no checkout relacionado `../elo`: `src/content/content_bundle.cpp`,
`src/content/content_catalog.cpp` e `tests/test_content_publishing.cpp`.

Causa: plano pode reter selo anterior; seleção de átomos muda bytes do staging.
Validação prévia comparava staging com selo antigo. Publicador passa a selar novo
snapshot antes da validação. Mensagem antes exibia esperado vazio porque limpava
catálogo antes de construir diagnóstico; agora usa cópia preservada.

Binário `elo-admin` recompilado. Regressão de seleção com selo anterior e diagnóstico
adicionada. CTest ELO: ContentSystem, ContentPublishing e AdminSecurity passaram (3/3).

Em cópia descartável dos dados reais, ativação de `app.elo.teste` passou; duas outras
aplicações chegaram à proteção legítima de versão existente com conteúdo diferente,
sem erro de integridade. Em nova cópia descartável, plano `elo-content-pampa` foi
salvo como 0.1.1 e ativado com HTTP 200. Não alterados dados editoriais originais ou
versões do operador. Serviço editorial reiniciado com binário corrigido.

## Confirmação de entrega

- Identidade do payload validado carregada junto ao conteúdo em memória.
- Snapshot do frame associado antes da sincronização e confirmado após frameSwapped;
  callback atrasado não confirma modelo mais novo.
- Relatórios autenticados, separados para recebido e apresentado; último estado
  persistido no servidor, sem texto ou identificadores pessoais.
- Painel acompanha estado e horário a cada cinco segundos sem perder seleção em edição.

Testes: oito casos do painel passaram; doze casos de distribuição passaram, incluindo
cliente Qt real. Novos casos distinguem download de apresentação, verificam persistência,
sequência/idempotência, autenticação e expiração. CTest cliente: 2/2 passaram (8,48 s).

Daemon HTTPS instalado foi atualizado. Cliente Qt de ensaio, com bundle real do ELO,
emitiu confirmação de frame aceita e persistida; `/manage/delivery` passou a presented.
Processo de ensaio foi encerrado; marcador passa a sem contato recente após expiração
se nenhum cliente atualizado continuar enviando relatórios.

Navegador Chromium/Playwright verificou exibição da confirmação real e que consulta
periódica não remarca checkbox desmarcado pelo operador. Captura local:
`build/server-panel-delivery.png`. Isso não representa monitor físico Pi 5 nem prova
de que uma pessoa leu conteúdo.

## Correção complementar — catálogo editorial vazio

Após novo relato do operador, confirmado `GET /api/catalog` retornando 500 por
comparar workspace editável exportado do SQLite com selo de versão anterior.
API de leitura do rascunho e validação editorial passam a usar explicitamente
`IntegrityPolicy::Skip`, mantendo validação estrutural e de assets. Defaults do
catálogo/bundle e validação das publicações seladas permanecem inalterados.

Regressão em AdminSecurity cobre rascunho com selo antigo, leitura de átomos e
validação sem falso erro de integridade. Três testes ELO passaram novamente.
Backend recompilado e reiniciado; endpoint instalado voltou a HTTP 200 e cinco átomos.
Não foram incrementadas versões nem ativadas aplicações nos dados originais.
Correções do ELO registradas no commit `8204b39`.
