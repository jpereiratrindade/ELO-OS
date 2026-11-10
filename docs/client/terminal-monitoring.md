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
