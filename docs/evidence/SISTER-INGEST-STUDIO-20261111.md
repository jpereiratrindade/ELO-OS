# Recepção Sister-Studio e correção de publicação de imagem — 2026-11-11

## Recepção de consumíveis

Implementados receptor opt-in, spool privado com SQLite de submissões, limites,
idempotência por instalação/produção/versão, PUT de asset e commit com validação
PCM. Versões válidas terminam em quarentena (`editorial_integration_required`),
sem registro editorial e sem `consumable_id`. Cliente CLI valida e envia por HTTPS.
Tokens de terminal/admin não autorizam ingestão; token de ingestão não autoriza
editorial/distribuição. Consulta administrativa de recepção é somente leitura.

`python3 tests/network/ingest-test.py -v`: oito testes aprovados, incluindo
concorrência de 16 reenvios, conflitos de versão e chave, isolamento de produtor,
persistência após reabrir o spool, rejeição de áudio inválido, cotas, traversal,
symlinks, cabeçalhos duplicados e cliente CLI com TLS/hostname verificados.
Testes usam portas, credenciais, certificados e diretórios temporários.
Ingestão permanece desabilitada no serviço instalado.

## Defeito relatado no Studio

Adicionar imagem e publicar retornava conflito da versão `0.1.0` já selada.
O frontend apenas exibia erro, sem resolver a nova versão na ação de publicação.
Além disso, o botão do cabeçalho usava o plano do formulário oculto, potencialmente
diferente da aplicação exibida; variantes sem visual próprio ignoravam imagens
salvas em `modalities.image` do átomo.

Correções: diálogo explícito de nova versão com sugestão do próximo patch livre,
cancelamento sem sobrescrever publicação, preservação de seleção/metadados do
plano, verificação de mudança concorrente observável antes de salvar e tentativa
única de nova publicação. Não há incremento diante de erro de validação.
O cabeçalho usa sua aplicação exibida; projeção herda uma imagem padrão quando a
variante não define imagem ou vídeo. Imagem explícita prevalece.

`node tests/network/studio-publishing-test.js`: aprovado para conflito, cancelamento,
edição concorrente, validação, versão já usada e falha de gravação. Adaptador das
três ações do frontend instalado conferido e JavaScript validado com `node --check`.

`python3 tests/network/studio-image-publish-test.py`: aprovado com binário real
`../elo/build/apps/elo-admin/elo-admin`, workspace/SQLite/IPC/gateway temporários:

1. Publicação inicial `0.1.0`.
2. Upload de PNG e associação ao átomo por API editorial.
3. Helper JavaScript real recebe conflito pelo gateway e publica `0.1.1`.
4. Arquivos de `0.1.0` preservados byte a byte; projeção anterior sem nova imagem.
5. Nova imagem incluída na projeção e cache legível após parar o backend de teste.

`python3 tests/client/elo-import-test.py`: onze testes aprovados, incluindo herança
da imagem do átomo, prioridade da variante e recusa de seleção padrão ambígua.
`./tests/smoke.sh`: aprovado com regressões e novos testes de ingestão/Studio.

## Instalação da correção

Aplicada à cópia servida de `app.js`, sem mudar o repositório ELO ou o banco editorial.
O instalador deste repositório passa a reproduzir a adaptação, recusando formatos
de origem inesperados. Corrigida também a projeção de imagem no daemon instalado.

A primeira troca do módulo de importação usou o código atual do checkout sobre
módulos instalados mais antigos e causou falha por dependência `MAX_MEDIA` ausente.
Revertida imediatamente e substituída por patch de herança de imagem compatível
com o runtime existente. Verificados importação dos módulos, projeção da publicação
existente, reinício do serviço e leitura HTTPS do JavaScript corrigido. Backups
locais em `build/`; nenhuma credencial impressa ou versionada.

A aplicação do usuário não foi publicada automaticamente nem sua versão alterada.
Recarregar o navegador e confirmar **Publicar nova versão** conclui a publicação
por ação editorial explícita. Distribuição continua sendo uma seleção separada.

## Limites

Catálogo/revisão de consumíveis no ELO e integração do cliente ao Sister-Studio
permanecem pendentes. Recepção em quarentena não conclui os gates G1–G9 de áudio.
O teste de cache é de host; não demonstra reprodução física, percepção humana ou
homologação da Pi. A verificação de concorrência do frontend não substitui um
futuro contrato de atualização editorial com compare-and-swap no backend.
