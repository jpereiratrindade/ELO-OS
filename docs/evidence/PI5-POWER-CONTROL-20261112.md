# Controle de energia do totem — 2026-11-12

## Entrega

Painel do servidor atualizado com ações Reiniciar e Desligar por totem compatível,
confirmação nominal e acompanhamento de recebimento. Servidor mantém comandos
expiráveis e vinculados à credencial individual; não usa SSH para executar as ações.

Agente ARM64 instalado por SSH no Raspberry Pi 5, com serviço independente
`S51elo-control`. Usa a configuração TLS existente, aceita apenas duas ações fixas,
registra identificadores consumidos de forma durável e confirma recebimento antes
de executar. A apresentação com câmera permaneceu no mesmo PID 5357 durante a
instalação e o reinício de teste do serviço de manutenção.

## Validação

- Compilações nativa e ARM64 do agente: PASS.
- Onze testes de controle: autenticação administrativa e por terminal, origem,
  destino, exclusão mútua, expiração, persistência, revogação e nova inicialização.
  Incluem três testes com agente Qt real e HTTPS, executor simulado: execução única
  com reentrega após reinício do agente, recusa após perda de confirmação e rejeição
  de certificado com nome incorreto. Nenhuma ação de energia real nesses testes.
- Onze testes existentes do painel: PASS.
- Chromium com API isolada: confirmação recusada não envia comando; confirmação
  aceita envia reinício/desligamento; estados pendente, offline e revogado bloqueiam
  ações; PC sem capacidade não mostra controles; sem erros JavaScript.
- Chromium no servidor operacional: ambos os botões habilitados somente no cartão
  do Pi; nenhuma ação enviada. Captura local em
  `build/pi5-provisioning/control-panel-live.png`.
- Reinício do serviço de manutenção no Pi: PASS; apresentação preservada, contador
  de frames avançando, nenhum comando consumido.
- Sintaxe Python, JavaScript, shell e `git diff --check`: PASS.

Logs locais de compilação e testes em `build/pi5-provisioning/control-*.log`.
Versão anterior dos módulos e arquivos web do servidor preservada em
`build/server-control-backup-20261112/`.

## Limites

Não foi solicitado reinício nem desligamento físico do Raspberry durante a entrega,
para preservar a apresentação em uso. Execução dos dois comandos foi validada com
executor simulado. A instalação operacional confirmou comunicação TLS, habilitação
das ações e independência do processo gráfico. Retorno real após reboot e atuação
elétrica de poweroff continuam sujeitos ao primeiro uso no hardware.

Não há ligação remota nem comprovação de desligamento por ausência de contato.
Depois de desligar, o operador precisa ligar novamente no próprio aparelho.
