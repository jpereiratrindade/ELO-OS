# ADR-011 — Consumíveis Sister-Studio e fronteira editorial

Data: 2026-11-11. Decisão adotada para evolução; integração completa pendente.

## Contexto e decisão

Incorporamos [ELO-SISTER-BASES-001 v0.1.0](../ELO-SISTER-BASES-001_v0.1.0.md)
como documento de origem, preservado sem alterações e com seu status de proposta.
Este ADR adota a separação: Sister-Studio produz, ELO cataloga e compõe,
ELO-OS distribui apresentações compatíveis. O banco editorial canônico continua
no ELO. Ingestão não significa inclusão em átomo, publicação ou ativação.

O catálogo e a aceitação editorial dependem da integração com o serviço ELO.
O gateway recebe somente staging/quarentena autenticados. Não deve usar upload editorial
genérico como substituto de ingestão autenticada nem reutilizar tokens existentes.
MCP poderá encapsular o contrato de publicação, sem criar outra fonte editorial.

## Primeiro incremento implementado

Validador local somente leitura e esquema do perfil inicial PCM WAV, descritos em
[integração Sister-Studio](../client/sister-consumables.md). Não há novo endpoint,
catálogo concorrente, credencial criada ou modificação de serviços instalados.
Validação local não emite recibo `accepted` nem comprova direitos ou autoria.

## Segundo incremento implementado

Recepção opt-in no gateway ELO-OS, com token dedicado e identidade de instalação
configurada no servidor, staging, cotas, idempotência persistente, upload e commit.
Cliente de envio por HTTPS com verificação de certificado/hostname. Pacotes válidos
ficam em `quarantined`, aguardando integração editorial; nenhum `consumable_id` é
criado. `intake.sqlite3` registra somente submissões e chaves, fora do workspace
ELO. O catálogo canônico permanece pendente no ELO. Não gravamos em seu banco.

O transporte inicial usa manifesto JSON no POST, bytes WAV no PUT e commit vazio,
concretizando as operações separadas do documento-base; não usa multipart.
`validating` ocorre dentro do commit síncrono; os estados persistidos são `staged`,
`quarantined` e `rejected`. `accepted` será reservado à futura aceitação pelo ELO.

## Terceiro incremento: interfaces e transferência manual

Sister-Studio Composição exporta `elo-consumable-package/v1` por backend C++20,
sob ação e declarações explícitas do operador. ELO Studio recebe o arquivo pela
sessão administrativa, mostra as submissões e permite ouvir o áudio em quarentena.
Essa transferência de arquivo é o primeiro percurso pelas interfaces; não altera
a fronteira canônica nem substitui o futuro publicador outbound. A recepção instalada
foi habilitada com token exclusivo e identidade técnica `sister-studio-local`.

## Decisões para o receptor futuro

- Identidade: `(producer_instance_id, production_id, production_version)`, com
  instância derivada da credencial pelo servidor, nunca confiada ao manifesto.
- Repetição idempotente exige manifesto normalizado e hashes iguais. Alterar
  metadados ou bytes sob a mesma identidade/versão é conflito; exige nova versão.
- Bundles publicados fixam versões e hashes de consumíveis; atualizar o catálogo
  não altera publicações existentes. Reversão conserva referências resolvidas.
- A credencial dedicada terá `consumable:submit`; revisão, publicação editorial
  e atribuição de terminal seguem permissões distintas.
- Aprovação de direitos ocorre no ELO; campos declarados não demonstram licença
  válida, consentimento ou identidade pessoal.

## Continuidade e critérios

1. Implementar catálogo versionado e autorização no ELO, com migração própria.
2. Conectar staging/commit/recibos autenticados e exportador Sister-Studio.
3. Permitir associação editorial explícita a átomos e publicação de aplicação.
4. Executar áudio curto até distribuição, recebimento, reprodução, reinício
   offline e reversão, conforme G1–G9 do documento de origem.

Pré-validação cobre apenas parte das verificações de arquivos de G2. G1 e G3–G9
dependem dos sistemas integrados; nenhum gate completo é declarado concluído.
