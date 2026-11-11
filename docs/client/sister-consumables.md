# Sister-Studio → ELO → ELO-OS

O Sister-Studio entrega produções reutilizáveis; o ELO atribui significado editorial,
seleciona átomos e publica aplicações; o ELO-OS distribui apresentações compatíveis.
Decisão: [ADR-011](../adr/ADR-011-sister-consumables.md).
Base integral: [ELO-SISTER-BASES-001](../ELO-SISTER-BASES-001_v0.1.0.md).

## Disponível neste repositório

Pré-validação local somente leitura, usando Python 3 sem dependências adicionais:

```bash
python3 scripts/elo_consumable.py /caminho/do/pacote
python3 tests/network/consumable-test.py
```

O diretório deve conter somente `manifest.json` e o WAV referenciado pelo manifesto.
O [JSON Schema](../contracts/elo-consumable-ingest-v1.schema.json) descreve o perfil
inicial de `elo-consumable-ingest/v1`: um áudio PCM de 16 bits, mono ou estéreo,
16/22,05/24/44,1/48 kHz, até 60 segundos e 8 MiB. Manifesto até 64 KiB.
O teste gera um pacote válido de exemplo com áudio sintético, sem arquivos binários
versionados. O JSON do documento de origem contém placeholders e deve ser preenchido.

O perfil exige revisão declarada, licença/titular não vazios e declaração de
permissão de voz `granted` ou `not-applicable`. Isso não aprova direitos: valores
como placeholders ainda exigem revisão editorial. A referência ao projeto é um
identificador opaco restrito, sem caminhos ou URLs. Campos extras são recusados.

O validador confere tamanho, SHA-256, estrutura PCM, duração e ausência de arquivos
extras; recusa symlinks, arquivos especiais e nomes com caminhos. O diretório é
selecionado por operador confiável; ancestrais do caminho pertencem a essa fronteira
local. Não é uma sandbox para processar uploads concorrentes de terceiros.

Sucesso retorna `validated_locally`, identificadores e hashes; erro retorna
`invalid_package` com saída 1. Nenhum arquivo é importado, publicado ou ativado.
O hash de manifesto usa JSON com chaves ordenadas, separadores compactos e escapes
ASCII, sem quebra de linha. Não é uma implementação geral de JCS. Os limites de
texto em bytes UTF-8 e a integridade dos arquivos são verificações adicionais ao
Schema. SHA-256 não autentica o produtor.

## Recepção autenticada implementada, opt-in

O gateway pode receber o perfil WAV com credencial exclusiva `consumable:submit`.
Permanece desabilitado sem configuração explícita. Para habilitar numa instalação,
acrescente `--enable-ingest --ingest-producer studio-laboratorio` ao comando normal
de `scripts/install-content-service.py`, preservando os argumentos de bundle,
variantes, host e certificado da instalação. O instalador cria `ingest.token`
privado ao lado das outras credenciais e spool em `state/ingest`.
Na continuidade de 2026-11-11, a recepção foi
habilitada no serviço instalado para `sister-studio-local`. A identidade vem da configuração
do servidor; não é aceita do manifesto. Rotação de token conserva essa identidade.

Ao iniciar manualmente `scripts/elo_server.py`, acrescente os três argumentos:

```text
--ingest-token-file /diretorio-privado/ingest.token
--ingest-root /diretorio-privado/intake
--ingest-producer studio-laboratorio
```

O token deve existir, ter 32–128 caracteres alfanuméricos/`_`/`-` e permissões 0600.
O spool é privado (0700), separado do workspace e da raiz web. Não há autoexposição
de seu conteúdo. Uma instalação produtora por configuração; escopos de revisão,
publicação e atribuição a terminais não são concedidos a essa credencial.

| Método e rota | Corpo / resultado |
| --- | --- |
| `POST /v1/ingest/submissions` | Manifesto JSON direto, `Content-Type: application/json`, `Idempotency-Key` obrigatório; cria `staged` (201) ou retorna a submissão existente (200). |
| `PUT /v1/ingest/submissions/{id}/assets/{asset_id}` | Bytes WAV, `Content-Type: audio/wav`, tamanho e hash exatos. |
| `POST /v1/ingest/submissions/{id}/commit` | Corpo vazio; valida PCM; retorna `quarantined` ou `rejected`. Ausência do asset: 409, mantendo `staged`. |
| `GET /v1/ingest/submissions/{id}` | Recibo persistente da própria instalação. |
| `GET /manage/ingest` | Resumo de recepção, somente com token administrativo. |

Mutações exigem um único `Content-Length`; rejeitam Transfer-Encoding, Origin de
navegador e credenciais de terminal/admin. Uma versão pertence à tupla instalação,
produção e versão. Mesmo manifesto normalizado pode ser reenviado com a mesma chave
ou outra chave. Outra chave não permite sobrescrever uma versão. Reuso de chave com
outro manifesto ou alteração de metadados/bytes sob a mesma versão retorna 409.
Após commit, PUT idêntico apenas devolve o recibo; não reescreve o arquivo.

O SQLite `intake.sqlite3` guarda **estado de recepção**, nunca átomos ou catálogo
editorial. Bytes são escritos com staging, fsync e troca atômica; conexões são
serializadas entre threads/processos. Submissões e recibos sobrevivem ao reinício.
Cotas iniciais: 128 submissões, 256 MiB reservados e até 512 chaves, incluindo
rejeitados. Limites não são liberados automaticamente: ao saturar, 429 exige
manutenção do operador; expiração/retirada automática fica pendente. Arquivos
temporários de escrita interrompida são removidos ao abrir o spool.

**Quarentena não é catálogo.** O recibo contém `consumable_id: null` e
`pending_reason: editorial_integration_required`. Não existe transição para
`accepted`, listagem `/v1/consumables` ou associação a átomo neste receptor.
Direitos continuam sendo declarações que precisam de revisão editorial no ELO.

## Cliente de envio explícito

```bash
python3 scripts/publish-consumable.py /caminho/do/pacote \
  --endpoint https://servidor:8443 \
  --token-file /diretorio-privado/ingest.token \
  --certificate /caminho/ca-ou-certificado-confiado.crt
```

Valida o pacote, cria/reobtém a submissão, envia o áudio e solicita commit. A chave
é derivada do manifesto normalizado; repetir o comando após falha recupera a mesma
submissão. Verificação TLS e hostname permanecem habilitadas; não segue redirects.
Emite o recibo sem imprimir credenciais. Saída 0 com `quarantined` significa apenas
entrega à recepção. HTTP simples é permitido exclusivamente com
`--allow-loopback-http --endpoint http://127.0.0.1:PORTA` para desenvolvimento.

## Fluxo visível pelas interfaces

1. No Sister-Studio **Composição**, use **Exportar composição para ELO**, ou
   **Exportar para ELO** numa composição do histórico. Preencha título, versão,
   licença/titular e confirme revisão. O backend C++20 produz um arquivo `.elo.json`.
2. No ELO Studio, abra a aba **Produções Sister-Studio**, ou o botão superior
   **Receber do Sister-Studio**. Selecione o arquivo e clique **Receber produção**.
3. Confira versão, duração, direitos declarados e estado; **Ouvir produção recebida**
   reproduz o WAV por uma requisição administrativa autenticada.

O envelope `elo-consumable-package/v1` contém somente `schema`, `manifest` e
`asset_base64`. O manifesto segue o contrato já descrito. A exportação manual não
envia credenciais, perfis, caminhos ou projetos do Sister-Studio ao ELO. Voz e Vídeo
oferecem um atalho **Composições → ELO**; a exportação inicial é instrumental.

`POST /manage/ingest/import` aceita o envelope por sessão administrativa e executa
pré-validação, staging, upload e commit. Essa é uma importação explícita do operador,
distinta das rotas de submissão por credencial do produtor. Tokens de terminal e de
ingestão não autorizam essa rota. `GET /manage/ingest/{id}/audio` devolve somente
áudio revalidado em quarentena, com autenticação administrativa. Nenhum arquivo
privado é servido por rota pública ou por cookie de mídia editorial.

Pacotes válidos aparecem como **Recebida — aguardando integração editorial**.
Essa recepção não cria um consumível canônico, um átomo ou uma aplicação.
Não há sincronização automática: o operador exporta e importa o arquivo escolhido.
Recarregar normalmente o ELO Studio carrega o JavaScript com identificador de versão.

## Ainda necessário para entrega completa

Catálogo versionado e revisão no ELO, associação a átomos e publicador outbound
no Sister-Studio para dispensar a transferência manual. Os gates G1–G9 e o experimento
vertical de áudio continuam pendentes; os testes de recepção cobrem apenas a
fronteira de envio, validação e quarentena. Aceitação futura no catálogo não autoriza
ativação.

Vídeo, outras mídias e múltiplos assets permanecem na arquitetura-alvo; o perfil
inicial restrito não implica suporte desses recursos. Testes de host não homologam
reprodução ou operação offline na Pi física.

[Evidência de recepção e correção do Studio](../evidence/SISTER-INGEST-STUDIO-20261111.md).
[Evidência das interfaces e do fluxo manual](../evidence/SISTER-VISIBLE-20261111.md).
