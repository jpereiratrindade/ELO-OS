---
document_id: ELO-SISTER-BASES-001
title: "Integração de consumíveis Sister-Studio → ELO → ELO-OS"
version: 0.1.0
status: proposed
created_at: 2026-11-11
scope: "contrato de ingestão, catálogo reutilizável, composição editorial e distribuição offline-first"
repositories:
  sister_studio: https://github.com/jpereiratrindade/sister-studio
  elo: https://github.com/jpereiratrindade/ELO
  elo_os: https://github.com/jpereiratrindade/ELO-OS
---

# ELO-SISTER-BASES-001 — Bases para consumíveis e composição de aplicações

**Status:** PROPOSTA PARA DISCUSSÃO. O presente documento descreve uma arquitetura-alvo; não afirma que a API aqui proposta já existe nem que os marcos de implementação foram concluídos.

## 1. Decisão fundamental proposta

**O Sister-Studio produz e entrega artefatos reutilizáveis; o ELO atribui significado editorial e compõe aplicações; o ELO-OS distribui e apresenta versões compatíveis dessas aplicações.** A integração não deve duplicar o estúdio editorial existente no ELO nem transformar o Sister-Studio num editor específico de totens.

A produção de um artefato é distinta de sua incorporação ao catálogo, de sua inclusão numa aplicação, da publicação da aplicação e da ativação/distribuição para terminais.

### 1.1 Fluxo

```text
Sister-Studio
  ├── composição de áudio / voz / vídeo / legendas
  ├── revisão humana e exportação de artefato
  └── publicação explícita (contrato ingest-v1)
                  ↓
ELO Server — fronteira de ingestão autenticada
  ├── staging e validação (hash, MIME, tamanho, licença, escopo)
  ├── recibo de aceitação, rejeição ou quarentena
  └── registro de produção/versão imutável
                  ↓
ELO Studio — editorial existente
  ├── navega produções disponíveis
  ├── associa produções a átomos ou cria novos átomos
  ├── monta aplicação com seleção parcial ou integral de átomos
  ├── define variantes, ordem, interações e público
  └── publica versão editorial imutável (bundle ELO)
                  ↓
ELO-OS Server — distribuição existente
  ├── seleciona versão e variantes compatíveis
  ├── atribui publicação para cliente(s) conforme políticas
  └── acompanha recibos de recebimento/apresentação
                  ↓
ELO-OS Client — cache validado e operação offline
```

## 2. Estado observado nos repositórios em 2026-11-11

- **Sister-Studio:** README e `docs/architecture.md` descrevem composição procedural em C++20, síntese de voz, FFmpeg, WAV/OGG/MIDI, SRT e MP4. O modo operacional compartilha workspace local sem login/senha; APIs LAN não devem ser expostas à internet. Uma API de publicação para ELO não foi demonstrada na documentação inspecionada.
- **ELO:** `docs/CONTENT_MODEL_V0.2.md` já estabelece **átomo** (registro canônico e reutilizável, `content_id`), **aplicação** (seleção e configuração editorial, `atom_ids`), **bundle** (snapshot imutável publicado). SQLite/WAL é fonte do editorial mutável; JSON é projeção técnica; salvar, publicar e ativar são estados diferentes.
- **ELO-OS:** `docs/client/server-panel.md` descreve o gateway e painel local de distribuição com Estúdio ELO existente. `docs/client/distribution.md` documenta contrato HTTPS de apresentação e isolamento das credenciais de terminal e administração; `docs/client/delivery-receipts.md` distingue recebimento de apresentação; `docs/client/audiovisual-perception.md` documenta audiovisual experimental (formato local 5), limite de 8 MiB por mídia A/V e 32 MiB por apresentação, condicionado a codecs/capacidades. Testes de workstation não homologam Pi físico.
- **Lacuna concreta:** a ingestão versionada de produções externas do Sister-Studio para a biblioteca editorial ELO, com rastreabilidade e autorização apropriadas, ainda precisa de contrato próprio.

## 3. Vocabulário canônico

| Termo | Identidade e propriedade | Pode ser reutilizado? | Pode ser entregue diretamente ao cliente? |
| --- | --- | --- | --- |
| **Projeto de origem** | Estrutura editável do Sister-Studio | Sim, na ferramenta de origem | Não por padrão; requer formato/runtime autorizado |
| **Artefato de produção** | Render ou arquivo gerado, com hash, versão e direitos | Sim | Somente via composição/publicação compatível |
| **Consumível catalogado** | Registro de artefato aceito pelo ELO, com metadados e origem | Sim | Não automaticamente |
| **Átomo ELO** | Unidade semântica com `content_id` | Sim, em várias aplicações | Mediante inclusão numa aplicação |
| **Aplicação ELO** | Configuração editorial de uso, com `atom_ids` e variantes | Sim, versionada | Após publicação/distribuição |
| **Bundle editorial ELO** | Snapshot selado e imutável da aplicação | É uma versão específica | Sim, após projeção de capacidades |
| **Apresentação ELO-OS** | Projeção validada para capacidade de cliente | Concreta por seleção | Sim; cache offline |

**Importante:** consumível não substitui o átomo. Um áudio pode ser usado por vários átomos; um átomo pode empregar várias mídias e variantes. A composição explicita a relação. O projeto editável pode ficar no Sister-Studio, enquanto o ELO recebe seus derivados publicáveis.

## 4. Invariantes propostas

1. **Separação de responsabilidades.** Sister-Studio não controla o domínio, a identidade ou a ativação do ELO; ELO-OS não é editor de artefatos.
2. **Publicação explícita.** `salvar`, `renderizar`, `publicar artefato`, `incluir na aplicação`, `publicar aplicação` e `distribuir` não são sinônimos.
3. **Sem destino obrigatório no artefato.** A ingestão deve ser independente de uma aplicação. O produtor pode sugerir usos (hints), nunca impor destino.
4. **Reuso por referência.** Uma mesma produção pode ser vinculada a vários átomos/aplicações sem duplicação lógica. Bundles distribuídos mantêm seus próprios snapshots fechados.
5. **Identidades distintas.** `production_id`, `consumable_id`, `content_id`, `bundle_id`, `device_id` e identidade do ator não são intercambiáveis.
6. **Integridade e origem separadas.** SHA-256 valida bytes; não autentica autoria. Autenticação decorre do canal e credencial; autoria editorial requer registro verificável.
7. **Imutabilidade das versões aceitas.** Mesmo ID+versão+hash implica reenvio idempotente; mesmo ID+versão com bytes diferentes é conflito.
8. **Falhas preservam o ativo.** Importação, validação ou distribuição inválida jamais substitui a última versão funcional.
9. **Capacidade explícita.** Ausência de codec, interação ou recursos impede entrega dessa variante; não há conversão silenciosa nem simulação de suporte.
10. **Offline-first.** Aplicação já entregue continua operando sem servidor, com vínculos versionados completos.
11. **Segurança e direitos por padrão.** Sem envio de perfil de clonagem, credenciais, caminhos locais ou dados pessoais por padrão. Direitos de mídia e voz são verificados antes de disponibilizar.
12. **Evidência operacional graduada.** Aceito no catálogo ≠ vinculado à aplicação ≠ distribuído ≠ recebido ≠ apresentado ≠ percebido pelo visitante.

## 5. Elementos de conteúdo — perfil inicial

### 5.1 Classes de consumível

- `media.audio`: WAV/OGG/MP3 conforme validação concreta do destino, duração, canais, codec, idioma, licença e transcrição opcional.
- `media.video`: MP4/WebM conforme capacidades, resolução, duração, legendas e direitos.
- `media.image`: PNG/JPEG e texto alternativo.
- `text.narrative`: texto puro/Markdown saneado, idioma, fontes e revisão editorial.
- `media.subtitle`: SRT, idioma e referência ao áudio/vídeo (a aceitação do arquivo **não significa** que o cliente já renderize legendas externas).
- `project.source`: composição editável e dependências próprias da origem; fora do escopo de execução do ELO-OS v1.
- `experience.interactive`: reservado para futuros manifestos declarativos/contratos de runtime; **não aceita executáveis arbitrários** na primeira versão.

### 5.2 Uso parcial/total

A aplicação escolhe `atom_ids` explicitamente, como já previsto no modelo ELO v0.2. Dentro do átomo, variantes escolhem mídias e modos de apresentação. O importador preserva o registro integral e seu histórico; a publicação da aplicação resolve um subconjunto fechado e verificável de referências. Não enviar ao terminal toda a biblioteca do produtor.

### 5.3 Semântica não deve ser inferida pela extensão

`MP4` identifica um contêiner, não uma experiência: pode servir como demonstração didática, ambientação ou apresentação comentada. Propósito, contexto, ordem, duração, interatividade e público pertencem à composição editorial ELO.

## 6. Contrato de ingestão proposto: `elo-consumable-ingest/v1`

Este contrato é **novo e proposto**. Não substitui `/v1/presentation`, `/v1/receipt` nem as APIs editoriais atualmente documentadas.

### 6.1 Manifesto exemplificativo

```json
{
  "schema": "elo-consumable-ingest/v1",
  "production_id": "prod_8b7e1f3a",
  "production_version": "1.0.0",
  "producer": {
    "system": "sister-studio",
    "release": "declarar-versao-real"
  },
  "title": "Paisagens sonoras dos campos",
  "description": "Locução e paisagem sonora para composição editorial",
  "language": "pt-BR",
  "suggested_uses": ["ambientacao", "educacao"],
  "assets": [
    {
      "asset_id": "audio-principal",
      "role": "primary",
      "kind": "media.audio",
      "filename": "paisagem.wav",
      "mime": "audio/wav",
      "size_bytes": 480000,
      "sha256": "SUBSTITUIR_PELO_SHA256_REAL_DE_64_HEXADECIMAIS",
      "duration_ms": 5000
    }
  ],
  "provenance": {
    "declared_creator": "equipe-produtora",
    "source_project_ref": "referencia-opaca-da-origem",
    "reviewed": true
  },
  "rights": {
    "license": "licenca-a-definir",
    "rights_holder": "titular-a-definir",
    "voice_permission": "not-applicable"
  },
  "privacy": {
    "classification": "public",
    "purpose": "catalogo-editorial-e-distribuicao"
  }
}
```

O JSON é ilustrativo e **não é pacote pronto**: `sha256`, licença, identidade e permissões devem ser substituídos por valores válidos. O formato deverá receber JSON Schema, restrições de tamanho, canonicalização e testes de compatibilidade antes de ser aceito.

### 6.2 API recomendada

| Operação proposta | Finalidade | Efeito |
| --- | --- | --- |
| `POST /v1/ingest/submissions` | Criar submissão, registrar manifesto/idempotency key | Reserva um staging; não publica |
| `PUT /v1/ingest/submissions/{id}/assets/{asset_id}` | Enviar bytes de cada artefato | Valida tamanho, digest, formato e limites |
| `POST /v1/ingest/submissions/{id}/commit` | Finalizar e pedir validação | Marca aceito, rejeitado ou pendente/quarentena |
| `GET /v1/ingest/submissions/{id}` | Consultar recibo/status | Informa versão, razões de recusa e registro criado |
| `GET /v1/consumables` | Navegação interna autorizada do catálogo | Permite seleção pelo Studio ELO |

*Versão 1 pode usar uma única transação HTTP multipart para arquivos pequenos, mas deve manter as mesmas propriedades de idempotência, staging e resultado. O contrato deve abstrair essa escolha.*

### 6.3 Resultado de publicação

```json
{
  "schema": "elo-consumable-receipt/v1",
  "submission_id": "sub_6a3c4e",
  "status": "accepted",
  "consumable_id": "con_17aa2b",
  "production_id": "prod_8b7e1f3a",
  "production_version": "1.0.0",
  "rejections": []
}
```

Estados mínimos: `staged`, `validating`, `accepted`, `rejected`, `quarantined`. Uma aceitação no catálogo não significa associação a átomo nem publicação de aplicação. Falhas devem ter códigos estáveis, detalhes públicos mínimos e logs técnicos protegidos.

## 7. Segurança e governança

**Fronteira crítica:** o Sister-Studio opera atualmente na LAN com workspace compartilhado e sem autenticação individual. Essa premissa **não** autoriza que toda estação na LAN publique no ELO. A publicação deve ser feita por adaptador outbound dedicado, com credencial própria, escopo mínimo e HTTPS verificado. Token de terminal ELO-OS é *somente* para o cliente e nunca pode publicar; token administrativo geral também não deve ser reutilizado para ingestão.

- Criar permissão `consumable:submit` distinta de `consumable:review`, `application:publish` e `terminal:assign`.
- Identidade do publicador autenticado deve vir do servidor; `declared_creator` do manifesto é **declaração**, não prova de identidade pessoal.
- Em ambiente LAN compartilhado, submissões podem ser atribuídas a uma instalação técnica; aprovação por pessoa identificada deve ocorrer no ELO quando necessária.
- Diretório staging fora da raiz de conteúdo servido; não seguir symlinks, `..` ou URLs fornecidas pelo produtor; negar executáveis por padrão; aplicar cotas, limites de MIME e conteúdo.
- Rejeitar mídia sem direitos adequados, perfil de clonagem, dados pessoais não autorizados ou texto sensível conforme classificação e finalidade. Não presumir que voz sintética ou áudio derivado é irrestrito.
- Definir retenção para rejeitados, versões antigas, derivados e conteúdo revogado. Não excluir artefatos ainda referenciados por bundles publicados sem política de expiração/retirada correspondente.
- Auditoria de submissões e aprovações sem armazenar segredos nem material pessoal desnecessário.
- Hash fornece integridade; assinaturas/autenticação forte de proveniência só devem ser alegadas quando implementadas e verificadas.

## 8. Interface proposta

### 8.1 Sister-Studio

Em cada projeto/render elegível: **Revisar → Publicar no ELO → Ver resultado**. Painel de estado mostra versão, arquivos, licença, destino lógico (catálogo), recibo e erros; não apresenta um botão genérico que publique automaticamente ao salvar. Permite nova versão sem sobrescrever a anterior.

### 8.2 Studio ELO (editorial existente)

Adicionar uma seção **Biblioteca de consumíveis** com origem, mídia, prévia quando suportada, direitos, versão, dependências e usos existentes. Permitir **Vincular a átomo existente** ou **Criar átomo a partir da produção**. Na aplicação, selecionar átomos, variantes, ordem e apresentação; sinalizar o que é usado e o que fica de fora. Diferenciar claramente **Salvar rascunho**, **Publicar versão** e **Distribuir/Ativar**.

### 8.3 ELO-OS Server

Manter a distribuição da aplicação compatível e seus recibos. O endpoint do terminal não aceita uploads. Compatibilidade é negociação pelo cliente e projeção editorial, preservando cache anterior em erros.

## 9. Primeiro experimento vertical: áudio curto

**Por que áudio curto?** É uma produção genuína do Sister-Studio, o cliente ELO-OS já documenta WAV em bancada experimental, e o pacote pode ficar abaixo de 8 MiB. O SRT eventualmente produzido acompanha a origem como metadado, mas não é pressuposto que tenha renderização no cliente.

1. No Sister-Studio, gerar e revisar locução/trilha WAV curta, de direitos controlados; atribuir `production_id` e `1.0.0`.
2. Publicar via contrato de ingestão em servidor ELO de ensaio; conferir hash, autorização e recibo.
3. No ELO Studio, associar a um átomo existente e criar uma aplicação `experimento-paisagem-sonora` que usa esse átomo e mais um átomo textual preexistente.
4. Publicar a aplicação v0.1.0; confirmar que só as seleções resolvidas compõem o bundle.
5. No painel de distribuição, selecionar versão/variante compatível e distribuir a um cliente de teste.
6. Verificar recebimento, frame apresentado, reprodução audiovisual (conforme testes do player) e reinício offline.
7. Atualizar somente o áudio de origem para `1.0.1`, sem alterar a aplicação ativa; depois publicar a aplicação v0.1.1 por ação explícita.
8. Reativar v0.1.0 e verificar restauração, sem confundir reversão de aplicação com mudança do projeto-fonte.

### 9.1 Gates de aceitação

- **G1 Identidade e repetição:** mesmo payload e chave não duplicam artefato; versão conflitante é rejeitada.
- **G2 Segurança:** token de terminal não autoriza submissão; submissão sem credencial é rejeitada; traversal/symlink/asset divergente são recusados.
- **G3 Semântica:** artefato aceito fica disponível no catálogo sem se autoativar; pode ser usado por duas aplicações com contextos distintos.
- **G4 Seleção:** a aplicação inclui apenas os átomos e assets realmente referenciados; dependências ausentes bloqueiam publicação.
- **G5 Compatibilidade:** ausência de `audiovisual-v5` impede entrega da variante A/V sem destruir cache anterior.
- **G6 Offline:** cliente validado permanece utilizável sem servidor após reinício; arquivo ou hash corrompido não substitui o ativo.
- **G7 Estado observável:** telas distinguem aceito, incluído, publicado, distribuído, recebido, apresentado; apresentação não significa atenção humana.
- **G8 Reversão:** versão editorial anterior pode voltar a ser ativada e mantém referências resolvidas.
- **G9 Direitos:** mídia sem licença/permissão exigida não entra no catálogo liberado.

## 10. Organização por repositório (sem duplicação de responsabilidade)

| Repositório | Alteração proposta | Não deve fazer |
| --- | --- | --- |
| `sister-studio` | Exportador e publicador; pacote de metadados; histórico de submissão/recibos | Definir `atom_ids` de uma aplicação ELO ou ativar terminais |
| `ELO` | Inventário/editorial de produções externas; associação a átomos, variantes, aplicações; migração/validação de modelo | Virar um serviço de renderização audiovisual do Sister-Studio |
| `ELO-OS` | Gateway/serviço de ingestão ou adaptador de acesso ao ELO, distinto das rotas de cliente; distribuição existente | Criar segundo banco editorial canônico concorrente ou aceitar upload via token de terminal |
| Contrato compartilhado | JSON Schema, fixtures, especificação de versionamento e testes end-to-end | Fazer os três sistemas dependerem uns dos diretórios internos dos outros |

**Decisão de implementação a validar:** a API pública de ingestão pode terminar no gateway ELO-OS e encaminhar ao serviço editorial ELO (proposta mais coerente com painel existente), ou terminar diretamente num serviço ELO dedicado. Em ambos os casos, **a fonte editorial canônica permanece ELO**; nenhuma ingestão deve gravar diretamente em `editorial.sqlite3` a partir do Sister-Studio.

## 11. Sequência de implementação

**Fase A — Definição**: aprovar taxonomia mínima de consumíveis, esquema e semântica de versões; registrar ADR de fronteiras e ameaças.

**Fase B — Ingestão**: adaptador exportador Sister-Studio, staging autenticado, validação, recibos e catálogo de produções externas no ELO.

**Fase C — Composição**: biblioteca de consumíveis no Studio ELO, vínculo para átomos, publicação editorial com seleção explícita.

**Fase D — Distribuição**: reaproveitar a publicação ELO e o servidor ELO-OS existentes; ensaio com mídia de curta duração em desktop, negociação e cache offline.

**Fase E — Generalização**: vídeo, imagens, legendas quando suportadas, múltiplos ativos/variantes, importação em lote, grupos de terminais e casos interativos declarativos. Executáveis e projetos fonte continuam fora do primeiro protocolo de entrega.

## 12. Decisões pendentes (não bloquear o primeiro experimento)

- A API de ingestão fica fisicamente no gateway ELO-OS, num adaptador ELO ou em serviço separado?
- Direitos/licenças mínimos para voz gerada/clonada, imagens, música e textos.
- Mapeamento inicial: uma produção → ativo vinculável a vários átomos; confirmar regras para importação automática de átomo versus criação editorial.
- Tamanho máximo e transcodificação: transcodificar no produtor, não assumir codec só pela extensão.
- Capacidade de legendas como recurso de acessibilidade: ingestão SRT não implica renderização SRT.
- Estratégia de retenção de originais, renders, hashes e referências quando um consumível for revogado.
- Compatibilidade e métricas no Pi real permanecem gate físico separado dos testes Fedora/QEMU.

## 13. Critério de êxito constitutivo

Não consideraremos o experimento concluído ao provar que um arquivo foi enviado com HTTP 200. A demonstração requer que a **mesma produção identificada** entre no catálogo, seja **selecionada editorialmente** em pelo menos uma aplicação, seja **publicada e distribuída de modo compatível**, tenha **recebimento/apresentação verificáveis** e continue disponível **offline**, com histórico e reversão controlados.

---

## Referências primárias de projeto consultadas

- Sister-Studio: [`README.md`](https://github.com/jpereiratrindade/sister-studio/blob/main/README.md), [`docs/architecture.md`](https://github.com/jpereiratrindade/sister-studio/blob/main/docs/architecture.md), [`docs/governance/DATA_PROTECTION.md`](https://github.com/jpereiratrindade/sister-studio/blob/main/docs/governance/DATA_PROTECTION.md).
- ELO: [`docs/CONTENT_MODEL_V0.2.md`](https://github.com/jpereiratrindade/ELO/blob/main/docs/CONTENT_MODEL_V0.2.md), [`README.md`](https://github.com/jpereiratrindade/ELO/blob/main/README.md).
- ELO-OS: [`docs/client/server-panel.md`](https://github.com/jpereiratrindade/ELO-OS/blob/main/docs/client/server-panel.md), [`docs/client/distribution.md`](https://github.com/jpereiratrindade/ELO-OS/blob/main/docs/client/distribution.md), [`docs/client/delivery-receipts.md`](https://github.com/jpereiratrindade/ELO-OS/blob/main/docs/client/delivery-receipts.md), [`docs/client/audiovisual-perception.md`](https://github.com/jpereiratrindade/ELO-OS/blob/main/docs/client/audiovisual-perception.md).
