# Confirmação de recebimento e apresentação

Acompanhamento atual por identidade e página: [Totens no servidor](terminal-monitoring.md).

Cliente atualizado envia estado autenticado para `POST /v1/receipt`, separado de
requisição de download. Painel consulta `/manage/delivery` a cada cinco segundos,
sem reconstruir formulário nem apagar uma seleção em edição.

Estados apresentados:

- **Sem confirmação do cliente**: nenhuma comunicação registrada.
- **Atualização pendente**: última comunicação não confirma conteúdo atualmente selecionado.
- **Recebido · aguardando Recomeçar**: conteúdo atual validado e publicado no cache;
  apresentação ainda é de outra publicação ou não foi confirmada.
- **Apresentação confirmada**: cliente informou frame correspondente ao hash exato
  da publicação atualmente selecionada.
- **Sem contato recente**: último relatório tem 90 segundos ou mais, ou horário do
  servidor ficou anterior ao registro. Não prova que apresentação offline parou.

Para participar, feche versão antiga do cliente e execute novamente, no Fedora,
dentro de ELO-OS:

```bash
./scripts/run-thin-client.sh
```

## Identificação do conteúdo e do frame

`JsonCatalog` calcula SHA-256 dos bytes validados e carrega esse identificador junto
ao conteúdo em memória. Não usa o `active.json` atual para adivinhar qual conteúdo
está sendo apresentado: esse apontador pode já referir uma atualização pendente.

Runtime copia identidade da apresentação durante `QQuickWindow::beforeSynchronizing`,
quando thread GUI está bloqueada. Após `frameSwapped`, encaminha snapshot por callback
à thread GUI e descarta confirmações de frames cujo conteúdo/página já mudou. Assim,
um callback atrasado de frame anterior não confirma o novo conteúdo apenas porque
o modelo já mudou. Este uso segue [contrato Qt](https://doc.qt.io/qt-6.5/qquickwindow.html#beforeSynchronizing).

Download só atualiza `received_sha256` depois de validação e persistência local.
`presented_sha256` só muda após confirmação do runtime. Ao iniciar com cache válido,
a própria apresentação confirma esse conteúdo mesmo se servidor estiver indisponível.
Fixture incorporada não recebe hash remoto nem gera confirmação de conteúdo ELO.

## Relatório 1

Usa a mesma credencial individual do terminal e a mesma configuração HTTPS do download.
Chave administrativa não pode enviar relatório; chave do terminal não pode consultar
administração. Corpo de até 2 KiB, sem texto, respostas pessoais, MAC ou IP persistido:

```json
{
  "schema": 1,
  "session": "UUID aleatório desta execução",
  "sequence": 1,
  "received_sha256": "64 caracteres hexadecimais ou vazio",
  "presented_sha256": "64 caracteres hexadecimais ou vazio"
}
```

Pelo menos um hash deve estar preenchido. Sequência inteira positiva até 2^53−1.
Reenvio idêntico da mesma sequência é idempotente e não renova horário de contato;
sequência antiga/conflitante na mesma sessão é recusada. Nova execução inicia sessão
aleatória nova. Credencial atual representa um único processo/terminal de bancada;
uso concorrente da mesma credencial em vários clientes não é suportado como inventário.

Mudança de estado agenda relatório após 50 ms; heartbeat após 30 s. Falhas repetem
em 5/10/20/40/60 s, com uma requisição de relatório por vez e prazo total de 15 s.
Eventos repetidos de frames com mesmo hash não causam um POST a cada frame.
Não segue redirects nem ignora erros TLS. Download e relatório têm timers separados;
falha de confirmação não impede apresentar conteúdo local.

Servidor persiste somente último relatório, com horário de recepção próprio, em
`$HOME/.local/share/elo-distribution/state/receipt.json`. Escrita atômica e fsync
preservam registro após reinício do daemon. Não mantém histórico crescente.
Cliente guarda estado de confirmação em memória e reconstrói a partir do cache e
do primeiro frame após reinício; não é fila durável de eventos de domínio.

Confirmação é declaração do cliente autenticado e progresso do caminho Qt. Não é
atestado de hardware nem prova de monitor físico ligado, percepção por uma pessoa
ou leitura de todas as páginas da publicação. Identidade persistente de equipamento,
múltiplos terminais e eventos/ACK do domínio continuam etapas próprias.

## Correção de ativação editorial

Também corrigido no checkout ELO: planos editoriais podem reter hash de publicação
anterior. Publicador agora calcula selo do snapshot após seleção dos átomos, antes
da validação desse snapshot. Validação continua obrigatória antes da ativação.
Diagnóstico de divergência passa a preservar hash esperado antes de limpar catálogo.

Versões imutáveis continuam protegidas. Quando `0.1.0` já foi publicada com conteúdo
diferente, edite aplicação, aumente para uma versão ainda não publicada, salve e ative.
Gateway apresenta instrução em português. Não incrementa versões automaticamente
nem substitui conteúdo já publicado.

Leitura e validação do workspace editorial mutável não comparam o rascunho ao selo
de uma versão anterior. Essa política é explícita nas rotas de autoria; leitura de
bundles publicados e verificação de integridade do cliente mantêm suas verificações.
Correções do ELO: commit `8204b39`.
