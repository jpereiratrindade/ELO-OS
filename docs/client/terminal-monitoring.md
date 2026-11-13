# Acompanhar totens no servidor

Painel de distribuição inclui **Totens → Acompanhamento da apresentação**. Cada
aparelho tem nome, credencial própria e último relatório independente.

Mostra publicação, título da última página confirmada, posição na sequência,
modo automático/manual, exposição programada, entrega pendente ou apresentada e
horário do último contato. Painel consulta estado a cada cinco segundos. Cliente
envia mudança de página após confirmação de frame com imagem pronta; mantém heartbeat
aproximadamente a cada 30 segundos. Não há transmissão de vídeo ou captura de tela.

**Contato recente** significa relatório recebido há menos de 90 segundos. Sem contato
recente não permite concluir que aparelho desligou: conteúdo pode continuar offline.
Última página conhecida permanece visível com horário, sem simular estado ao vivo.
Cliente anterior que só envia recibo schema 1 continua funcionando, com página não
informada até atualização.

## Identidades e provisionamento

PC mantém credencial original da bancada, identificado como **PC de testes**.
**Raspberry Pi 5 · CPPSUL** foi cadastrado separadamente; sua credencial privada está
em `~/.config/elo-distribution/pi5-terminal.token`, fora do repositório. Esse arquivo
já é utilizado pelo roteiro local `build/pi5-provisioning/configurar-pi.sh`.

Para outro aparelho: informe nome em **Cadastrar totem**, baixe credencial individual,
aplique `chmod 600` no arquivo e forneça-o a `install-terminal.py --token-file`.
Credencial é entregue uma única vez; servidor guarda somente seu SHA-256. Não concede
acesso administrativo, upload ou publicação. Nunca coloque credencial administrativa
no terminal. Cada token autentica identidade escolhida pelo servidor, não por campo
livre no relatório.

**Revogar credencial** impede novas consultas e relatórios daquele aparelho, mantendo
último estado para acompanhamento. Cópia offline permanece no aparelho. Credencial
original do PC continua gerenciada pela instalação existente e não é revogada nessa UI.

Todos recebem seleção editorial compartilhada nesta etapa. Distribuição específica por
aparelho ou grupo ainda não foi implementada.

## Reiniciar e desligar

Totens Raspberry Pi com `elo-control-agent` ativo mostram **Reiniciar** e **Desligar**
no próprio cartão. As ações exigem a sessão administrativa do painel e confirmação
com o nome do aparelho. Desligar exige ligar novamente no aparelho; o painel não
oferece ligação remota. Clientes sem agente, como o PC desta bancada, não mostram
esses controles. Sem contato de manutenção há mais de 30 segundos, ficam desabilitados.

O serviço `/etc/init.d/S51elo-control` funciona independentemente do cliente gráfico,
consulta o servidor por HTTPS a cada cinco segundos e usa a credencial individual e
CA de `/etc/elo-terminal`. Não recebe chave administrativa nem abre uma nova porta.
O executável de produção exige root e hardware Raspberry Pi, e só pode chamar
`/sbin/reboot` ou `/sbin/poweroff`, sem comandos de shell enviados pelo servidor.

Cada solicitação vale 120 segundos, fica vinculada à identidade e à inicialização
atual do aparelho e é persistida em `state/control.json` no servidor. Somente uma
solicitação pode ficar em andamento por totem. Revogação cancela solicitações ainda
pendentes. Uma solicitação expirada não é entregue após reconexão.

O agente registra o identificador em `/var/lib/elo-control/consumed.json` antes de
confirmar recebimento ao servidor. Somente após resposta HTTPS válida executa a ação.
O registro privado impede repetir os últimos 128 comandos após reinício ou reentrega.
Falha de confirmação recusa a ação e exige nova solicitação administrativa.

O painel distingue espera, recebimento, falha, expiração e nova inicialização observada.
Recebimento não comprova desligamento físico; ausência de contato tampouco comprova
desligamento. **Totem conectado após reinicialização** significa que o agente informou
uma nova inicialização dentro do intervalo de observação, sem provar a causa.

Testes isolados e instalação operacional estão registrados na
[evidência de controle de energia](../evidence/PI5-POWER-CONTROL-20261112.md).

## Persistência e validação

Cadastro privado em `state/terminals.json`; relatórios individuais em
`state/terminals/ID/receipt.json`. Relatório original permanece em `state/receipt.json`
para compatibilidade. Cadastro limitado a 100 identidades adicionais, nome até 80 bytes.
Publicação/título, número de página, total, modo e duração têm limites validados.
Nenhuma resposta, endereço MAC ou dado pessoal do visitante é coletado.

Relatório schema 2 estende recibo anterior com objeto `display`. Cliente só atualiza
esse objeto na confirmação de frame correspondente. Hash identifica bytes da publicação
validada, não uma screenshot. Identificação por credencial não prova ausência de falha
física no monitor: sistema acompanha o caminho de apresentação do cliente.

Testes usam dois clientes Qt nativos com credenciais e caches distintos, verificam
mudança automática de página, revogação, persistência e rejeição de relatórios inválidos.
Portal foi aberto por HTTPS na LAN e conferido em Chromium. Pi físico ainda aguarda
provisionamento e ensaio; cadastro sem relatório aparece aguardando primeira comunicação.
