# Cliente — contratos locais experimentais

Esta entrega implementa os protótipos T-203/T-205/T-209/T-210/T-211 do [IMPL-002](../ELO-OS-IMPL-002_v0.1.0.md). O código Qt/C++ novo aguarda compilação e validação no desktop; os testes Python/shell têm evidência separada. Não há contrato de servidor, conteúdo pessoal, HTTPS, sessão autenticada ou estado ONLINE operacional.

## Portas e adaptadores

`core/ports.hpp` define `LocalStore`, `NetworkStatus`, `Clock`, `PresentationPort` e `Diagnostics`; `ContentCatalog` permanece no núcleo. Os consumidores são, respectivamente: catálogo JSON, observador Linux de interfaces, política de eventos/saúde, registro de frames e diagnóstico explícito das transições. O núcleo não abre arquivos nem sockets; adaptadores são injetados. A apresentação e o controlador continuam no mesmo processo.

O frontend observa interface ativa, com link e endereço IPv4/IPv6, excluindo loopback. Isso significa disponibilidade **local**, sem testar DNS, Internet ou autenticação. Perda posterior à apresentação produz DEGRADED_OFFLINE e preserva a página; ausência inicial de rede permite READY_LOCAL quando a fixture e a apresentação forem válidas. O botão de nova tentativa só fica disponível em ERROR_RECOVERABLE. Textos de conteúdo são apresentados como texto simples.

## Ativação de fixture no host

`scripts/elo_content.py` é ferramenta de desenvolvimento Python/stdlib para Linux; não é instalada na imagem. O formato de teste contém `schema: 1`, `id`, `name`, `version: "1"` e `pages` com `title`/`body`. Limites em bytes UTF-8: ID 128, nome 256, título 256, corpo 4096, 1–32 páginas; arquivo completo até 256 KiB. NUL não é aceito nos textos. Tamanho/SHA-256 esperados são argumentos obrigatórios do operador.

```text
content-root/
  .activation.lock
  bundles/<sha256-do-payload>/
    manifest.json
    presentation.json
  active.json                  # {"bundle": "<sha256>"}
```

A publicação serializa escritores com `flock`, escreve arquivos em staging no mesmo filesystem, sincroniza, relê e valida os bytes, publica o diretório imutável e sincroniza diretórios. Um único `active.json` temporário é sincronizado e substituído via `rename`, seguido de `fsync` do diretório. Leitores usam um único marcador e encontram um bundle completo anterior ou novo; múltiplos arquivos não são tratados como uma transação de vários renames.

Falha antes da troca do marcador preserva o ativo anterior. Falha após a troca, antes de confirmar durabilidade, retorna `ActivationUncertain`/código CLI 3: o novo ativo pode já estar visível; é preciso reler/reconciliar. Não se anuncia rollback automático nesse caso. Bundles anteriores permanecem disponíveis para reativação explícita e não há coleta automática. SHA-256 prova integridade em relação aos metadados fornecidos, sem autenticar autoria.

`QtLocalStore` relê o marcador/manifesto, restringe o identificador do diretório, limita leituras e confere tamanho/hash. `JsonCatalog` adapta JSON para o domínio; o núcleo valida versão e limites antes de permitir READY_LOCAL. `--content-dir` habilita esse caminho explicitamente. A opção padrão continua sendo a fixture incorporada. Não há hot reload, instalação persistente em `/data` ou atualização de SO.

Os testes de falha usam diretório descartável e exceções injetadas, inclusive após publicação; não simulam fisicamente queda de energia. O diretório de conteúdo pertence ao operador confiável e deve permanecer sem escritores externos ao protocolo.

## Eventos idempotentes de teste

`core/events.hpp` define `EventLedger`: chave opaca não vazia até 128 bytes, payload opaco não vazio até 4096 bytes, tentativa, prazo monotônico e confirmação local. Mesma chave/payload retorna duplicate; payload divergente retorna conflict e preserva o original, inclusive após confirmação. Até 256 chaves são retidas; lotação é explícita, sem expulsão silenciosa.

O relógio é injetado. Prazos de reenvio são 1, 2, 4 e 8 segundos até cinco tentativas; um evento esgotado permanece diagnosticável, sem envio infinito. ACK local exige a mesma chave/payload e é idempotente. Esta é uma política **em memória**, exercitada por testes C++ ainda não executados nesta entrega. Reiniciar o processo perde o ledger; não há fila durável, transporte ou alegação de idempotência do servidor. O protótipo não coleta eventos da navegação da fixture.

## Saúde e supervisão

O supervisor shell pertence somente ao overlay dos perfis gráficos QEMU. Executa o cliente, mantém PID próprio e PID do filho em diretório privado e exclui outra instância no mesmo diretório com `flock`, já habilitado no BusyBox fixado. O lock é liberado pelo kernel ao terminar o supervisor e não é herdado pelo cliente. O protocolo utiliza:

```text
ELO_HEALTH_V1 geração pid boottime_ms sequência estado página digest_sha256
```

O frontend solicita atualização a cada dois segundos e publica o registro atomicamente **após `frameSwapped`**, com sequência crescente. `Clock` e `/proc/uptime` usam o mesmo domínio CLOCK_BOOTTIME. O digest identifica fixture/versão e texto da página, sem gravar seu conteúdo no registro. A geração muda a cada processo e evita aceitar arquivos antigos como saúde do novo cliente; não é credencial de autenticação.

O supervisor requer PID/geração corretos, horário recente, estado conhecido e avanço da sequência. Timestamp atualizado com contador parado não basta. Inicialização: até 30 s; perda de progresso: 7 s; SIGTERM com graça de 2 s antes de SIGKILL. Reinícios usam backoff 1/2/4/8/16/30 s, com até cinco reinícios por janela móvel de 300 s; 60 s de saúde contínua restauram o atraso inicial, mantendo o orçamento da janela.

Ao esgotar o orçamento, encerra com código 1 e diagnóstico `give-up` no log. Não reinicia VM, não aciona watchdog e não reinicia por ausência de rede. Uma tela de erro responsiva conta como apresentação viva, mas seu estado continua ERROR_RECOVERABLE/ERROR_FATAL e não vira READY_LOCAL. Não se promete tela de diagnóstico após falha do próprio supervisor.

`/run/elo-client/{supervisor.pid,child.pid,health}` são temporários; logs ficam em `/run/elo-client.log`. SIGTERM ao supervisor encerra/recolhe o filho e remove os registros. O serviço continua como root na bancada. Esta política não é homologação de produção nem prova com a aplicação Qt real antes da validação no desktop.
